import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
import json
import os
from dotenv import load_dotenv
from config import ADMINS
from flask import Flask, request, jsonify
import threading
import traceback

# ================== CẤU HÌNH ==================
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("❌ Thiếu DISCORD_TOKEN trong .env hoặc Secrets!")

DB_FILE = "keys.json"
MENU_MESSAGE_FILE = "menu_message_id.txt"  # Lưu ID message để không spam nhiều menu
CHANNEL_ID = 1404789284694917161  # 🔴 THAY BẰNG CHANNEL ID CỦA BẠN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================== HÀM QUẢN LÝ FILE ==================
def load_db():
    if not os.path.exists(DB_FILE):
        print("⚠️ Chưa có file keys.json → tạo mới.")
        with open(DB_FILE, "w") as f:
            json.dump({"keys": {}}, f, indent=4)
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("❌ Lỗi khi đọc keys.json:", e)
        return {"keys": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("❌ Lỗi khi ghi keys.json:", e)

def save_menu_message_id(message_id):
    with open(MENU_MESSAGE_FILE, "w") as f:
        f.write(str(message_id))

def load_menu_message_id():
    if os.path.exists(MENU_MESSAGE_FILE):
        try:
            with open(MENU_MESSAGE_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return None
    return None

# ================== BOT EVENTS ==================
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")

    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print(f"❌ Không tìm thấy channel ID: {CHANNEL_ID}")
            return

        old_msg_id = load_menu_message_id()
        if old_msg_id:
            try:
                old_msg = await channel.fetch_message(old_msg_id)
                if old_msg:
                    print("📌 Menu đã tồn tại, không gửi thêm.")
                    return
            except Exception:
                pass

        embed = discord.Embed(
            title="🔧 Hệ thống Key",
            description="Chọn hành động trong menu bên dưới:",
            color=0x00ffcc
        )
        msg = await channel.send(embed=embed, view=MenuView())
        save_menu_message_id(msg.id)
        print("📨 Đã gửi menu thành công!")

    except Exception as e:
        print("❌ Lỗi khi gửi menu:", e)
        traceback.print_exc()

# ================== MODALS ==================
class RedeemModal(Modal, title="🔑 Redeem Key"):
    key = TextInput(label="Nhập key của bạn", placeholder="Ví dụ: ABC123", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            db = load_db()
            keys = db["keys"]
            user_id = str(interaction.user.id)
            key_value = str(self.key.value).strip()

            if key_value not in keys:
                return await interaction.response.send_message("❌ Key không tồn tại!", ephemeral=True)

            if keys[key_value]["uid"] is not None:
                return await interaction.response.send_message("❌ Key này đã được sử dụng!", ephemeral=True)

            keys[key_value]["uid"] = user_id
            keys[key_value]["hwid"] = None
            save_db(db)

            await interaction.response.send_message(
                f"✅ Redeem thành công! Key `{key_value}` đã bind với UID {user_id}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            traceback.print_exc()

class CreateKeyModal(Modal, title="🛠️ Tạo Key"):
    key = TextInput(label="Nhập key muốn tạo", placeholder="Ví dụ: NEWKEY123", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if interaction.user.id not in ADMINS:
                return await interaction.response.send_message("❌ Bạn không có quyền tạo key!", ephemeral=True)

            db = load_db()
            keys = db["keys"]
            key_value = str(self.key.value).strip()

            if key_value in keys:
                return await interaction.response.send_message("❌ Key đã tồn tại!", ephemeral=True)

            keys[key_value] = {"uid": None, "hwid": None}
            save_db(db)

            await interaction.response.send_message(f"✅ Đã tạo key mới: `{key_value}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            traceback.print_exc()

# ================== MENU ==================
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuSelect())

class MenuSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Redeem Key", description="Nhập key để bind"),
            discord.SelectOption(label="Reset HWID", description="Reset HWID theo UID"),
            discord.SelectOption(label="Tạo Key (Admin)", description="Admin tạo key mới"),
            discord.SelectOption(label="Check Key", description="Kiểm tra key của bạn"),
            discord.SelectOption(label="Get Script", description="Lấy script Roblox")
        ]
        super().__init__(placeholder="Chọn hành động...", options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            choice = self.values[0]
            user_id = str(interaction.user.id)
            db = load_db()
            keys = db["keys"]

            if choice == "Redeem Key":
                return await interaction.response.send_modal(RedeemModal())

            elif choice == "Reset HWID":
                for k, v in keys.items():
                    if v["uid"] == user_id:
                        v["hwid"] = None
                        save_db(db)
                        return await interaction.response.send_message(f"✅ HWID của key `{k}` đã reset!", ephemeral=True)
                await interaction.response.send_message("❌ Bạn chưa có key!", ephemeral=True)

            elif choice == "Tạo Key (Admin)":
                if interaction.user.id not in ADMINS:
                    return await interaction.response.send_message("❌ Bạn không có quyền!", ephemeral=True)
                return await interaction.response.send_modal(CreateKeyModal())

            elif choice == "Check Key":
                for k, v in keys.items():
                    if v["uid"] == user_id:
                        return await interaction.response.send_message(
                            f"✅ Bạn có key `{k}` | HWID: `{v['hwid']}`", ephemeral=True
                        )
                await interaction.response.send_message("❌ Bạn không có key!", ephemeral=True)

            elif choice == "Get Script":
                for k, v in keys.items():
                    if v["uid"] == user_id:
                        script = f'''```lua
getgenv().Key = "{k}"
getgenv().ID = "{user_id}"
loadstring(game:HttpGet("https://raw.githubusercontent.com/chaudzvn123/dangcap/refs/heads/main/hub"))()
```'''
                        try:
                            await interaction.user.send(f"✅ Đây là script của bạn:\n{script}")
                            return await interaction.response.send_message("📩 Script đã được gửi vào tin nhắn riêng (DM)!", ephemeral=True)
                        except:
                            return await interaction.response.send_message("❌ Không thể gửi DM! Hãy bật tin nhắn riêng.", ephemeral=True)
                await interaction.response.send_message("❌ Bạn chưa redeem key!", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            traceback.print_exc()

# ================== LỆNH ==================
@bot.command()
async def menu(ctx):
    try:
        embed = discord.Embed(
            title="🔧 Hệ thống Key",
            description="Chọn hành động trong menu bên dưới:",
            color=0x00ffcc
        )
        await ctx.send(embed=embed, view=MenuView())
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {e}")
        traceback.print_exc()

# ================== API FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "API is running!"

@app.route("/check", methods=["POST"])
def check():
    try:
        data = request.json
        uid = str(data.get("uid"))
        hwid = str(data.get("hwid"))

        db = load_db()
        keys = db["keys"]

        for k, v in keys.items():
            if v["uid"] == uid:
                if v["hwid"] is None:
                    v["hwid"] = hwid
                    save_db(db)
                    return jsonify({"status": "success", "key": k, "uid": uid})
                elif v["hwid"] == hwid:
                    return jsonify({"status": "success", "key": k, "uid": uid})
                else:
                    return jsonify({"status": "hwid_mismatch"})
        return jsonify({"status": "no_key"})
    except Exception as e:
        print("❌ Lỗi API /check:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# ================== START BOT + API ==================
if __name__ == "__main__":
    try:
        threading.Thread(target=run_flask).start()
        print("🚀 Đang khởi động bot...")
        bot.run(TOKEN)
    except Exception as e:
        print("❌ Lỗi khi chạy bot:", e)
        traceback.print_exc()
