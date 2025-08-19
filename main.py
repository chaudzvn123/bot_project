import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
import json
import os
from dotenv import load_dotenv
from config import ADMINS

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "keys.json"

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")

# ================== MODAL ==================
class RedeemModal(Modal, title="🔑 Redeem Key"):
    key = TextInput(label="Nhập key của bạn", placeholder="Ví dụ: ABC123XYZ", required=True)

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
        keys[key_value]["hwid"] = "BIND"  # hoặc None nếu bạn muốn để trống
        save_db(db)

        await interaction.response.send_message(f"✅ Redeem thành công! Key `{key_value}` đã bind với UID {user_id}", ephemeral=True)

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
            discord.SelectOption(label="Check Key", description="Kiểm tra key của bạn")
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
            await interaction.response.send_message("🛠️ Nhập theo cú pháp: `!createkey <key>`", ephemeral=True)

        elif choice == "Check Key":
            for k, v in keys.items():
                if v["uid"] == user_id:
                    return await interaction.response.send_message(
                        f"✅ Bạn có key `{k}` | HWID: `{v['hwid']}`", ephemeral=True
                    )
            await interaction.response.send_message("❌ Bạn không có key!", ephemeral=True)

# ================== LỆNH ==================
@bot.command()
async def menu(ctx):
    embed = discord.Embed(title="🔧 Hệ thống Key", description="Chọn hành động trong menu bên dưới:", color=0x00ffcc)
    await ctx.send(embed=embed, view=MenuView())

@bot.command()
async def createkey(ctx, key: str):
    if ctx.author.id not in ADMINS:
        return await ctx.send("❌ Bạn không có quyền!")

    db = load_db()
    keys = db["keys"]

    if key in keys:
        return await ctx.send("❌ Key đã tồn tại!")

    keys[key] = {"uid": None, "hwid": None}
    save_db(db)
    await ctx.send(f"✅ Đã tạo key: {key}")

bot.run(TOKEN)
