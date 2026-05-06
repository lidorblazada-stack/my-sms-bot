import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות שמושכות מה-Secrets של GitHub
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL") # הלינק שצילמת
LOG_ID = 1499510962296721568 

async def fb_update(path, data):
    """שומר מידע ב-Firebase בלייב"""
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            await client.put(url, json=data)
        except Exception as e:
            print(f"Error: {e}")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.tree.sync()
    # מעדכן את האתר של פיירבייס שהשומר עלה
    await fb_update("guard_status", {"status": "Active", "time": str(datetime.datetime.now())})
    print(f"🛡️ {bot.user} שומר השרת באוויר!")

@bot.event
async def on_member_join(member):
    # שומר כניסה ב-Firebase ושולח Welcome
    user_data = {"name": member.name, "joined": str(datetime.datetime.now())}
    await fb_update(f"members/{member.id}", user_info)
    
    chan = bot.get_channel(LOG_ID)
    if chan:
        embed = discord.Embed(title=f"⚡ ברוך הבא {member.name}", color=0x00ff00)
        await chan.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    # בדיקת חסימות (Blacklist) מהפיירבייס
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{FB_URL}blacklist/{message.author.id}.json")
        if res.json():
            await message.delete()
            return
    await bot.process_commands(message)

bot.run(TOKEN)
