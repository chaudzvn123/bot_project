import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
import json
import os
import random
import string
import traceback
from flask import Flask, request, jsonify
import threading

# ================== CẤU HÌNH ==================
TOKEN = "YOUR_DISCORD_BOT_TOKEN"  # Thay token bot của bạn
ADMINS = [123456789012345678]  # Thay bằng Discord UID của bạn
DATA_FILE = "keys.json"

# ================== FLASK API (keep_alive) ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot đang chạy!"

@app.route('/check_key', methods=['POST'])
def check_key():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    db = load_db()
    if key in db["keys"]:
        k = db["keys"][key]
        if k["hwid"] is None:
            k["hwid"] = hwid
            save_db(db)
            return jsonify({"status": "success", "msg": "Key hợp lệ & HWID đã bind"})
        elif k["hwid"] == hwid:
            return jsonify({"status": "success", "msg": "Key hợp lệ"})
        else:
            return jsonify({"status": "fail", "msg": "HWID không khớp"})
    return jsonify({"status": "fail", "msg": "Key không tồn tại"})

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ================== QUẢN LÝ DATA ==================
def load_db():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ================== DISCORD BOT ==================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=",", intents=intents)

# -------- MODALS --------
class RedeemModal(Modal, title="Redeem Key"):
    key = TextInput(label="Nhập Key", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            db = load_db()
            if self.key.value in db["keys"]:
                db["keys"][self.key.value]["uid"] = str(interaction.user.id)
                save_db(db)
                await interaction.response.send_message("✅ Key đã được redeem!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Key không hợp lệ!", ephemeral=True)
        except Exception as e:
            print("❌ Lỗi Redeem:", e)
            await interaction.response.send_message("⚠️ Lỗi redeem key!", ephemeral=True)

class CreateKeyModal(Modal, title="Tạo Key"):
    uid = TextInput(label="UID (Discord ID)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if interaction.user.id not in ADMINS:
                return await interaction.response.send_message("❌ Bạn không có quyền!", ephemeral=True)

            key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            db = load_db()
            db["keys"][key] = {"uid": self.uid.value, "hwid": None}
            save_db(db)

            await interaction.response.send_message(f"✅ Key mới: `{key}`", ephemeral=True)
        except Exception as e:
            print("❌ Lỗi CreateKey:", e)
            await interaction.response.send_message("⚠️ Lỗi tạo key!", ephemeral=True)

# -------- MENU SELECT --------
class MenuSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Redeem Key", description="Nhập key để bind"),
            discord.SelectOption(label="Reset HWID", description="Reset HWID theo UID"),
            discord.SelectOption(label="Tạo Key (Admin)", description="Admin tạo key mới"),
            discord.SelectOption(label="Check Key", description="Kiểm tra key của bạn"),
            discord.SelectOption(label="Get Script", description="Lấy script Roblox"),
            discord.SelectOption(label="📜 Danh sách Key", description="Chỉ Admin mới dùng")
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
                            f"✅ Key: `{k}` | HWID: `{v['hwid']}`", ephemeral=True
                        )
                await interaction.response.send_message("❌ Bạn chưa redeem key!", ephemeral=True)

            elif choice == "Get Script":
                for k, v in keys.items():
                    if v["uid"] == user_id:
                        script = f'''```lua
getgenv().Key = "{k}"
getgenv().ID = "{user_id}"
loadstring(game:HttpGet("https://raw.githubusercontent.com/chaudzvn123/dangcap/refs/heads/main/hub"))()
```'''
                        try:
                            await interaction.user.send(f"✅ Script của bạn:\n{script}")
                            return await interaction.response.send_message("📩 Script đã gửi vào DM!", ephemeral=True)
                        except:
                            return await interaction.response.send_message("❌ Không gửi được DM, bật tin nhắn riêng!", ephemeral=True)
                await interaction.response.send_message("❌ Bạn chưa redeem key!", ephemeral=True)

            elif choice == "📜 Danh sách Key":
                if interaction.user.id not in ADMINS:
                    return await interaction.response.send_message("❌ Bạn không có quyền!", ephemeral=True)

                if not keys:
                    return await interaction.response.send_message("⚠️ Chưa có key nào!", ephemeral=True)

                msg = "📜 **Danh sách key:**\n"
                for k, v in keys.items():
                    msg += f"- `{k}` | UID: `{v['uid']}` | HWID: `{v['hwid']}`\n"

                if len(msg) > 1900:
                    with open("keys_list.txt", "w", encoding="utf-8") as f:
                        f.write(msg)
                    await interaction.response.send_message(
                        "📂 Danh sách key dài, xuất file:",
                        file=discord.File("keys_list.txt"),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(msg, ephemeral=True)

        except Exception as e:
            print("❌ Lỗi MenuSelect:", e)
            traceback.print_exc()
            await interaction.response.send_message("⚠️ Lỗi xử lý menu!", ephemeral=True)

class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuSelect())

# -------- LỆNH HIỆN MENU --------
@bot.command()
async def menu(ctx):
    await ctx.send("📌 Chọn chức năng từ menu:", view=MenuView())

# ================== CHẠY BOT & FLASK ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
