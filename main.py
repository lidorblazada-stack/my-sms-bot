import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
VERIFY_ROLE_ID = 1501983948111352091 

user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

# --- פונקציית אבטחה קריטית (לוגים + אזהרות) ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    # שליחת לוג מיידי לניהול
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        now = datetime.now(timezone.utc).strftime('%H:%M:%S | %d/%m/%Y')
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000)
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="הפקודה שנוסתה:", value=f"/{interaction.command.name}", inline=False)
        embed.add_field(name="זמן ניסיון:", value=now, inline=False)
        await log_ch.send(embed=embed)
    
    # מערכת אזהרות פנימית למשתמש
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **פקודה ל-OWNER בלבד!** ניסיון נוסף יגרור אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **קיבלת אזהרה רשמית!** אל תיגע בפקודות OWNER. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- Views לפאנלים ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות חשבון ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

class FeedbackModal(ui.Modal, title="פידבק לשרת"):
    msg = ui.TextInput(label="הודעה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        if ch: await ch.send(f"💎 פידבק מ-{i.user.name}: {self.msg.value}")
        await i.response.send_message("נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 📝", style=discord.ButtonStyle.blurple, custom_id="f_btn")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- פקודות OWNER ---

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות (OWNER)")
async def sv(i: discord.Interaction):
    if await check_is_owner(i): await i.channel.send("🛡️ לחץ לאימות:", view=VerifyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק (OWNER)")
async def sf(i: discord.Interaction):
    if await check_is_owner(i): await i.channel.send("💬 פאנל פידבקים:", view=FeedbackView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש (OWNER)")
async def warn(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! (סך הכל: {user_warnings[member.id]})")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות (OWNER)")
async def cw(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i):
        user_warnings[member.id] = 0
        await i.response.send_message(f"✅ האזהרות של {member.mention} אופסו.")

@bot.tree.command(name="ban", description="חסימת משתמש (OWNER)")
async def ban(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i): await member.ban(); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="mute", description="השתקת משתמש (OWNER)")
async def mute(i: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(i): await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.name} הושתק.")

# --- פקודות כלליות ---

@bot.tree.command(name="warnings", description="בדיקת אזהרות של משתמש")
async def check_w(i: discord.Interaction, member: discord.Member = None):
    target = member or i.user
    await i.response.send_message(f"📋 למשתמש {target.mention} יש **{user_warnings[target.id]}** אזהרות.")

@bot.tree.command(name="ping", description="בדיקת מהירות")
async def ping(i: discord.Interaction): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# --- אירועים ---

@bot.event
async def on_member_join(member):
    # בדיקת חשבון חשוד
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשבון חשוד!" if age.days < 3 else "✅ תקין"
        await log_ch.send(f"👤 **כניסה:** {member.mention} | **גיל חשבון:** {age.days} ימים | **סטטוס:** {status}")
    
    # וולקם
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"ברוך הבא {member.mention}! 🔥", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    bot.add_view(VerifyView()); bot.add_view(FeedbackView())
    print(f"🛡️ {bot.user.name} Is Fully Ready!")

if TOKEN: bot.run(TOKEN)
