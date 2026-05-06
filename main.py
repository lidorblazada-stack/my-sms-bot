import discord
from discord import app_commands
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
LOG_ID = 1499510962296721568

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # מסנכרן את פקודות הסלאש עם דיסקורד
        await self.tree.sync()
        print(f"✅ פקודות הסלאש סונכרנו!")

bot = MyBot()

# פונקציית עזר לפיירבייס
async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            return res.json()
        except: return None

# --- פקודות סלאש (Slash Commands) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.describe(member="המשתמש להזהיר", reason="סיבת האזהרה")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    await interaction.response.defer() # מונע מהפקודה להיכשל אם לוקח זמן
    
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    
    await interaction.followup.send(f"⚠️ {member.mention} קיבל אזהרה! ({warns}/5)")
    
    if warns == 3:
        await member.timeout(datetime.timedelta(minutes=30), reason="3 אזהרות")
    elif warns >= 5:
        await member.kick(reason="5 אזהרות")
        await fb_request("PUT", f"warnings/{member.id}", 0)

@bot.tree.command(name="blacklist", description="חסימה לצמיתות מהספאמר")
@app_commands.checks.has_permissions(administrator=True)
async def blacklist(interaction: discord.Interaction, member: discord.Member):
    await fb_request("PUT", f"blacklist/{member.id}", {"name": member.name})
    await member.ban(reason="Blacklist")
    await interaction.response.send_message(f"💀 {member.name} נחסם לצמיתות והוסף לרשימה השחורה.")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def clear_warns(interaction: discord.Interaction, member: discord.Member):
    await fb_request("PUT", f"warnings/{member.id}", 0)
    await interaction.response.send_message(f"✅ האזהרות של {member.name} אופסו.")

# --- אירועים רגילים (וולקם) ---
@bot.event
async def on_member_join(member):
    # (הקוד של הוולקם שכתבנו קודם נשאר כאן אותו דבר)
    welcome_channel = discord.utils.get(member.guild.text_channels, name="welcome") or bot.get_channel(LOG_ID)
    if welcome_channel:
        embed = discord.Embed(title="🎊 ברוך הבא לספאמר!", description=f"היי {member.mention}, תהנה מהספאמר הכי חזק בארץ! 🔥", color=0x00ffff)
        await welcome_channel.send(embed=embed)

bot.run(TOKEN)
