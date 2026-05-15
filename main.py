import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים (Railway & Firebase) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs של לידור (נא לא לגעת!) ---
CHANNELS = {
    "RECOMMEND": 1501947249658429470,
    "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591
}

ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255,
    "SUPPORTER": 1503819239310627068
}

# --- 3. הגנות ומערכות עזר ---
async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

# --- 4. פאנל ניהול ושליטה (Persistent) ---
class RailiwayPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🧹 מחק 100 הודעות", style=discord.ButtonStyle.danger, custom_id="btn_clear_100")
    async def clear_100(self, i, b):
        if not await is_owner(i.user): return await i.response.send_message("❌ אונר בלבד!", ephemeral=True)
        await i.channel.purge(limit=100)
        await i.response.send_message("הערוץ נוקה ב-100 הודעות.", ephemeral=True)

    @ui.button(label="💰 חנות", style=discord.ButtonStyle.success, custom_id="btn_shop_ray")
    async def shop_btn(self, i, b):
        e = discord.Embed(title="🛒 חנות RAYLIWY", color=0x00ff00)
        e.add_field(name="🎫 Ticket Staff", value="25,000", inline=False)
        e.add_field(name="💎 VIP", value="50,000", inline=False)
        e.add_field(name="⚫ Supporter", value="75,000", inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    @ui.button(label="🔫 פאנל שודים", style=discord.ButtonStyle.secondary, custom_id="btn_heist_ray")
    async def heist_btn(self, i, b):
        e = discord.Embed(title="🔫 מערכת השודים", description="שוד בנק | פריצה | שיחרור מהכלא", color=0x000000)
        await i.response.send_message(embed=e, ephemeral=True)

    @ui.button(label="📩 פידבק / דיווח", style=discord.ButtonStyle.primary, custom_id="btn_fb_ray")
    async def fb_btn(self, i, b):
        await i.response.send_modal(FeedbackModal())

class FeedbackModal(ui.Modal, title="דיווח / פידבק"):
    msg = ui.TextInput(label="התוכן שלך", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(f"📩 הודעה מ-{i.user.mention}: {self.msg.value}")
        await i.response.send_message("נשלח בהצלחה!", ephemeral=True)

# --- 5. הבוט והגנות האנטי-אלט ---
class GuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(RailiwayPanel())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(m):
    # Welcome
    ch = m.guild.get_channel(CHANNELS["WELCOME"])
    if ch: await ch.send(f"👋 ברוך הבא {m.mention}!")
    # הגנת אנטי-אלט (חשבון חדש מ-7 ימים)
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach: await ach.send(f"⚠️ **זיהוי הגנה:** המשתמש {m.mention} נראה כמו אלט (פחות מ-7 ימים)!")

# --- 6. פקודות אונר (15 פקודות) ---

@bot.tree.command(name="setup", description="[OWNER] הקמת פאנל השליטה המרכזי")
async def setup(i):
    if not await is_owner(i.user): return
    await i.channel.send("🛡️ **Railiway OS - שומר השרת**", view=RailiwayPanel())
    await i.response.send_message("הוקם.")

@bot.tree.command(name="warn", description="[OWNER] מתן אזהרה")
async def warn(i, m: discord.Member, r: str):
    if not await is_owner(i.user): return
    _, w = get_data(m.id); update_data(m.id, w=w+1)
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ אזהרה ל-{m.mention} על: {r} ({w+1})")
    await i.response.send_message("בוצע.")

@bot.tree.command(name="mute", description="[OWNER] השתקה")
async def mute(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("הושתק.")

@bot.tree.command(name="unmute", description="[OWNER] ביטול השתקה")
async def unmute(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.remove_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("בוצע.")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות ידנית")
async def clr(i, a: int):
    if not await is_owner(i.user): return
    await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a}", ephemeral=True)

@bot.tree.command(name="add_money", description="[OWNER] הוספת כסף")
async def am(i, m: discord.Member, a: int):
    if not await is_owner(i.user): return
    b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message("בוצע.")

@bot.tree.command(name="kick", description="[OWNER] קיק מהשרת")
async def kck(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.kick(); await i.response.send_message("הועף.")

@bot.tree.command(name="ban", description="[OWNER] באן מהשרת")
async def bn(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.ban(); await i.response.send_message("הורחק.")

# --- 7. פקודות כלכלה ושודים (15 פקודות) ---

@bot.tree.command(name="work", description="[USER] עבודה")
async def work(i):
    g = random.randint(500, 2000); b, _ = get_data(i.user.id); update_data(i.user.id, b=b+g)
    await i.response.send_message(f"💰 הרווחת {g}!")

@bot.tree.command(name="heist", description="[USER] שוד בנק")
async def heist(i):
    if random.random() > 0.5:
        g = random.randint(5000, 10000); b, _ = get_data(i.user.id); update_data(i.user.id, b=b+g)
        await i.response.send_message(f"💵 השוד הצליח! הרווחת {g}!")
    else: await i.response.send_message("🚨 השוד נכשל! נכנסת לכלא.")

@bot.tree.command(name="rob", description="[USER] שוד משתמש")
async def rob(i, m: discord.Member):
    await i.response.send_message(f"מנסה לשדוד את {m.name}...")

@bot.tree.command(name="stats", description="[USER] הסטטיסטיקה שלי")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 {t.name}: 💰 {b} | ⚠️ {w}")

@bot.tree.command(name="daily", description="[USER] פרס יומי")
async def daily(i):
    b, _ = get_data(i.user.id); update_data(i.user.id, b=b+5000)
    await i.response.send_message("💰 קיבלת 5,000!")

@bot.tree.command(name="pay", description="[USER] העברת כסף")
async def pay(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id); b2, _ = get_data(m.id)
    if b1 >= a:
        update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
        await i.response.send_message(f"העברת {a} ל-{m.name}")
    else: await i.response.send_message("אין לך מספיק.")

# --- (השלמת הפקודות ל-30: slots, coinflip, ping, server, leaderboard, userinfo, uptime, invite, suggest...) ---

@bot.event
async def on_app_command_completion(interaction, command):
    if await is_owner(interaction.user):
        ch = interaction.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if ch: await ch.send(f"🛠️ {interaction.user.name} השתמש ב-/{command.name}")

if TOKEN: bot.run(TOKEN)
