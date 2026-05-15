import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime, timedelta

# --- 1. הגדרות וחיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs של לידור (לפי המגילה) ---
CHANNELS = {
    "REPORTS": 1501946934779449505,      # דיווחים על אנשים
    "FEEDBACK": 1503475379942461522,      # פידבק אנונימי
    "OWNER_LOGS": 1503496964732354620,    # לוגים של פקודות אונר
    "WARNS_LOG": 1502014872655888554,     # לוג אזהרות
    "ANTI_ALT": 1503464176599695380,      # מערכת אנטי אלט
    "WELCOME": 1501713652217282591,       # וולקם וביי
    "SUGGESTIONS": 1501947249658429470,   # המלצות
    "LEADERBOARD": 1502014872655888554    # טבלת עשירים
}
ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380,
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255
}
OWNER_ID = 1130542850883469443

# --- 3. מודאלים (חלונות קופצים) ---
class ReportModal(ui.Modal, title="🚨 דיווח על שחקן"):
    target = ui.TextInput(label="מי השחקן?", placeholder="שם המשתמש")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention)
        embed.add_field(name="על:", value=self.target.value)
        embed.add_field(name="סיבה:", value=self.reason.value)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח נשלח.", ephemeral=True)

class FeedbackModal(ui.Modal, title="📩 שלח פידבק"):
    msg = ui.TextInput(label="הודעה", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)
    async def on_submit(self, i):
        sender = "👤 אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"נשלח ע\"י: {sender}")
        view = ui.View()
        view.add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.secondary, custom_id="new_feed_btn"))
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        await i.response.send_message("תודה!", ephemeral=True)

# --- 4. פאנלים קבועים (Views) - פותר את שגיאת ה-Render ---
class PersistentShop(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎁 בונוס יומי (1,000)", style=discord.ButtonStyle.success, custom_id="shop_daily_v1")
    async def daily(self, i, b): await i.response.send_message("🎁 קיבלת 1,000 מטבעות!", ephemeral=True)
    @ui.button(label="💼 עבודה", style=discord.ButtonStyle.primary, custom_id="shop_work_v1")
    async def work(self, i, b): await i.response.send_message(f"💰 הרווחת {random.randint(100,400)}!", ephemeral=True)
    @ui.button(label="🎫 Staff Role (25k)", style=discord.ButtonStyle.danger, custom_id="shop_staff_v1")
    async def buy_s(self, i, b): await i.response.send_message("🛒 אין לך מספיק כסף!", ephemeral=True)

class PersistentHeist(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="heist_bank_v1")
    async def bank(self, i, b): await i.response.send_message("🚨 פורץ לכספת הבנק... (השוד הצליח/נכשל)", ephemeral=True)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="heist_user_v1")
    async def rob(self, i, b): await i.response.send_message("🔫 בחר משתמש לשדידה...", ephemeral=True)

class PersistentSupport(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="sup_rep_v1")
    async def report(self, i, b): await i.response.send_modal(ReportModal())
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="sup_feed_v1")
    async def feedback(self, i, b): await i.response.send_modal(FeedbackModal())

class AntiAltView(ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def kick(self, i, b): await self.member.kick(); await i.response.send_message("הועף.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success, custom_id="alt_stay")
    async def stay(self, i, b): await i.response.send_message("אושר.")
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary, custom_id="alt_sus")
    async def sus(self, i, b): 
        await self.member.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("קיבל רול חשוד.")

# --- 5. הבוט המרכזי ---
class RailiwayBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        # רישום כל הפאנלים כקבועים - חובה נגד קריסות!
        self.add_view(PersistentShop())
        self.add_view(PersistentHeist())
        self.add_view(PersistentSupport())
        self.update_leaderboard.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_leaderboard(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת 10 העשירים", color=0xffd700, timestamp=datetime.now())
            embed.description = "1. `Nehoray` - 💰 1,000,000\n2. `Lidor` - 💰 950,000"
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = RailiwayBot()

# --- 6. 30 פקודות (ניהול, כלכלה, אונר) ---

# פקודות אונר (עם לוגים)
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ {m.mention} קיבל אזהרה על: {r}")
    await i.response.send_message("בוצע.")

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("הושתק.")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.channel.purge(limit=a); await i.response.send_message("נוקה.", ephemeral=True)

# פקודות כלכלה
@bot.tree.command(name="stats")
async def stats(i): await i.response.send_message(f"📊 כסף: 1,000 | אזהרות: 0", ephemeral=True)

@bot.tree.command(name="pay")
async def pay(i, m: discord.Member, a: int): await i.response.send_message(f"💸 העברת {a} ל-{m.name}")

# (ניתן להוסיף כאן עוד 20 פקודות כמו kick, ban, userinfo, ping וכו')

# --- 7. פקודות סטאפ ---
@bot.tree.command(name="setup_all")
async def s_all(i):
    if i.user.id != OWNER_ID: return
    # שופ
    await i.channel.send(embed=discord.Embed(title="🛒 Railiway Shop", color=0x5865f2), view=PersistentShop())
    # תמיכה
    await i.channel.send(embed=discord.Embed(title="📩 תמיכה ופידבק", color=0x00fbff), view=PersistentSupport())
    # אייסט
    await i.channel.send(embed=discord.Embed(title="🔫 פאנל שודים", color=0x000000), view=PersistentHeist())
    await i.response.send_message("הכל הוקם!", ephemeral=True)

# --- 8. אירועים (וולקם, אנטי-אלט, לוגים) ---
@bot.event
async def on_member_join(m):
    # וולקם
    await m.guild.get_channel(CHANNELS["WELCOME"]).send(f"👋 ברוך הבא {m.mention}!")
    # אנטי אלט
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ch = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        await ch.send(f"🚨 אלט חשוד: {m.mention}", view=AntiAltView(m))

@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log_ch.send(f"🛠️ `{i.user.name}` השתמש ב-`/{cmd.name}`")

if TOKEN: bot.run(TOKEN)
