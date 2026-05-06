import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות שמושכות נתונים מהמערכת (כדי שלא יפרצו לך בגיטהאב)
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = "https://vouge-guard-default-rtdb.firebaseio.com/"
LOG_CHANNEL = 1499510962296721568

async def fb_update(path, data):
    """פונקציה שכותבת ישירות לתוך ה-Firebase שבתמונה שלך"""
    async with httpx.AsyncClient() as client:
        # פיירבייס חייב .json בסוף הלינק
        url = f"{FB_URL}{path}.json"
        await client.put(url, json=data)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.tree.sync()
    # ברגע שהבוט עולה, הוא יוצר שורה ב-Firebase
    status_data = {
        "status": "online",
        "last_seen": str(datetime.datetime.now())
    }
    await fb_update("bot_info", status_data)
    print(f"✅ {bot.user} מחובר לגיטהאב ולפיירבייס!")

@bot.event
async def on_member_join(member):
    # שומר כל מי שנכנס לשרת בתוך הפיירבייס
    user_info = {
        "username": member.name,
        "id": member.id,
        "time": str(datetime.datetime.now())
    }
    await fb_update(f"users/{member.id}", user_info)

bot.run(TOKEN)
