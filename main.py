import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")

async def fb_update(path, data):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        await client.put(url, json=data)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    # ברגע שהבוט עולה, הוא מעדכן את הפיירבייס שצילמת
    status = {"bot": "online", "time": str(datetime.datetime.now())}
    await fb_update("system_status", status)
    print(f"✅ {bot.user} באוויר ומחובר לפיירבייס!")

@bot.event
async def on_member_join(member):
    # שומר כל כניסה לפיירבייס בלייב
    await fb_update(f"logs/joins/{member.id}", {"user": member.name})

bot.run(TOKEN)
