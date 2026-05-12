import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import asyncio
from collections import defaultdict

# --- IDs והגדרות סופיות ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443 # ה-ID של לידור
SECOND_ID = 1493293951959044147

# ערוצים
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1503475379942461522
RECOMMEND_CH_ID = 1501947249658429470     
REPORT_LOG_CH_ID = 1501946934779449505    
OWNER_LOG_CH_ID = 1503496964732354620     
ALT_DETECTION_LOG = 1503464176599695380   

# רולים
MEMBER_ROLE_ID = 1501983948111352091
SUSPICIOUS_ROLE_ID = 1503464176599695380 
MUTE_2DAYS_ROLE_ID = 1501953906736103535 

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 150131611041 # לפי ה-ID בתמונה

# דאטה-בייס בזיכרון
user_warnings = defaultdict(int)
user_balances = defaultdict(int)
user_xp = defaultdict(int)
user_levels = defaultdict(int)
spam_tracker = defaultdict(list)
last_xp_time = {}

def xp_for_level(level):
    return 100 * (level ** 2) + 500

# --- פונקציית לוג אונר ---
async def send_owner_log(guild, user, command_name, details=""):
    ch = guild.get_channel(OWNER_LOG_CH_ID)
    if ch:
        emb = discord.Embed(title="👑 Owner Action Log", color=0xffd700, timestamp=datetime.utcnow())
        emb.add_field(name="מבצע", value=f"{user.mention}")
        emb.add_field(name="פקודה", value=f"`/{command_name}`")
        if details: emb.add_field(name="פרטים", value=details)
        await ch.send(embed=emb)

# --- Views ---

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_v1")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

class FeedbackReplyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.green, custom_id="fb_v1")
    async def fast_fb(self, i, b): await i.response.send_modal(FeedbackModal())

class FeedbackModal(ui.Modal, title="📤 שלח פידבק"):
    inp = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        emb = discord.Embed(title="💬 פידבק חדש", description=self.inp.value, color=0x00ffff)
        emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        await ch.send(embed=emb, view=FeedbackReplyView())
        await i.response.send_message("נשלח!", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s_1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="s_2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="s_3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="יתרה 💳", style=discord.ButtonStyle.success, custom_id="s_4")
    async def b4(self, i, b): await i.response.send_message(f"💰 יתרה נוכחית: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ אין לך מספיק כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        role = i.guild.get_role(r_id)
        if role: await i.user.add_roles(role)
        await i.response.send_message("✅ תתחדש על הרול!", ephemeral=True)

# --- Bot Core ---
class CyberShieldBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.add_view(FeedbackReplyView())
        self.add_view(ShopView())
        await self.tree.sync()

bot = CyberShieldBot()

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    u_id = msg.author.id
    now = asyncio.get_event_loop().time()
    
    # אנטי-ספאם עם טיימאוט דקה (לידור, זה בול מה שביקשת)
    spam_tracker[u_id].append(now)
    spam_tracker[u_id] = [t for t in spam_tracker[u_id] if now - t < 5]
    if len(spam_tracker[u_id]) > 5:
        try:
            await msg.author.timeout(timedelta(minutes=1), reason="ספאם")
            await msg.channel.send(f"⚠️ {msg.author.mention}, אזהרה מילולית! הושבתת לדקה בגלל ספאם.")
        except: pass
        return

    # כסף ו-XP
    user_balances[u_id] += 10
    user_xp[u_id] += 15
    if user_xp[u_id] >= xp_for_level(user_levels[u_id] + 1):
        user_levels[u_id] += 1
        await msg.channel.send(f"🎊 {msg.author.mention} עלית לרמה {user_levels[u_id]}! 🔥")

    await bot.process_commands(msg)

# --- פקודות (עברית עם OWNER באנגלית) ---

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת חנות הרולים של השרת")
async def ss(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🛒 חנות השרת", color=0xf1c40f), view=ShopView())
    await i.response.send_message("החנות הוקמה!", ephemeral=True)
    await send_owner_log(i.guild, i.user, "setup_shop")

@bot.tree.command(name="setup_verify", description="[OWNER] הקמת מערכת האימות")
async def sv(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🛡️ אימות", description="לחץ על הכפתור למטה כדי לקבל גישה", color=0x2ecc71), view=VerifyView())
    await i.response.send_message("אימות הוקם!", ephemeral=True)
    await send_owner_log(i.guild, i.user, "setup_verify")

@bot.tree.command(name="setup_feedback", description="[OWNER] הקמת מערכת הפידבקים")
async def sf(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="💬 פידבק", description="שלח לנו פידבק על השרת בלחיצה על הכפתור"), view=FeedbackReplyView())
    await i.response.send_message("פידבק הוקם!", ephemeral=True)
    await send_owner_log(i.guild, i.user, "setup_feedback")

@bot.tree.command(name="rank", description="[USER] בדיקת הרמה וה-XP שלך")
async def r(i):
    await i.response.send_message(f"📊 {i.user.mention}, אתה ברמה **{user_levels[i.user.id]}** עם `{user_xp[i.user.id]}` XP.", ephemeral=True)

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה למשתמש וענישה אוטומטית")
async def aw(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    await i.response.send_message(f"המשתמש {member.mention} קיבל אזהרה ({count}/5). סיבה: {reason}")
    await send_owner_log(i.guild, i.user, "add_warn", f"אל: {member.name} | כמות: {count}")

bot.run(TOKEN)
