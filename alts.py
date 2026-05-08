import discord
import os
from discord.ext import commands

# הגדרה שתומכת גם ב-TOKEN וגם ב-ALT_BOT_TOKEN כדי שלא תהיה טעות
TOKEN = os.getenv('ALT_BOT_TOKEN') or os.getenv('TOKEN')

if not TOKEN:
    print("❌ ERROR: No token found! Check your Railway Variables.")

class AltDetector(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=".", intents=intents)

    async def on_ready(self):
        print(f'✅ Alt Detector Online: {self.user}')

bot = AltDetector()

# הוסף כאן את שאר הפקודות של ה-Alts שלך...

if TOKEN:
    bot.run(TOKEN)
