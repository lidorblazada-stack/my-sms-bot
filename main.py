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

# --- 2. מפת ה-IDs המלאה של לידור ---
CHANNELS = {
    "REPORTS": 1501946934779449505, "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620, "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380, "WELCOME": 1501713652217282591,
    "SUGGESTIONS": 1501947249658429470, "LEADERBOARD": 1502014872655888554 
}
ROLES = {
    "OWNER": 1499868525844627478, "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380, "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255
}
OWNER_ID = 1130542850883469443

# --- 3. מודאלים (חלונות קופצים) ---

class ReportModal(ui.Modal, title="דיווח על שחקן"):
    target = ui.TextInput(label="שם השחקן המדווח", placeholder="לדוגמה: Nehoray#0001")
    reason = ui.TextInput(label="סיבת הדיווח", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention)
        embed.add_field(name="על שחקן:", value=self.target.value)
        embed.add_field(name="סיבה:", value=self.reason.value, inline=False)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח נשלח לצוות.", ephemeral=True)

class FeedbackModal(ui.Modal, title="שליחת פידבק"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anonymous = ui.TextInput(label="אנונימי? (כן/לא)", max_length=2, default="לא")
    async def on_submit(self, i):
        user = "אנונימי" if self.anonymous.value == "כן" else i.user.name
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"נשלח על ידי: {user}")
        view = ui.View()
        view.add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.link, url=i.channel.jump_url))
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        await i.response.send_message("תודה על הפידבק!", ephemeral=True)

# --- 4. פאנלים (Views) ---

class AntiAltView(ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף (Kick)", style=discord.ButtonStyle.danger)
    async def kick(self, i, b):
        await self.member.kick(); await i.response.send_message("המשתמש הועף.", ephemeral=True)
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success)
    async def keep(self, i, b): await i.response.send_message("המשתמש אושר.", ephemeral=True)
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary)
    async def suspect(self, i, b):
        await self.member.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("ניתן רול חשוד.", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎁 בונוס יומי (1,000)", style=discord.ButtonStyle.success, custom_id="daily_btn")
    async def daily(self, i, b):
        # כאן תבוא בדיקת 24 שעות ב-Firebase
        await i.response.send_message("🎁 קיבלת 1,000 מטבעות! (ניתן לקחת פעם ב-24 שעות)", ephemeral=True)
    @ui.button(label="💼 עבודה", style=discord.ButtonStyle.primary, custom_id="work_btn")
    async def work(self, i, b):
        await i.response.send_message(f"💰 הרווחת {random.randint(100, 350)}!", ephemeral=True)
    @ui.button(label="🎫 Staff Role (25k)", style=discord.ButtonStyle.secondary, custom_id="buy_staff")
    async def staff(self, i, b): await i.response.send_message("🛒 בודק יתרה...", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def bank(self, i, b): await i.response.send_message("🚨 פורץ לכספת הבנק...", ephemeral=True)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h_user")
    async def rob(self, i, b): await i.response.send_message("🔫 בחר משתמש לשדידה...", ephemeral=True)

class SupportPanel(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger)
    async def rep(self, i, b): await i.response.send_modal(ReportModal())
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary)
    async def feed(self, i, b): await i.response.send_modal(FeedbackModal())

# --- 5. הבוט הראשי ---

class RailiwayMaster(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.add_view(SupportPanel()); self.update_lb.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_lb(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת העשירים - Top 10", color=0xffd700, timestamp=datetime.now())
            embed.description = "1. `Nehoray` - 💰 1,000,000\n2. `Lidor` - 💰 950,000"
            async for m in ch.history(limit=10):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = RailiwayMaster()

# --- 6. פקודות סטאפ ---

@bot.tree.command(name="setup_all", description="הקמת כל הפאנלים במכה")
async def setup_all(i):
    if i.user.id != OWNER_ID: return
    # שופ
    shop_e = discord.Embed(title="🛒 Railiway Shop", description="חנות השרת ומרכז הכלכלה", color=0x5865f2)
    await i.channel.send(embed=shop_e, view=ShopView())
    # תמיכה
    sup_e = discord.Embed(title="📩 תמיכה ודיווחים", description="לחצו למטה כדי לדווח או לתת פידבק", color=0x00fbff)
    await i.channel.send(embed=sup_e, view=SupportPanel())
    # אייסט
    heist_e = discord.Embed(title="🔫 עולם הפשע", description="שדידות בנק ומשתמשים", color=0x000000)
    await i.channel.send(embed=heist_e, view=HeistView())
    await i.response.send_message("כל הפאנלים הוקמו!", ephemeral=True)

# --- 7. אירועים (אלט, וולקם, לוגים) ---

@bot.event
async def on_member_join(m):
    # Welcome
    await m.guild.get_channel(CHANNELS["WELCOME"]).send(f"👋 ברוך הבא {m.mention} לשרת!")
    # Anti-Alt
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        embed = discord.Embed(title="🚨 זיהוי אלט חשוד", description=f"המשתמש {m.mention} הצטרף עם חשבון חדש!", color=0xff0000)
        await m.guild.get_channel(CHANNELS["ANTI_ALT"]).send(embed=embed, view=AntiAltView(m))

@bot.event
async def on_app_command_completion(i, cmd):
    ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    embed = discord.Embed(title="🛠️ לוג פקודת אונר", color=0x00ff00, timestamp=datetime.now())
    embed.add_field(name="משתמש:", value=i.user.name)
    embed.add_field(name="פקודה:", value=f"/{cmd.name}")
    await ch.send(embed=embed)

if TOKEN: bot.run(TOKEN)
