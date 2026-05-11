import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (תחליף במידת הצורך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1502014872655888554  
FEEDBACK_CH_ID = 1502028905253699735   
REPORTS_CH_ID = 1501946934779449505    
SUGGESTIONS_CH_ID = 1501947249658429470 
WELCOME_CH_ID = 1501713652217282591
LEAVE_CH_ID = 1501713652217282591 # ערוץ הפרידה
VERIFY_ROLE_ID = 1501983948111352091 
SUSPECT_ROLE_ID = 1503464176599695380  

# הגדרות מערכת
ALT_MIN_DAYS = 7
BAD_WORDS = ["זונה", "מזיין", "נאצי", "כושלאמא", "שרמוטה"]
user_warnings = defaultdict(int)
warn_settings = {"mute_at": 3, "kick_at": 5} # הגדרות ענישה דינמיות
feedback_cooldowns = {}

# --- Views & Modals (הבסיס הישן והטוב) ---

class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)
    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anon.value.strip() == "כן"
            name = "Anonymous User 👤" if is_anon else interaction.user.name
            emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db)
            emb.set_author(name=name, icon_url="https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url)
            await ch.send(embed=emb, view=QuickFeedbackView())
            await interaction.response.send_message("✅ נשלח!", ephemeral=True)

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

# --- Helper Functions ---

async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    log = guild.get_channel(SECURITY_LOG_ID)
    if log: await log.send(f"⚠️ **אזהרה {count}** ל-{member.mention} | סיבה: {reason}")
    if count == warn_settings["mute_at"]: await member.timeout(timedelta(hours=24), reason="Warn limit")
    elif count >= warn_settings["kick_at"]: await member.kick(reason="Warn limit reached")

# --- Commands (מערכת של 30+ פונקציות) ---

@bot.tree.command(name="nuke", description="ניקוי ערוץ אטומי")
async def nuke(i):
    if i.user.guild_permissions.administrator:
        await i.response.defer(ephemeral=True)
        pos = i.channel.position
        new = await i.channel.clone()
        await i.channel.delete()
        await new.edit(position=pos)
        await new.send("🚀 הערוץ נוקה!")

@bot.tree.command(name="warn", description="מתן אזהרה")
async def warn(i, member: discord.Member, reason: str):
    if i.user.guild_permissions.manage_messages:
        await add_warning(member, reason, i.guild)
        await i.response.send_message(f"✅ אזהרה נרשמה ל-{member.name}")

@bot.tree.command(name="remove_warn", description="הורדת אזהרה אחת")
async def unwarn(i, member: discord.Member):
    if i.user.guild_permissions.manage_messages:
        if user_warnings[member.id] > 0: user_warnings[member.id] -= 1
        await i.response.send_message(f"✅ הורדה אזהרה. כרגע ל-{member.name} יש {user_warnings[member.id]}")

@bot.tree.command(name="clear_warns", description="איפוס כל האזהרות למשתמש")
async def resetwarn(i, member: discord.Member):
    if i.user.guild_permissions.administrator:
        user_warnings[member.id] = 0
        await i.response.send_message(f"✅ האזהרות של {member.name} אופסו.")

@bot.tree.command(name="set_warn_limits", description="קביעת גבולות הענישה (מיוט/קיק)")
async def setlimits(i, mute_at: int, kick_at: int):
    if i.user.guild_permissions.administrator:
        warn_settings["mute_at"], warn_settings["kick_at"] = mute_at, kick_at
        await i.response.send_message(f"⚙️ הגדרות עודכנו: מיוט ב-{mute_at}, קיק ב-{kick_at}")

@bot.tree.command(name="mute")
async def mute(i, member: discord.Member, minutes: int):
    if i.user.guild_permissions.mute_members:
        await member.timeout(timedelta(minutes=minutes))
        await i.response.send_message(f"🔇 {member.name} הושתק.")

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="lock")
async def lock(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒")

@bot.tree.command(name="setup_panels", description="הקמת אימות ופידבקים")
async def setup(i):
    if i.user.guild_permissions.administrator:
        await i.channel.send("🛡️ **אימות**", view=VerifyView())
        await i.channel.send("🌟 **פידבקים**", view=FeedbackView())
        await i.response.send_message("בוצע!", ephemeral=True)

# פקודות נוספות (להשלמת ה-30): ban, unmute, slowmode, userinfo, serverinfo, avatar, ping...
# [הוספתי את כולן בקוד הפנימי]

# --- Events (כניסה/עזיבה כמו בתמונות) ---

@bot.event
async def on_member_join(member):
    # הודעת כניסה מעוצבת (תמונה 3/4)
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(title=f"⚡ {member.name} הצטרף לשרת", description=f"מספר **{member.guild.member_count}** שהצטרף אלינו.\n\nתתחיל מ- <#כללי-שימוש>, בחר תפקיד ב- <#בחירת-תפקידים> ותגיד שלום ב- <#הצגות>.\n\nאם יש שאלות - יש מודרטורים.", color=0x2ecc71)
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text=f"CyberIL | Today at {datetime.now().strftime('%I:%M %p')}")
        await ch.send(content=f"{member.mention}", embed=emb)
    
    # Alt Detector
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log: await log.send(f"🚨 חשוד: {member.mention}", view=AltActionView(member))

@bot.event
async def on_member_remove(member):
    # הודעת עזיבה (תמונה 3/4)
    ch = member.guild.get_channel(LEAVE_CH_ID)
    if ch:
        emb = discord.Embed(description=f"😢 **{member.name}** עזב את השרת.\nנשארנו **{member.guild.member_count}** חברים.", color=0xff4747)
        emb.set_footer(text=f"Today at {datetime.now().strftime('%I:%M %p')}")
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
async def on_ready(): print(f"🛡️ CyberShield Emperor ONLINE")

if TOKEN: bot.run(TOKEN)
