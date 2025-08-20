import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
import json
import os
from dotenv import load_dotenv
from config import ADMINS
from flask import Flask, request, jsonify
import threading

# ================== CẤU HÌNH ==================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "keys.json"
CHANNEL_ID = 1404789284694917161  # 🔴 THAY BẰNG CHANNEL ID CỦA BẠN
MENU_MESSAGE_FILE = "menu_message_id.txt"  # Lưu ID message để không spam nhiều menu

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_menu_message_id(message_id):
    with open(MENU_MESSAGE_FILE, "w") as f:
        f.write(str(message_id))

def load_menu_message_id():
    if os.path.exists(MENU_MESSAGE_FILE):
        with open(MENU_MESSAGE_FILE, "r") as f:
            return int(f.read().strip())
    return None

# ================== BOT EVENTS ==================
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Kiểm tra xem đã gửi menu trước đó chưa
        old_msg_id = load_menu_message_id()
        if old_msg_id:
            try:
                old_msg = await channel.fetch_message(old_msg_id)
                if old_msg:  # Nếu tồn tại thì không gửi lại
                    print("📌 Menu đã tồn tại, không gửi thêm.")
                    return
            except:
                pass  # Nếu lỗi (msg bị xoá) thì gửi mới

        embed = discord.Embed(
            title="🔧 Hệ thống Key",
            description="Chọn hành động trong menu bên dưới:",
            color=0x00ffcc
        )
        msg = await channel.send(embed=embed, view=MenuView())
        save_menu_message_id(msg.id)

# ================== MODALS ==================
class RedeemModal(Modal, title="🔑 Redeem Key"):
    key = TextInput(label="Nhập key của bạn", placeholder="Ví dụ: ABC123", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        db = load_db()
        keys = db["keys"]
        user_id = str(interaction.user.id)
        key_value = str(self.key.value).strip()

        if key_value not in keys:
            return await interaction.response.send_message("❌ Key không tồn tại!", ephemeral=True)

        if keys[key_value]["uid"] is not None:
            return await interaction.response.send_message("❌ Key này đã được sử dụng!", ephemeral=True)

        keys[key_value]["uid"] = user_id
        keys[key_value]["hwid"] = None  # HWID sẽ bind khi chạy script lần đầu
        save_db(db)

        await interaction.response.send_message(f"✅ Redeem thành công! Key `{key_value}` đã bind với UID {user_id}", ephemeral=True)

class CreateKeyModal(Modal, title="🛠️ Tạo Key"):
    key = TextInput(label="Nhập key muốn tạo", placeholder="Ví dụ: NEWKEY123", required=True)

    async def on_submit(self, interaction: discord.Interaction):
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

# ================== LỆNH ==================
@bot.command()
async def menu(ctx):
    embed = discord.Embed(
        title="🔧 Hệ thống Key",
        description="Chọn hành động trong menu bên dưới:",
        color=0x00ffcc
    )
    await ctx.send(embed=embed, view=MenuView())

# ================== API FLASK ==================
app = Flask(__name__)

@app.route("/check", methods=["POST"])
def check():
    data = request.json
    uid = str(data.get("uid"))
    hwid = str(data.get("hwid"))

    db = load_db()
    keys = db["keys"]

    for k, v in keys.items():
        if v["uid"] == uid:
            if v["hwid"] is None:
                v["hwid"] = hwid  # bind lần đầu
                save_db(db)
                return jsonify({"status": "success", "key": k, "uid": uid})
            elif v["hwid"] == hwid:
                return jsonify({"status": "success", "key": k, "uid": uid})
            else:
                return jsonify({"status": "hwid_mismatch"})
    return jsonify({"status": "no_key"})

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# ================== START BOT + API ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
