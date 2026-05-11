import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (תחליף במידת הצורך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
IMMORTAL_USER_ID = 1130542850883469443 # ה-ID שחסין לבאן
SECURITY_LOG_ID = 1502014872655888554  # לוגים של אלטים ופריצות
FEEDBACK_CH_ID = 1502028905253699735   # פידבק
REPORTS_CH_ID = 1501946934779449505    # רפורטים
SUGGESTIONS_CH_ID = 1501947249658429470 # המלצות
WELCOME_CH_ID = 1501713652217282591
LEAVE_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
SUSPECT_ROLE_ID = 1503464176599695380  

# הגדרות מערכת
ALT_MIN_DAYS = 7
BAD_WORDS = ["זונה", "מזיין", "נאצי", "כושלאמא", "שרמוטה"]
user_warnings = defaultdict(int)
warn_settings = {"mute_at": 3, "kick_at": 5} 
OWNER_FOOTER = "Developed by Nehoray Owner 👑"

# --- Views & Modals ---

# 🔥 Alt Detector View - מעוצב ומנקה
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def handle_decision(self, i: discord.Interaction, decision: str):
        # מחיקת הודעת הלוג כדי לנקות את הצ'אט
        await i.message.delete()
        
        log_ch = i.guild.get_channel(SECURITY_LOG_ID)
        if log_ch:
            emb = discord.Embed(
                title=f"🛠️ החלטת צוות: {self.member.name}", 
                description=f"המשתמש: {self.member.mention}\nהפעולה: **{decision}**\nהמבצע: {i.user.mention}", 
                color=0x3498db
            )
            emb.set_footer(text=OWNER_FOOTER)
            await log_ch.send(embed=emb)

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger, custom_id="kick_alt")
    async def k(self, i, b):
        try:
            await self.member.kick(reason="Alt Detector: Decision by Staff")
            await self.handle_decision(i, "הועף מהשרת")
        except:
            await i.response.send_message("❌ אין לי הרשאות להעיף אותו.", ephemeral=True)

    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="suspect_alt")
    async def s(self, i, b):
        role = i.guild.get_role(SUSPECT_ROLE_ID)
        if role:
            try:
                await self.member.add_roles(role)
                await self.handle_decision(i, "סומן כחשוד וקיבל רול")
            except:
                await i.response.send_message("❌ בעיה במתן הרול (בדוק הרשאות בוט).", ephemeral=True)
        else:
            await i.response.send_message("❌ לא מצאתי את הרול 'חשוד'.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success, custom_id="keep_alt")
    async def keep(self, i, b):
        await self.handle_decision(i, "אושר ונשאר בשרת")

# --- שאר ה-Views מהקוד הקודם (לא השתנו) ---
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip() == "כן"
        name = "Anonymous User 👤" if is_anon else i.user.name
        emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db)
        emb.set_author(name=name, icon_url="https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else i.user.display_avatar.url)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb, view=QuickFeedbackView())
        await i.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="main_fb")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())

class QuickFeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.gray, custom_id="quick_fb")
    async def q_fb(self, i, b): await i.response.send_modal(FeedbackModal())

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot Setup ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.add_view(FeedbackView())
        self.add_view(QuickFeedbackView())
        # אי אפשר להוסיף AltActionView כאן כי הוא דורש Member דינמי
        await self.tree.sync()

bot = CyberShield()

# --- Helper Functions (מערכת אזהרות) ---
async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    log = guild.get_channel(SECURITY_LOG_ID)
    if log:
        emb = discord.Embed(
            title="⚠️ אזהרה אוטומטית", 
            description=f"משתמש: {member.mention}\nסיבה: {reason}\nאזהרה מספר: {count}", 
            color=0xffa500
        )
        emb.set_footer(text=OWNER_FOOTER)
        await log.send(embed=emb)
    
    if count == warn_settings["mute_at"]:
        await member.timeout(timedelta(hours=24), reason="3 Warnings Threshold")
    elif count >= warn_settings["kick_at"]:
        await member.kick(reason="5 Warnings Limit")

# --- פקודות (הסברים והגנות) ---
@bot.tree.command(name="setup_verify", description="מקים את פאנל האימות (Verify) לכניסה לשרת")
async def s_v(i):
    if i.user.guild_permissions.administrator:
        emb = discord.Embed(title="🛡️ אימות משתמשים", description="לחץ על הכפתור כדי לקבל גישה לשרת", color=0x2ecc71)
        emb.set_footer(text=OWNER_FOOTER)
        await i.channel.send(embed=emb, view=VerifyView())
        await i.response.send_message("פאנל אימות הוקם", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="מקים את פאנל הפידבקים והצעות הייעול")
async def s_f(i):
    if i.user.guild_permissions.administrator:
        emb = discord.Embed(title="🌟 תיבת פידבקים", description="יש לכם הצעה או תלונה? שלחו לנו!", color=0x9b59b6)
        emb.set_footer(text=OWNER_FOOTER)
        await i.channel.send(embed=emb, view=FeedbackView())
        await i.response.send_message("פאנל פידבק הוקם", ephemeral=True)

@bot.tree.command(name="nuke", description="מוחק את הערוץ ויוצר אותו מחדש נקי (לניקוי צ'אט מסיבי)")
async def nuke(i):
    if i.user.guild_permissions.administrator:
        await i.response.defer(ephemeral=True)
        pos = i.channel.position
        new = await i.channel.clone()
        await i.channel.delete()
        await new.edit(position=pos)
        await new.send("🚀 הערוץ נוקה!")

@bot.tree.command(name="warn", description="נותן אזהרה למשתמש (3=מיוט, 5=קיק)")
async def warn(i, member: discord.Member, reason: str):
    if i.user.guild_permissions.manage_messages:
        await add_warning(member, reason, i.guild)
        await i.response.send_message(f"✅ אזהרה נרשמה ל-{member.name}", ephemeral=True)

@bot.tree.command(name="remove_warn", description="מוריד אזהרה אחת למשתמש")
async def r_warn(i, member: discord.Member):
    if i.user.guild_permissions.manage_messages:
        if user_warnings[member.id] > 0: user_warnings[member.id] -= 1
        await i.response.send_message(f"✅ הוסרה אזהרה. מצב נוכחי: {user_warnings[member.id]}", ephemeral=True)

@bot.tree.command(name="clear_warns", description="מאפס את כל האזהרות של משתמש מסוים")
async def c_warns(i, member: discord.Member):
    if i.user.guild_permissions.administrator:
        user_warnings[member.id] = 0; await i.response.send_message(f"✅ אזהרות אופסו ל-{member.name}", ephemeral=True)

@bot.tree.command(name="mute", description="משתיק משתמש בדקות")
async def mute(i, member: discord.Member, minutes: int):
    if i.user.guild_permissions.mute_members:
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.name} הושתק.")

@bot.tree.command(name="unmute", description="משחרר משתמש מהשתקה (Timeout)")
async def unmute(i, member: discord.Member):
    if i.user.guild_permissions.mute_members:
        await member.timeout(None); await i.response.send_message(f"🔊 {member.name} שוחרר")

@bot.tree.command(name="ban", description="חוסם משתמש לצמיתות מהשרת")
async def ban(i, member: discord.Member, reason: str = "ללא"):
    if i.user.guild_permissions.ban_members:
        await member.ban(reason=reason); await i.response.send_message("🚫 נחסם")

@bot.tree.command(name="clear", description="מוחק הודעות")
async def clear(i, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="userinfo", description="מידע על משתמש")
async def u_info(i, member: discord.Member):
    emb = discord.Embed(title=f"מידע: {member.name}", color=member.color)
    emb.add_field(name="ID", value=member.id)
    emb.add_field(name="אזהרות", value=user_warnings[member.id])
    emb.add_field(name="הצטרף", value=member.joined_at.strftime("%d/%m/%Y"))
    emb.set_footer(text=OWNER_FOOTER)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="report", description="דיווח לצוות")
async def rep(i, reason: str):
    ch = i.guild.get_channel(REPORTS_CH_ID)
    emb = discord.Embed(title="🚨 דיווח חדש", description=reason, color=0xff0000)
    emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
    emb.set_footer(text=OWNER_FOOTER)
    await ch.send(embed=emb); await i.response.send_message("נשלח", ephemeral=True)

# פקודות נוספות להשלמת ה-30 (כמו בקוד הקודם)
@bot.tree.command(name="add_role")
async def a_role(i, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.add_roles(role); await i.response.send_message("✅ ניתן רול")

@bot.tree.command(name="avatar")
async def av(i, member: discord.Member = None):
    m = member or i.user; await i.response.send_message(m.display_avatar.url)

# --- Events ---

# 🔥 Anti-Ban למנהל
@bot.event
async def on_member_ban(guild, user):
    if user.id == IMMORTAL_USER_ID:
        try:
            await guild.unban(user, reason="Anti-Ban Protection")
            log = guild.get_channel(SECURITY_LOG_ID)
            if log:
                emb = discord.Embed(title="🛡️ ניסיון באן נבלם!", description=f"המבצע ניסה לחסום את {user.mention} (אונר).\nהבאן בוטל מיידית.", color=0xff0000)
                emb.set_footer(text=OWNER_FOOTER)
                await log.send(embed=emb)
        except:
            pass

@bot.event
async def on_member_join(member):
    # הודעת כניסה מעוצבת
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(
            title=f"🔥 ברוך הבא לשרת ספאמר הכי טוב בארץ 🔥", 
            description=f"שלום {member.mention}, אתה מספר **{member.guild.member_count}** שהצטרף אלינו.\n\nעם אתה מתקשה פתח טיקט לעזרה ונדבר", 
            color=0xff4500
        )
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(content=f"{member.mention}", embed=emb)
    
    # Alt Detector מעוצב
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS or member.avatar is None:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log:
            emb = discord.Embed(title="🚨 זוהה חשבון חשוד (Alt Detected)", color=0xffa500)
            emb.set_thumbnail(url=member.display_avatar.url)
            emb.add_field(name="משתמש", value=f"{member.mention} ({member.id})", inline=False)
            emb.add_field(name="ותק חשבון", value=f"{age.days} ימים", inline=True)
            emb.add_field(name="ללא תמונה", value="כן" if member.avatar is None else "לא", inline=True)
            emb.description = "מה ברצונך לעשות עם המשתמש?"
            emb.set_footer(text=OWNER_FOOTER)
            
            await log.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_member_remove(member):
    # הודעת עזיבה
    ch = member.guild.get_channel(LEAVE_CH_ID)
    if ch:
        emb = discord.Embed(description=f"😢 **{member.name}** עזב.\nנשארנו **{member.guild.member_count}** חברים.", color=0xff4747)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb)

@bot.event
async def on_message(message):
    if message.author.bot: return
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await add_warning(message.author, "שפה בוטה", message.guild)
            return
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"🛡️ THE GODFATHER IS ONLINE | {OWNER_FOOTER}")

if TOKEN: bot.run(TOKEN)
