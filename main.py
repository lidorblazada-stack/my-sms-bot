import discord
from discord import app_commands
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות IDs קבועים לפי הבקשה שלך
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
REPORT_CHANNEL_ID = 1501721217818824805 # ערוץ דיווחים
SUGGESTIONS_CHANNEL_ID = 1501721653112078639 # ערוץ המלצות
WELCOME_CHANNEL_ID = 1501713652217282591 # ערוץ כניסה ועזיבה

class GuardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🛡️ שומר השרת מאובטח ב-100% ומוכן לפעולה!")

bot = GuardBot()

# פונקציית עזר ל-Firebase
async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            elif method == "DELETE": res = await client.delete(url)
            return res.json() if method != "DELETE" else None
        except: return None

# --- פקודות ניהול (אדמינים בלבד) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    await interaction.response.defer()
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    await interaction.followup.send(f"⚠️ {member.mention} הוזהר! (סה''כ: {warns}/5)")
    if warns == 3: await member.timeout(datetime.timedelta(minutes=30))
    elif warns >= 5: 
        await member.kick()
        await fb_request("DELETE", f"warnings/{member.id}")

@bot.tree.command(name="clear_warns", description="איפוס כל האזהרות למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def clear_warns(interaction: discord.Interaction, member: discord.Member):
    await fb_request("DELETE", f"warnings/{member.id}")
    await interaction.response.send_message(f"✅ האזהרות של {member.name} אופסו.", ephemeral=True)

@bot.tree.command(name="block_user", description="חסימת משתמש ממערכת הדיווחים/המלצות")
@app_commands.choices(system=[
    app_commands.Choice(name="דיווחים (Report)", value="reports"),
    app_commands.Choice(name="המלצות (Suggest)", value="suggestions")
])
@app_commands.checks.has_permissions(administrator=True)
async def block_user(interaction: discord.Interaction, member: discord.Member, system: str):
    await fb_request("PUT", f"blocked_{system}/{member.id}", True)
    await interaction.response.send_message(f"🚫 {member.name} נחסם מה-{system}.", ephemeral=True)

# --- פקודות משתמשים (דיווח והמלצה מעוצבים) ---

@bot.tree.command(name="report", description="דווח על משתמש לצוות 🚨")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    if await fb_request("GET", f"blocked_reports/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש הגיע", color=0xff0000, timestamp=datetime.datetime.now())
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=True)
        embed.add_field(name="על המשתמש:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)
        await interaction.response.send_message("הדיווח התקבל, הצוות יבדוק ויעדכן. ✅", ephemeral=True)

@bot.tree.command(name="suggest", description="שלח המלצה לשיפור השרת 💡")
async def suggest(interaction: discord.Interaction, suggestion: str):
    if await fb_request("GET", f"blocked_suggestions/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="💡 המלצה חדשה לצוות", color=0x00ff00, timestamp=datetime.datetime.now())
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=False)
        embed.add_field(name="ההמלצה:", value=f"```\n{suggestion}\n```", inline=False)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        await channel.send(embed=embed)
        await interaction.response.send_message("ההמלצה התקבלה, תודה על העזרה! ✅", ephemeral=True)

# --- מידע ---

@bot.tree.command(name="check_warns", description="בדיקה כמה אזהרות יש למשתמש")
async def check_warns(interaction: discord.Interaction, member: discord.Member):
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    await interaction.response.send_message(f"🔍 למשתמש **{member.name}** יש **{warns}** אזהרות.", ephemeral=True)

# --- אירועי כניסה ועזיבה (עם הכיתובים שלך) ---

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎊 ברוך הבא לשרת המוגן! 🎊",
            description=f"שלום {member.mention}, הגעת לשומר השרת! תהנה מהשהות 🛡️",
            color=0x3498db,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"משתמש מספר {member.guild.member_count}")
        await channel.send(content=f"ברוך הבא {member.mention}, הגעת לשומר השרת המוגן! 🔥", embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 להתראות",
            description=f"המשתמש **{member.name}** עזב את השרת המוגן. נתגעגע! 😢",
            color=0xff0000,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(content=f"להתראות {member.name}, חבל שעזבת את שומר השרת המוגן שלנו...", embed=embed)

bot.run(TOKEN)
