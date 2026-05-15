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

# --- 2. מפת ה-IDs של לידור (מעודכן) ---
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

# --- 3. פאנלים (Views) - עם custom_id למניעת השגיאה ---

class SupportPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # חשוב ל-Persistent View

    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="btn_rep_v1")
    async def report(self, i, b):
        await i.response.send_modal(ReportModal())

    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="btn_feed_v1")
    async def feedback(self, i, b):
        await i.response.send_modal(FeedbackModal())

# --- 4. מודאלים (חלונות קופצים) ---
class ReportModal(ui.Modal, title="דיווח על שחקן"):
    target = ui.TextInput(label="שם השחקן", placeholder="לדוגמה: Nehoray")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention)
        embed.add_field(name="על:", value=self.target.value)
        embed.add_field(name="סיבה:", value=self.reason.value)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח נשלח.", ephemeral=True)

class FeedbackModal(ui.Modal, title="פידבק לשרת"):
    msg = ui.TextInput(label="תוכן הפידבק", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)
    async def on_submit(self, i):
        name = "אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"מאת: {name}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed)
        await i.response.send_message("תודה על הפידבק!", ephemeral=True)

# --- 5. הבוט ופקודות האונר ---

class RailiwayBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # רישום הפאנלים כקבועים
        self.add_view(SupportPanel())
        # כאן תוסיף עוד add_view לשאר הפאנלים (Shop, Heist וכו')
        self.update_lb.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_lb(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת עשירים (מתעדכן)", color=0xffd700)
            embed.description = "1. `Lidor` - 1,000,000\n2. `Nehoray` - 500,000"
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = RailiwayBot()

# --- פקודות ניהול (לוגים אוטומטיים) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
async def warn(i, m: discord.Member, r: str):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    # לוג אונר
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log_ch.send(f"🛠️ **לוג:** {i.user.name} נתן אזהרה ל-{m.name} | סיבה: {r}")
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ {m.mention} הוזהר: {r}")
    await i.response.send_message("בוצע.")

# --- פקודות סטאפ ---
@bot.tree.command(name="setup_support", description="הקמת פאנל תמיכה")
async def s_sup(i):
    if i.user.id != OWNER_ID: return
    await i.channel.send("📩 **תמיכה ופידבק**", view=SupportPanel())
    await i.response.send_message("הוקם.", ephemeral=True)

if TOKEN: bot.run(TOKEN)
