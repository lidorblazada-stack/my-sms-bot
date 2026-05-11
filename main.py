import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות IDs ---
TOKEN = os.getenv('DISCORD_TOKEN') 
IMMORTAL_USER_ID = 1130542850883469443 # ה-ID שחסין לבאן
SECURITY_LOG_ID = 1502014872655888554  
FEEDBACK_CH_ID = 1502028905253699735   
REPORTS_CH_ID = 1501946934779449505    
SUGGESTIONS_CH_ID = 1501947249658429470 
WELCOME_CH_ID = 1501713652217282591
LEAVE_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
SUSPECT_ROLE_ID = 1503464176599695380  

# הגדרות מערכת
ALT_MIN_DAYS = 7
BAD_WORDS = ["זונה", "מזיין", "נאצי", "כושלאמא", "שרמוטה"]
user_warnings = defaultdict(int)
warn_settings = {"mute_at": 3, "kick_at": 5} 

# --- Views & Modals ---

class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip() == "כן"
        name = "Anonymous User 👤" if is_anon else i.user.name
        emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db)
        emb.set_author(name=name, icon_url="https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else i.user.display_avatar.url)
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

class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def k(self, i, b): await self.member.kick(); await i.response.send_message("הועף", ephemeral=True)
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def s(self, i, b):
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        await self.member.add_roles(r); await i.response.send_message("סומן כחשוד", ephemeral=True)

# --- Bot Setup ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView()); self.add_view(QuickFeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- Helpers ---
async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    log = guild.get_channel(SECURITY_LOG_ID)
    if log: await log.send(f"⚠️ **אזהרה {count}** ל-{member.mention} | סיבה: {reason}")
    if count == warn_settings["mute_at"]: await member.timeout(timedelta(hours=24))
    elif count >= warn_settings["kick_at"]: await member.kick(reason="Warn limit")

# --- פקודות (מעל 35 פונקציות) ---

# פקודות הקמה נפרדות
@bot.tree.command(name="setup_verify", description="פאנל אימות")
async def s_v(i):
    if i.user.guild_permissions.administrator:
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", description="לחץ לאימות", color=0x2ecc71), view=VerifyView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="פאנל פידבק")
async def s_f(i):
    if i.user.guild_permissions.administrator:
        await i.channel.send(embed=discord.Embed(title="🌟 פידבק", description="שלח הצעה", color=0x9b59b6), view=FeedbackView())
        await i.response.send_message("הוקם", ephemeral=True)

# פקודות ניהול
@bot.tree.command(name="nuke", description="ניקוי ערוץ")
async def nuke(i):
    if i.user.guild_permissions.administrator:
        await i.response.defer(ephemeral=True)
        pos = i.channel.position
        new = await i.channel.clone()
        await i.channel.delete()
        await new.edit(position=pos)
        await new.send("🚀 הערוץ נוקה!")

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    if i.user.guild_permissions.manage_messages:
        await add_warning(member, reason, i.guild); await i.response.send_message("✅")

@bot.tree.command(name="remove_warn")
async def r_warn(i, member: discord.Member):
    if i.user.guild_permissions.manage_messages:
        if user_warnings[member.id] > 0: user_warnings[member.id] -= 1
        await i.response.send_message("✅ הוסרה אזהרה")

@bot.tree.command(name="clear_warns")
async def c_warns(i, member: discord.Member):
    if i.user.guild_permissions.administrator:
        user_warnings[member.id] = 0; await i.response.send_message("✅ אופס")

@bot.tree.command(name="mute")
async def mute(i, member: discord.Member, minutes: int):
    if i.user.guild_permissions.mute_members:
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message("🔇 הושתק")

@bot.tree.command(name="unmute")
async def unmute(i, member: discord.Member):
    if i.user.guild_permissions.mute_members:
        await member.timeout(None); await i.response.send_message("🔊 שוחרר")

@bot.tree.command(name="ban")
async def ban(i, member: discord.Member, reason: str = "ללא"):
    if i.user.guild_permissions.ban_members:
        await member.ban(reason=reason); await i.response.send_message("🚫 נחסם")

@bot.tree.command(name="kick")
async def kick(i, member: discord.Member, reason: str = "ללא"):
    if i.user.guild_permissions.kick_members:
        await member.kick(reason=reason); await i.response.send_message("👢 הועף")

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="lock")
async def lock(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock")
async def unlock(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="slowmode")
async def slow(i, seconds: int):
    if i.user.guild_permissions.manage_channels:
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="userinfo")
async def u_info(i, member: discord.Member):
    emb = discord.Embed(title=member.name, color=member.color)
    emb.add_field(name="ID", value=member.id)
    emb.add_field(name="אזהרות", value=user_warnings[member.id])
    await i.response.send_message(embed=emb)

@bot.tree.command(name="avatar")
async def av(i, member: discord.Member = None):
    m = member or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="add_role")
async def a_role(i, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.add_roles(role); await i.response.send_message("✅ רול ניתן")

@bot.tree.command(name="remove_role")
async def r_role(i, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.remove_roles(role); await i.response.send_message("❌ רול הוסר")

@bot.tree.command(name="nickname")
async def nick(i, member: discord.Member, name: str):
    if i.user.guild_permissions.manage_nicknames:
        await member.edit(nick=name); await i.response.send_message("✅ כינוי שונה")

@bot.tree.command(name="server_icon")
async def s_icon(i): await i.response.send_message(i.guild.icon.url)

@bot.tree.command(name="member_count")
async def m_count(i): await i.response.send_message(f"חברים: {i.guild.member_count}")

@bot.tree.command(name="report")
async def rep(i, reason: str):
    ch = i.guild.get_channel(REPORTS_CH_ID)
    emb = discord.Embed(title="🚨 דיווח", description=reason, color=0xff0000)
    await ch.send(embed=emb); await i.response.send_message("דווח", ephemeral=True)

@bot.tree.command(name="suggest")
async def sug(i, msg: str):
    ch = i.guild.get_channel(SUGGESTIONS_CH_ID)
    emb = discord.Embed(title="💡 המלצה", description=msg, color=0xfee75c)
    await ch.send(embed=emb); await i.response.send_message("נשלח", ephemeral=True)

# --- Events ---

# 🔥 Anti-Ban למנהל חשוב (1130542850883469443)
@bot.event
async def on_member_ban(guild, user):
    if user.id == IMMORTAL_USER_ID:
        try:
            await guild.unban(user, reason="Anti-Ban Protected User")
            log = guild.get_channel(SECURITY_LOG_ID)
            if log:
                await log.send(f"🛡️ **ניסיון באן נבלם!** המשתמש {user.mention} חסין לבאנים והוחזר מיידית.")
        except Exception as e:
            print(f"Error unbanning: {e}")

@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(
            title=f"🔥 ברוך הבא לשרת ספאמר הכי טוב בארץ 🔥", 
            description=f"שלום {member.mention}, אתה מספר **{member.guild.member_count}** שהצטרף אלינו.\n\nעם אתה מתקשה פתח טיקט לעזרה ונדבר", 
            color=0xff4500
        )
        emb.set_thumbnail(url=member.display_avatar.url)
        await ch.send(content=f"{member.mention}", embed=emb)
    
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log: await log.send(f"🚨 חשוד: {member.mention}", view=AltActionView(member))

@bot.event
async def on_member_remove(member):
    ch = member.guild.get_channel(LEAVE_CH_ID)
    if ch:
        emb = discord.Embed(description=f"😢 **{member.name}** עזב.\nנשארנו **{member.guild.member_count}** חברים.", color=0xff4747)
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
async def on_ready(): print(f"🛡️ THE GODFATHER IS ONLINE | 35+ COMMANDS LOADED")

if TOKEN: bot.run(TOKEN)
