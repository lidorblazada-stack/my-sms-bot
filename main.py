import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int) 
feedback_cooldowns = {}

# --- פונקציית אבטחה ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה:", value=f"/{interaction.command.name}", inline=False)
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **אזהרה ראשונה!** פקודה ל-OWNER בלבד. ניסיון נוסף = אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **קיבלת אזהרה!** אל תיגע בפקודות OWNER. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# (Views/Modals...)
class FeedbackModal(ui.Modal, title='💎 פידבק לקהילה'):
    fb_text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='אנונימי? (כן/לא)', default='לא', max_length=2)
    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = time.time()
        if user_id in feedback_cooldowns and now - feedback_cooldowns[user_id] < 300:
            await interaction.response.send_message(f"⏳ חכה עוד קצת אחי.", ephemeral=True); return
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anonymous.value.strip() == "כן"
            author = "אנונימי" if is_anon else interaction.user.name
            embed = discord.Embed(title="💎 פידבק", description=self.fb_text.value, color=0x3498db)
            embed.set_author(name=f"מאת: {author}"); await ch.send(embed=embed)
            feedback_cooldowns[user_id] = now
            await interaction.response.send_message("✅ נשלח!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='אימות ✅', style=discord.ButtonStyle.green, custom_id='v_final_20')
    async def v_callback(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role: await interaction.user.add_roles(role); await interaction.response.send_message("אומתת!", ephemeral=True)

class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(VerifyView()); await self.tree.sync()

bot = CyberShield()

# --- רשימת ה-20+ פקודות ---

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות כניסה (OWNER בלבד)")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.send("🛡️ **אימות:**", view=VerifyView()); await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק אנונימי (OWNER בלבד)")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        view = ui.View(timeout=None); btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="fb_20")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal()); view.add_item(btn)
        await interaction.channel.send("💎 **פידבקים:**", view=view); await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True); await interaction.channel.purge(limit=amount); await interaction.followup.send(f"נמחקו {amount}.")

@bot.tree.command(name="mute", description="השתקת משתמש (OWNER בלבד)")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes)); await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="unmute", description="ביטול השתקה (OWNER בלבד)")
async def umt(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.timeout(None); await interaction.response.send_message(f"🔊 {member.mention} חזר לדבר.")

@bot.tree.command(name="kick", description="העפת משתמש מהשרת (OWNER בלבד)")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick(); await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="חסימת משתמש מהשרת (OWNER בלבד)")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban(); await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="unban", description="ביטול חסימה למשתמש לפי ID (OWNER בלבד)")
async def ubn(interaction: discord.Interaction, user_id: str):
    if await check_is_owner(interaction):
        user = await bot.fetch_user(int(user_id)); await interaction.guild.unban(user); await interaction.response.send_message(f"✅ {user.name} שוחרר.")

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש (OWNER בלבד)")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1; await interaction.response.send_message(f"⚠️ {member.mention} הוזהר.")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות (OWNER בלבד)")
async def cwr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] = 0; await interaction.response.send_message(f"✅ אופס.")

@bot.tree.command(name="lock", description="נעילת ערוץ (OWNER בלבד)")
async def lock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False); await interaction.response.send_message("🔒 ננעל.")

@bot.tree.command(name="unlock", description="פתיחת ערוץ (OWNER בלבד)")
async def unlock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True); await interaction.response.send_message("🔓 נפתח.")

@bot.tree.command(name="slowmode", description="הגדרת מצב איטי (OWNER בלבד)")
async def slow(interaction: discord.Interaction, seconds: int):
    if await check_is_owner(interaction):
        await interaction.channel.edit(slowmode_delay=seconds); await interaction.response.send_message(f"⏳ {seconds} שניות.")

@bot.tree.command(name="report", description="דיווח על משתמש לצוות")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח", color=0xe74c3c); embed.add_field(name="על:", value=member.mention); embed.add_field(name="סיבה:", value=reason)
        await ch.send(embed=embed); await interaction.response.send_message("נשלח.", ephemeral=True)

@bot.tree.command(name="suggest", description="שליחת הצעה לשיפור")
async def sg(interaction: discord.Interaction, text: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 הצעה", description=text, color=0xf1c40f); await ch.send(embed=embed); await interaction.response.send_message("תודה!", ephemeral=True)

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def wrs(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user; await interaction.response.send_message(f"📋 {m.mention}: {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="avatar", description="הצגת תמונת פרופיל")
async def av(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user; await interaction.response.send_message(m.display_avatar.url)

@bot.tree.command(name="user_id", description="קבלת ה-ID של משתמש")
async def uid(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🆔 ה-ID של {member.name} הוא: `{member.id}`")

@bot.tree.command(name="server_icon", description="הצגת האייקון של השרת")
async def s_ico(interaction: discord.Interaction):
    await interaction.response.send_message(interaction.guild.icon.url if interaction.guild.icon else "אין אייקון.")

@bot.tree.command(name="server_info", description="מידע על השרת")
async def si(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏰 {interaction.guild.name}\n👥 {interaction.guild.member_count} חברים.")

@bot.tree.command(name="ping", description="בדיקת דיליי")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# (Events/Welcome...)
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        embed = discord.Embed(description="**ברוך הבא לספאמר! 🔥**", color=0x00ffff)
        embed.set_image(url=member.display_avatar.url)
        await ch.send(content=f"אהלן {member.mention} !", embed=embed)

@bot.event
async def on_ready(): print(f'🛡️ Cyber-Shield Final 20+ Commands Online!')

if TOKEN: bot.run(TOKEN)
