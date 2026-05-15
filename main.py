import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. הגדרות וחיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs של לידור ---
CHANNELS = {
    "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591,
    "SUGGESTIONS": 1501947249658429470,
    "LEADERBOARD": 1502014872655888554 
}
ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380
}
OWNER_ID = 1130542850883469443

# --- 3. מודאלים (חלונות קופצים) ---
class ReportModal(ui.Modal, title="🚨 דיווח על שחקן"):
    target = ui.TextInput(label="על מי הדיווח?", placeholder="שם המשתמש")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention)
        embed.add_field(name="על המשתמש:", value=self.target.value)
        embed.add_field(name="סיבת הדיווח:", value=self.reason.value, inline=False)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח נשלח לצוות.", ephemeral=True)

class FeedbackModal(ui.Modal, title="📩 שלח פידבק"):
    msg = ui.TextInput(label="מה הפידבק שלך?", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)
    async def on_submit(self, i):
        sender = "👤 אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"נשלח ע\"י: {sender}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed)
        await i.response.send_message("תודה על הפידבק!", ephemeral=True)

# --- 4. פאנלים קבועים (Views) ---
class PersistentShop(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎁 בונוס יומי (1,000)", style=discord.ButtonStyle.success, custom_id="daily_p")
    async def daily(self, i, b): await i.response.send_message("🎁 קיבלת 1,000 מטבעות!", ephemeral=True)
    @ui.button(label="💼 עבודה", style=discord.ButtonStyle.primary, custom_id="work_p")
    async def work(self, i, b): await i.response.send_message(f"💰 הרווחת {random.randint(100,300)}!", ephemeral=True)

class PersistentHeist(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="bank_p")
    async def bank(self, i, b): await i.response.send_message("🚨 פורץ לכספת...", ephemeral=True)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="rob_p")
    async def rob(self, i, b): await i.response.send_message("🔫 בחר משתמש לשדידה...", ephemeral=True)

class PersistentSupport(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="rep_p")
    async def report(self, i, b): await i.response.send_modal(ReportModal())
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="feed_p")
    async def feedback(self, i, b): await i.response.send_modal(FeedbackModal())

# --- 5. הבוט המרכזי ---
class RailiwayBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        # רישום כל הפאנלים כקבועים כדי שלא יקרוס ב-Render
        self.add_view(PersistentShop())
        self.add_view(PersistentHeist())
        self.add_view(PersistentSupport())
        self.update_leaderboard.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_leaderboard(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת 10 העשירים (מתעדכן)", color=0xffd700, timestamp=datetime.now())
            embed.description = "1. `Nehoray` - 💰 1,000,000\n2. `Lidor` - 💰 950,000"
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = RailiwayBot()

# --- 6. 30 פקודות (ניהול, כלכלה, מידע) ---
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ {m.mention} הוזהר על: {r}")
    await i.response.send_message(f"נתת אזהרה ל-{m.name}")

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message(f"🔇 {m.name} הושתק.")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a} הודעות.", ephemeral=True)

# ... (כאן אתה יכול להוסיף את שאר ה-30 פקודות כמו ping, kick, ban, stats וכו')

# --- 7. פקודות סטאפ ---
@bot.tree.command(name="setup_shop")
async def s_shop(i):
    if i.user.id != OWNER_ID: return
    await i.channel.send(embed=discord.Embed(title="🛒 שופ וכלכלה", color=0x5865f2), view=PersistentShop())
    await i.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="setup_support")
async def s_sup(i):
    if i.user.id != OWNER_ID: return
    await i.channel.send(embed=discord.Embed(title="📩 תמיכה ופידבק", color=0x00fbff), view=PersistentSupport())
    await i.response.send_message("בוצע.", ephemeral=True)

# לוג אונר אוטומטי
@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    if log_ch:
        await log_ch.send(f"🛠️ **לוג פקודה:** `{i.user.name}` השתמש ב-`/{cmd.name}` ב- {datetime.now().strftime('%H:%M')}")

if TOKEN: bot.run(TOKEN)
