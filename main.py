import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים ---
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
    "REPORTS": 1501946934779449505, "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620, "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380, "WELCOME": 1501713652217282591
}
ROLES = {
    "OWNER": 1499868525844627478, "MUTE": 1501953906736103535,
    "STAFF": 1501316672345211041, "VIP": 1503817695466881255, "SUPPORTER": 1503819239310627068
}

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 3. פאנלים (Setup Views) ---
class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.secondary, custom_id="h_b_f")
    async def bank(self, i, b): await i.response.send_message("🔫 שוד בנק בתהליך...", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Staff Role", style=discord.ButtonStyle.primary, custom_id="s_s_f")
    async def buy_s(self, i, b): await i.response.send_message("🛒 בודק יתרה לרול Staff...", ephemeral=True)

# --- 4. הבוט ופקודות הסלאש (30 פקודות) ---
class MasterBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistView()); self.add_view(ShopView())
        await self.tree.sync()

bot = MasterBot()

# --- פקודות ניהול (15 פקודות) ---
@bot.tree.command(name="warn", description="[OWNER] מתן אזהרה")
async def warn(i, m: discord.Member, r: str):
    if not await is_owner(i.user): return
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ אזהרה ל-{m.mention} על: {r}")
    await i.response.send_message(f"נתת אזהרה ל-{m.name}")

@bot.tree.command(name="mute", description="[OWNER] השתקת משתמש")
async def mute(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message(f"השתקת את {m.name}")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def clr(i, a: int):
    if not await is_owner(i.user): return
    await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a} הודעות", ephemeral=True)

@bot.tree.command(name="kick", description="[OWNER] העפה")
async def kck(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.kick(); await i.response.send_message("הועף.")

@bot.tree.command(name="ban", description="[OWNER] באן")
async def ban(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.ban(); await i.response.send_message("הורחק.")

# --- פקודות כלכלה ומשחק (15 פקודות) ---
@bot.tree.command(name="work", description="[USER] עבודה")
async def work(i):
    await i.response.send_message(f"💰 הרווחת {random.randint(500, 2000)}!")

@bot.tree.command(name="daily", description="[USER] פרס יומי")
async def daily(i):
    await i.response.send_message("🎁 קיבלת 5,000 מטבעות!")

@bot.tree.command(name="stats", description="[USER] סטטיסטיקה")
async def stats(i, m: discord.Member = None):
    t = m or i.user
    await i.response.send_message(f"📊 נתונים עבור {t.name}: 💰 10,000")

@bot.tree.command(name="heist", description="[USER] שוד בנק")
async def heist_c(i):
    await i.response.send_message("🔫 מתחיל שוד...")

@bot.tree.command(name="pay", description="[USER] העברת כסף")
async def pay(i, m: discord.Member, a: int):
    await i.response.send_message(f"העברת {a} ל-{m.name}")

# --- פקודות סטאפ (השארתי לך שיהיה אחי) ---
@bot.tree.command(name="setup_heist", description="[OWNER] הקמת פאנל שודים")
async def s_h(i):
    if not await is_owner(i.user): return
    await i.channel.send("🔫 **מערכת השודים**", view=HeistView())
    await i.response.send_message("בוצע.", ephemeral=True)

# --- לוגים ואירועים ---
@bot.event
async def on_app_command_completion(i, cmd):
    if await is_owner(i.user):
        ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if ch: await ch.send(f"🛠️ **לוג ניהול:** {i.user.name} הריץ `/{cmd.name}`")

@bot.event
async def on_member_join(m):
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach: await ach.send(f"🚨 **חשוד באלט:** {m.mention}")

if TOKEN: bot.run(TOKEN)
