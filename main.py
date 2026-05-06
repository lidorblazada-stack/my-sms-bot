import discord
from discord import app_commands
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות IDs
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
REPORT_CHANNEL_ID = 1501721217818824805
SUGGESTIONS_CHANNEL_ID = 1501721653112078639
WELCOME_CHANNEL_ID = 1501713652217282591

class GuardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🛡️ שומר השרת מאובטח ומוכן!")

bot = GuardBot()

async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            elif method == "DELETE": res = await client.delete(url)
            return res.json() if method != "DELETE" else None
        except: return None

# --- פקודות ניהול ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    await interaction.response.defer()
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    await interaction.followup.send(f"⚠️ {member.mention} הוזהר! ({warns}/5)")
    if warns == 3: await member.timeout(datetime.timedelta(minutes=30))
    elif warns >= 5: 
        await member.kick()
        await fb_request("DELETE", f"warnings/{member.id}")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות")
@app_commands.checks.has_permissions(administrator=True)
async def clear_warns(interaction: discord.Interaction, member: discord.Member):
    await fb_request("DELETE", f"warnings/{member.id}")
    await interaction.response.send_message(f"✅ האזהרות של {member.name} אופסו.", ephemeral=True)

@bot.tree.command(name="block_user", description="חסימת משתמש מדיווחים/המלצות")
@app_commands.choices(system=[
    app_commands.Choice(name="דיווחים", value="reports"),
    app_commands.Choice(name="המלצות", value="suggestions")
])
@app_commands.checks.has_permissions(administrator=True)
async def block_user(interaction: discord.Interaction, member: discord.Member, system: str):
    await fb_request("PUT", f"blocked_{system}/{member.id}", True)
    await interaction.response.send_message(f"🚫 {member.name} נחסם מהמערכת.", ephemeral=True)

# --- פקודות משתמשים (סדר Fields הפוך לעברית) ---

@bot.tree.command(name="report", description="דווח על משתמש לצוות 🚨")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    if await fb_request("GET", f"blocked_reports/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.datetime.now())
        # הפכתי את הסדר כאן: קודם 'על המשתמש' ואז 'מאת' - בגלל ה-Left to Right של דיסקורד
        embed.add_field(name="על המשתמש:", value=member.mention, inline=True)
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=True)
        embed.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)
        await interaction.response.send_message("הדיווח התקבל, הצוות יבדוק ויעדכן. ✅", ephemeral=True)

@bot.tree.command(name="suggest", description="שלח המלצה לצוות 💡")
async def suggest(interaction: discord.Interaction, suggestion: str):
    if await fb_request("GET", f"blocked_suggestions/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="💡 המלצה חדשה", color=0x00ff00, timestamp=datetime.datetime.now())
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=False)
        embed.add_field(name="ההמלצה:", value=f"```\n{suggestion}\n```", inline=False)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        await channel.send(embed=embed)
        await interaction.response.send_message("ההמלצה התקבלה, תודה על העזרה! ✅", ephemeral=True)

@bot.tree.command(name="check_warns", description="בדיקת אזהרות")
async def check_warns(interaction: discord.Interaction, member: discord.Member):
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    await interaction.response.send_message(f"🔍 למשתמש **{member.name}** יש **{warns}** אזהרות.", ephemeral=True)

# --- כניסה ועזיבה ---

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🎊 ברוך הבא לשרת המוגן! 🎊", description=f"שלום {member.mention}, הגעת לשומר השרת! 🔥", color=0x3498db)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(content=f"ברוך הבא {member.mention}!", embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="👋 להתראות", description=f"המשתמש **{member.name}** עזב את השרת. נתגעגע!", color=0xff0000)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(content=f"להתראות {member.name}, חבל שעזבת...", embed=embed)

bot.run(TOKEN)
