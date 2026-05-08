import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID (חובה לוודא ב-Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
VERIFY_ROLE_ID = 1501983948111352091 

user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)
feedback_cooldowns = {}

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

# --- פונקציית הגנה אקטיבית לאונר + לוגים ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    # בדיקה אם למשתמש יש רול בשם Owner או שהוא בעל השרת
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    # דיווח מיידי לערוץ לוגים
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        now = datetime.now(timezone.utc).strftime('%H:%M:%S | %d/%m/%Y')
        embed = discord.Embed(title="🚫 ניסיון פריצה לפקודה", color=0xff0000)
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="פקודה חסומה:", value=f"/{interaction.command.name}", inline=False)
        embed.add_field(name="זמן ניסיון:", value=now, inline=False)
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **זו פקודה ל-OWNER בלבד!** ניסיון נוסף יוביל לאזהרה.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **אזהרה רשמית!** הניסיון שלך דווח לצוות. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- מערכת פידבק נגישה (חלון + אנונימיות) ---
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד לנו?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="להישאר אנונימי? (כן / לא)", placeholder="כתוב 'כן' להסתרה", default="לא", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        last = feedback_cooldowns.get(interaction.user.id)
        if last and (now - last).seconds < 300:
            return await interaction.response.send_message(f"⏳ קולדאון של 5 דקות! נסה שוב בעוד {300 - (now - last).seconds} שניות.", ephemeral=True)

        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anon.value.strip() == "כן"
            name = "Anonymous User 👤" if is_anon else interaction.user.name
            icon = "https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url
            emb = discord.Embed(title="📝 פידבק חדש התקבל", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            emb.set_author(name=name, icon_url=icon)
            await ch.send(embed=emb, view=QuickFeedbackView())
            feedback_cooldowns[interaction.user.id] = now
            await interaction.response.send_message("✅ הפידבק שלך נשלח בהצלחה!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="main_fb")
    async def fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

class QuickFeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.gray, custom_id="quick_fb")
    async def q_fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

# --- מערכת אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("✅ אומתת בהצלחה! ברוך הבא לשרת.", ephemeral=True)

# --- פקודות Slash מפורטות ---

@bot.tree.command(name="setup_feedback", description="[OWNER] הקמת פאנל שליחת פידבקים בערוץ")
async def sf(i: discord.Interaction): 
    if await check_is_owner(i): 
        await i.channel.send(embed=discord.Embed(title="New Feedback", description="לחצו למטה כדי לשלוח פידבק!", color=0x3498db), view=FeedbackView())
        await i.response.send_message("הפאנל הוקם!", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[OWNER] הקמת פאנל אימות כניסה לשרת")
async def sv(i: discord.Interaction): 
    if await check_is_owner(i): 
        await i.channel.send(embed=discord.Embed(title="🛡️ מערכת אימות", description="לחץ על הכפתור כדי לקבל גישה", color=0x2ecc71), view=VerifyView())
        await i.response.send_message("פאנל האימות הוקם!", ephemeral=True)

@bot.tree.command(name="ban", description="[OWNER] חסימת משתמש מהשרת לצמיתות")
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    if await check_is_owner(i): await member.ban(reason=reason); await i.response.send_message(f"🚫 {member.mention} נחסם מהשרת.")

@bot.tree.command(name="kick", description="[OWNER] בעיטת משתמש מהשרת (יכול לחזור)")
async def kick(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i): await member.kick(); await i.response.send_message(f"👞 {member.mention} נזרק מהשרת.")

@bot.tree.command(name="mute", description="[OWNER] השתקת משתמש לזמן מוגדר (דקות)")
async def mute(i: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(i): await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

@bot.tree.command(name="unmute", description="[OWNER] ביטול השתקה של משתמש")
async def unmute(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i): await member.timeout(None); await i.response.send_message(f"🔊 ההשתקה בוטלה עבור {member.mention}.")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות בכמות גדולה מהערוץ")
async def clear(i: discord.Interaction, amount: int):
    if await check_is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="warn", description="[OWNER] מתן אזהרה רשמית למשתמש")
async def warn(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i): user_warnings[member.id] += 1; await i.response.send_message(f"⚠️ {member.mention} הוזהר! (מצב: {user_warnings[member.id]}/5)")

@bot.tree.command(name="clear_warns", description="[OWNER] איפוס כל האזהרות של משתמש")
async def cw(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i): user_warnings[member.id] = 0; await i.response.send_message(f"✅ כל האזהרות של {member.mention} נמחקו.")

@bot.tree.command(name="lock", description="[OWNER] נעילת הערוץ לכתיבה עבור משתמשים רגילים")
async def lock(i: discord.Interaction):
    if await check_is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock", description="[OWNER] פתיחת הערוץ שננעל")
async def unlock(i: discord.Interaction):
    if await check_is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 הערוץ נפתח.")

@bot.tree.command(name="slowmode", description="[OWNER] הגדרת מצב איטי לערוץ (שניות)")
async def slow(i: discord.Interaction, seconds: int):
    if await check_is_owner(i): await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ מצב איטי הוגדר ל-{seconds} שניות.")

@bot.tree.command(name="warnings", description="בדיקת כמות האזהרות של משתמש או של עצמך")
async def check_w(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    await i.response.send_message(f"📋 למשתמש {m.mention} יש **{user_warnings[m.id]}** אזהרות.")

@bot.tree.command(name="ping", description="בדיקת מהירות התגובה (Latency) של הבוט")
async def ping(i: discord.Interaction): await i.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="userinfo", description="קבלת פרטים טכניים על משתמש")
async def uinfo(i: discord.Interaction, member: discord.Member):
    emb = discord.Embed(title=f"מידע: {member.name}", color=0x00ff00)
    emb.add_field(name="ID", value=member.id)
    emb.add_field(name="תאריך כניסה", value=member.joined_at.strftime("%d/%m/%Y"))
    await i.response.send_message(embed=emb)

@bot.tree.command(name="serverinfo", description="קבלת פרטים על השרת הנוכחי")
async def sinfo(i: discord.Interaction):
    emb = discord.Embed(title=f"מידע שרת: {i.guild.name}", color=0x00ffff)
    emb.add_field(name="מספר חברים", value=i.guild.member_count)
    await i.response.send_message(embed=emb)

# --- אירועים אוטומטיים ---
@bot.event
async def on_member_join(member):
    # Alt Detector ללוג האבטחה
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = (datetime.now(timezone.utc) - member.created_at).days
        status = "⚠️ חשבון חשוד (חדש)!" if age < 3 else "✅ חשבון תקין"
        await log_ch.send(f"👤 **משתמש חדש:** {member.mention} | **גיל חשבון:** {age} ימים | **סטטוס:** {status}")
    
    # הודעת וולקם
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"**ברוך הבא {member.mention} לשרת! 🔥**", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    # רישום מחדש של כפתורים אחרי הפעלה
    bot.add_view(VerifyView())
    bot.add_view(FeedbackView())
    bot.add_view(QuickFeedbackView())
    print(f"🛡️ Cyber-Shield Pro IS FULLY ONLINE AND SYNCED!")

if TOKEN: bot.run(TOKEN)
