import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות שמושכות מה-Secrets של השרת
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
LOG_ID = 1499510962296721568

async def fb_put(path, data):
    async with httpx.AsyncClient() as client:
        # החיבור לפיירבייס שבתמונה שלך
        url = f"{FB_URL}{path}.json"
        await client.put(url, json=data)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.tree.sync()
    # עדכון ראשון לפיירבייס שהבוט עלה
    await fb_put("status", {"bot_status": "online", "time": str(datetime.datetime.now())})
    print(f"✅ {bot.user} מחובר ופיירבייס מעודכן!")

@bot.event
async def on_member_join(member):
    # שומר כל כניסה לפיירבייס
    await fb_put(f"logs/joins/{member.id}", {"user": member.name, "at": str(datetime.datetime.now())})
    
    chan = bot.get_channel(LOG_ID)
    if chan:
        await chan.send(f"📥 {member.name} נשמר בפיירבייס.")

bot.run(TOKEN)
