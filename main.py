import discord
from discord import app_commands
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות IDs של הערוצים ששלחת
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
LOG_ID = 1499510962296721568
REPORT_CHANNEL_ID = 1501721217818824805 # הערוץ ששלחת לדיווחים
SUGGESTIONS_CHANNEL_ID = 1501721653112078639 # הערוץ ששלחת להמלצות

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ שומר השרת של לידור מחובר עם IDs קבועים!")

bot = MyBot()

async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            return res.json()
        except: return None

# --- פקודות ניהול ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    await interaction.response.defer()
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    
    await interaction.followup.send(f"⚠️ {member.mention} הוזהר! (סה''כ אזהרות: {warns}/5)")
    
    if warns == 3:
        await member.timeout(datetime.timedelta(minutes=30), reason="3 אזהרות")
    elif warns >= 5:
        await member.kick(reason="5 אזהרות")
        await fb_request("PUT", f"warnings/{member.id}", 0)

@bot.tree.command(name="check_warns", description="בדיקה כמה אזהרות יש למשתמש")
async def check_warns(interaction: discord.Interaction, member: discord.Member):
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    await interaction.response.send_message(f"🔍 למשתמש **{member.name}** יש **{warns}** אזהרות רשומות.", ephemeral=True)

# --- פקודות משתמשים (דיווח והמלצה) ---

@bot.tree.command(name="report", description="דווח על משתמש לצוות 🚨")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.datetime.now())
        embed.add_field(name="מדווח:", value=interaction.user.mention, inline=True)
        embed.add_field(name="על המשתמש:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await report_channel.send(embed=embed)
        await interaction.response.send_message("✅ הדיווח נשלח בהצלחה.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ שגיאה: ערוץ הדיווחים לא נמצא.", ephemeral=True)

@bot.tree.command(name="suggest", description="שלח המלצה לשיפור השרת 💡")
async def suggest(interaction: discord.Interaction, suggestion: str):
    suggest_channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if suggest_channel:
        embed = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0x00ff00)
        embed.set_author(name=f"מאת: {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        
        now = datetime.datetime.now().strftime("%H:%M")
        embed.set_footer(text=f"נשלח בשעה {now} | Spammer System")
        
        await suggest_channel.send(embed=embed)
        await interaction.response.send_message("✅ ההמלצה שלך פורסמה.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ שגיאה: ערוץ ההמלצות לא נמצא.", ephemeral=True)

# --- כניסה לשרת ---
@bot.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.text_channels, name="welcome") or bot.get_channel(LOG_ID)
    if welcome_channel:
        embed = discord.Embed(title="🎊 ברוך הבא לשרת ספאמר!", description=f"היי {member.mention}, הגעת לספאמר הכי חזק בארץ! 🔥", color=0x00ffff)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await welcome_channel.send(content=f"וולקם {member.mention}!", embed=embed)

bot.run(TOKEN)
