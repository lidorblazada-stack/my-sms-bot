import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID (תוודא שה-Token ב-Variables ב-Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)
feedback_cooldowns = {}

# --- פונקציית אבטחה לאונר בלבד ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000)
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention}")
        embed.add_field(name="פקודה:", value=f"/{interaction.command.name}")
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ פקודה ל-OWNER בלבד! ניסיון נוסף יגרור אזהרה.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ אזהרה רשמית נרשמה! ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- הגדרות הבוט ---
class ServerGuard(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync() # מסנכרן את כל הפקודות לדיסקורד

bot = ServerGuard()

# --- פקודות ניהול (OWNER בלבד) ---

@bot.tree.command(name="check_status", description="בדיקת סטטוס אבטחה וגיל חשבון (OWNER בלבד)")
async def chk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשוד (חדש)" if age.days < 3 else "✅ תקין"
        await interaction.response.send_message(f"👤 {member.name} | גיל: {age.days} ימים | סטטוס: {status}")

@bot.tree.command(name="clear", description="מחיקת הודעות (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="השתקת משתמש (OWNER בלבד)")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="unmute", description="ביטול השתקה (OWNER בלבד)")
async def umt(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 {member.mention} חזר לדבר.")

@bot.tree.command(name="kick", description="העפת משתמש (OWNER בלבד)")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick()
        await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="חסימת משתמש (OWNER בלבד)")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="unban", description="ביטול חסימה לפי ID (OWNER בלבד)")
async def ubn(interaction: discord.Interaction, user_id: str):
    if await check_is_owner(interaction):
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.name} שוחרר.")

@bot.tree.command(name="warn", description="מתן אזהרה (OWNER בלבד)")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר.")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות (OWNER בלבד)")
async def cwr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"✅ אזהרות אופסו.")

@bot.tree.command(name="lock", description="נעילת ערוץ (OWNER בלבד)")
async def lock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 ננעל.")

@bot.tree.command(name="unlock", description="פתיחת ערוץ (OWNER בלבד)")
async def unlock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("🔓 נפתח.")

@bot.tree.command(name="slowmode", description="הגדרת מצב איטי (OWNER בלבד)")
async def slow(interaction: discord.Interaction, seconds: int):
    if await check_is_owner(interaction):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"⏳ סלואו-מוד: {seconds} שניות.")

# --- פקודות כלליות ---

@bot.tree.command(name="report", description="דיווח על משתמש לצוות")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח", color=0xe74c3c)
        embed.add_field(name="על:", value=member.mention)
        embed.add_field(name="סיבה:", value=reason)
        await ch.send(embed=embed)
        await interaction.response.send_message("נשלח.", ephemeral=True)

@bot.tree.command(name="suggest", description="שליחת הצעה לשיפור")
async def sg(interaction: discord.Interaction, text: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 הצעה", description=text, color=0xf1c40f)
        await ch.send(embed=embed)
        await interaction.response.send_message("תודה!", ephemeral=True)

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def wrs(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 {m.mention}: {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="avatar", description="הצגת תמונת פרופיל")
async def av(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(m.display_avatar.url)

@bot.tree.command(name="user_id", description="קבלת ID של משתמש")
async def uid(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🆔 `{member.id}`")

@bot.tree.command(name="server_info", description="מידע על השרת")
async def si(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏰 {interaction.guild.name} | 👥 {interaction.guild.member_count}")

@bot.tree.command(name="ping", description="בדיקת דיליי")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# --- אירועים: וולקם + Alt Detector ---

@bot.event
async def on_member_join(member):
    # 1. דיווח אבטחה ל-ID שלך (Server Guard מדווח)
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשוד (חדש)" if age.days < 3 else "✅ תקין"
        color = 0xff0000 if age.days < 3 else 0x00ff00
        embed = discord.Embed(title="🛡️ שומר השרת - בדיקת אבטחה", color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="משתמש:", value=member.mention)
        embed.add_field(name="גיל חשבון:", value=f"{age.days} ימים")
        embed.add_field(name="סטטוס:", value=status)
        await log_ch.send(embed=embed)

    # 2. הודעת וולקם עם תמונת פרופיל גדולה (מתוקן!)
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        w_embed = discord.Embed(description="**ברוך הבא לשרת! 🔥**", color=0x00ffff)
        w_embed.set_image(url=member.display_avatar.url)
        await welcome_ch.send(content=f"אהלן {member.mention} !", embed=w_embed)

@bot.event
async def on_ready():
    print(f'🛡️ Unified Server Guard is ONLINE!')

if TOKEN: bot.run(TOKEN)
