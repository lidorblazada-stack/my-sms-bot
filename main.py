import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")

# פונקציית עזר לעדכון פיירבייס
async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        if method == "PUT":
            res = await client.put(url, json=data)
        elif method == "GET":
            res = await client.get(url)
        return res.json()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # מעדכן סטטוס בפיירבייס שהשומר עלה
    await fb_request("PUT", "guard_status", {"status": "Active", "last_boot": str(datetime.datetime.now())})
    print(f"🛡️ {bot.user} שומר השרת נכנס למשמרת!")

# --- פקודות שומר השרת ---

@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, user: discord.Member):
    """חוסם משתמש ורושם אותו בפיירבייס"""
    await fb_request("PUT", f"blacklist/{user.id}", {"name": user.name, "reason": "Blocked by Admin"})
    await user.kick(reason="נכנסת לרשימה השחורה של שומר השרת")
    await ctx.send(f"🚫 המשתמש **{user.name}** נוסף לרשימה השחורה ונזרק מהשרת.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, user_id: str):
    """מסיר משתמש מהרשימה השחורה"""
    await fb_request("PUT", f"blacklist/{user_id}", None)
    await ctx.send(f"✅ המשתמש עם האיידי {user_id} הוסר מהרשימה השחורה.")

@bot.event
async def on_member_join(member):
    """בודק כל מי שנכנס אם הוא ברשימה השחורה"""
    is_blocked = await fb_request("GET", f"blacklist/{member.id}")
    if is_blocked:
        await member.kick(reason="ניסיון כניסה של משתמש חסום (Blacklist)")
        print(f"⚠️ נחסמה כניסה של משתמש חסום: {member.name}")

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # הגנה מפני קישורים (אם אתה רוצה)
    if "http" in message.content and not message.author.guild_permissions.administrator:
        await message.delete()
        await message.channel.send(f"{message.author.mention}, אסור לשלוח לינקים בשרת הזה! 🛡️")
    
    await bot.process_commands(message)

bot.run(TOKEN)
