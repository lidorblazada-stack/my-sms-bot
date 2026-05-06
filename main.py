import discord
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
LOG_ID = 1499510962296721568 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            return res.json()
        except: return None

@bot.event
async def on_ready():
    await fb_request("PUT", "guard_status", {"status": "Online", "time": str(datetime.datetime.now())})
    print(f"🛡️ Spammer Guard מחובר ומוכן!")

# --- מערכת וולקם (Welcome) יפה ---
@bot.event
async def on_member_join(member):
    # בדיקת בלאקליסט
    is_blocked = await fb_request("GET", f"blacklist/{member.id}")
    if is_blocked:
        await member.ban(reason="Blacklist")
        return

    # חיפוש ערוץ וולקם
    welcome_channel = discord.utils.get(member.guild.text_channels, name="welcome") or \
                      discord.utils.get(member.guild.text_channels, name="וולקם") or \
                      bot.get_channel(LOG_ID)

    if welcome_channel:
        embed = discord.Embed(
            title=f"🎊 ברוך הבא לשרת ספאמר! 🎊",
            description=f"היי {member.mention}, הגעת לשרת הספאמר הכי חזק בארץ!\n\nתעשה חיים ותהנה מהספאמר 🔥",
            color=0x00ffff, # צבע טורקיז חזק
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_author(name=member.name, icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text="Spammer System • תהנה!", icon_url=member.guild.icon.url if member.guild.icon else None)
        
        await welcome_channel.send(content=f"וולקם {member.mention}!", embed=embed)

# --- הודעת עזיבה ---
@bot.event
async def on_member_remove(member):
    log_channel = bot.get_channel(LOG_ID)
    if log_channel:
        embed = discord.Embed(description=f"המשתמש **{member.name}** עזב את הספאמר... 👋", color=0xff0000)
        await log_channel.send(embed=embed)

# --- פקודות ניהול ---
@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member, *, reason="לא צוין"):
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    await ctx.send(f"⚠️ {member.mention} קיבל אזהרה ({warns}/5)")
    
    if warns == 3:
        await member.timeout(datetime.timedelta(minutes=30), reason="3 אזהרות")
    elif warns >= 5:
        await member.kick(reason="5 אזהרות")
        await fb_request("PUT", f"warnings/{member.id}", 0)

@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, user: discord.Member):
    await fb_request("PUT", f"blacklist/{user.id}", {"name": user.name})
    await user.ban(reason="Blacklist")
    await ctx.send(f"🚫 {user.name} נחסם לצמיתות.")

bot.run(TOKEN)
