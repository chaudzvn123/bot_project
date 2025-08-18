import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import datetime
import config

# Khởi tạo bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Hàm đọc dữ liệu từ keys.json
def fetch_keys_data():
    try:
        with open(config.KEYS_FILEPATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Hàm ghi dữ liệu vào keys.json
def write_keys_data(data):
    with open(config.KEYS_FILEPATH, 'w') as f:
        json.dump(data, f, indent=2)

# Menu chính
class MainMenu(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.green)
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Vui lòng nhập key và HWID để redeem.")

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.blurple)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Vui lòng nhập key và HWID mới để reset.")

    @discord.ui.button(label="Tạo Key Mới", style=discord.ButtonStyle.red)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Vui lòng nhập key mới để tạo.")

    @discord.ui.button(label="Lấy Script", style=discord.ButtonStyle.grey)
    async def script_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Vui lòng nhập key và HWID để lấy script.")

# Lệnh hiển thị menu
@bot.command()
async def menu(ctx):
    view = MainMenu()
    await ctx.send("Chọn chức năng bạn muốn sử dụng:", view=view)

# Chạy bot
bot.run(config.DISCORD_TOKEN)
