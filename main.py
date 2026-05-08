import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID (תוודא שהן נכונות ב-Railway) ---
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

# --- פונקציית אבטחה לאונר ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה שנוסתה:", value=f"/{interaction.command.name}", inline=False)
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **פקודה ל-OWNER בלבד!** ניסיון נוסף יגרור אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **אזהרה רשמית נרשמה!** אל תנסה להשתמש בפקודות OWNER. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- הגדרות הבוט ---
class ServerGuard(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync() # מסנכרן את כל 21 הפקודות

bot = ServerGuard()

# --- פקודות ניהול (OWNER בלבד) ---

@bot.tree.command(name="check_status", description="בדיקת סטטוס אבטחה וגיל חשבון (OWNER בלבד)")
async def chk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשוד (חשבון חדש)" if age.days < 3 else "✅ חשבון תקין"
        await interaction.response.send_message(f"👤 {member.mention} | גיל חשבון: {age.days} ימים | סטטוס: {status}")

@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="השתקת משתמש (OWNER בלבד)")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

@bot.tree.command(name="unmute", description="ביטול השתקה (OWNER בלבד)")
async def umt(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 {member.mention} חזר לדבר.")

@bot.tree.command(name="kick", description="העפת משתמש מהשרת (OWNER בלבד)")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick()
        await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="חסימת משתמש לצמיתות (OWNER בלבד)")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="unban", description="ביטול חסימה לפי ID (OWNER בלבד)")
async def ubn(interaction: discord.Interaction, user_id: str):
    if await check_is_owner(interaction):
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.name} שוחרר מהחסימה.")

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש (OWNER בלבד)")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות למשתמש (OWNER בלבד)")
async def cwr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"✅ האזהרות של {member.mention} אופסו.")

@bot.tree.command(name="lock", description="נעילת הערוץ (OWNER בלבד)")
async def lock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock", description="פתיחת הערוץ (OWNER בלבד)")
async def unlock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("🔓 הערוץ נפתח.")

# (כאן נמצאות שאר הפקודות הכלליות: ping, avatar, server_info, report, suggest וכו'...)

# --- אירועים: וולקם + בדיקת אבטחה אוטומטית ---
@bot.event
async def on_member_join(member):
    # 1. שליחת סטטוס ללוג האבטחה (שומר השרת מדווח)
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשבון חשוד (חדש)" if age.days < 3 else "✅ חשבון תקין"
        color = 0xff0000 if age.days < 3 else 0x00ff00
        embed = discord.Embed(title="🛡️ שומר השרת - בדיקת אבטחה", color=color, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="משתמש:", value=member.mention)
        embed.add_field(name="גיל חשבון:", value=f"{age.days} ימים")
        embed.add_field(name="סטטוס:", value=status)
        await log_ch.send(embed=embed)

    # 2. הודעת וולקם בערוץ הכללי
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        w_embed = discord.Embed(description="**ברוך הבא לשרת! 🔥**", color=0x00ffff)
        w_embed.set_image(url=member.display_avatar.url)
        await welcome_ch.send(content=f"אהלן {member.mention} !", embed=w_embed)

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} is Unified and Guarding!')

if TOKEN: bot.run(TOKEN)
