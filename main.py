import discord
from discord.ext import commands
from discord import app_commands
import os

# 1. קודם כל מגדירים את הבוט
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

# 2. כאן אנחנו יוצרים את המשתנה 'bot'
bot = MyBot()

# 3. רק עכשיו אפשר להשתמש ב-@bot.tree.command
@bot.tree.command(name="spam")
async def spam(interaction: discord.Interaction, phone: str):
    await interaction.response.send_message(f"🚀 מתחיל הפצצה על {phone}...")

# 4. בסוף מריצים
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
