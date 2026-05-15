import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime, timedelta

# --- 1. חיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs של RAYLIWY ---
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

# --- 3. פונקציות עזר ונתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 4. מערכות פאנלים (Persistent Views) ---

class RAYLIWY_System(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="ray_fb")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="ray_rp")
    async def rp(self, i, b): await i.response.send_modal(ReportModal())

class FeedbackModal(ui.Modal, title="פידבק ל-RAYLIWY"):
    msg = ui.TextInput(label="הודעה", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא")
    async def on_submit(self, i):
        user_info = "🤫 אנונימי" if self.anon.value == "כן" else i.user.mention
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"מאת: {user_info}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=RAYLIWY_System())
        await i.response.send_message("נשלח!", ephemeral=True)

class ReportModal(ui.Modal, title="דיווח על שחקן"):
    target = ui.TextInput(label="מי המטרה?")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח רשמי", color=0xff0000)
        embed.add_field(name="👤 מדווח", value=i.user.mention).add_field(name="🎯 נגד", value=self.target.value)
        embed.add_field(name="📄 סיבה", value=self.reason.value)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח התקבל.", ephemeral=True)

# --- 5. הגדרת הבוט ---
class RayliwyBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(RAYLIWY_System())
        await self.tree.sync()

bot = RayliwyBot()

# --- 6. פקודות ניהול ואונר (15 פקודות) ---
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if not await is_owner(i.user): return
    _, w = get_data(m.id); update_data(m.id, w=w+1)
    e = discord.Embed(title="⚠️ אזהרה", description=f"משתמש: {m.mention}\nסיבה: {r}\nאזהרה: {w+1}", color=0xffa500)
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(embed=e)
    if w+1 >= 3: await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("בוצע.")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if not await is_owner(i.user): return
    await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a} הודעות.", ephemeral=True)

@bot.tree.command(name="add_money")
async def am(i, m: discord.Member, a: int):
    if not await is_owner(i.user): return
    b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message("בוצע.")

@bot.tree.command(name="remove_money")
async def rm(i, m: discord.Member, a: int):
    if not await is_owner(i.user): return
    b, _ = get_data(m.id); update_data(m.id, b=max(0, b-a)); await i.response.send_message("בוצע.")

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"])); await i.response.send_message("הושתק.")

@bot.tree.command(name="unmute")
async def unmute(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.remove_roles(i.guild.get_role(ROLES["MUTE"])); await i.response.send_message("בוצע.")

@bot.tree.command(name="setup_rayliwy")
async def setup(i):
    if not await is_owner(i.user): return
    await i.channel.send("⚙️ **מערכת RAYLIWY: שליטה ובקרה**", view=RAYLIWY_System())
    await i.response.send_message("הוקם.")

@bot.tree.command(name="kick")
async def kck(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.kick(); await i.response.send_message("הועף.")

@bot.tree.command(name="ban")
async def bn(i, m: discord.Member):
    if not await is_owner(i.user): return
    await m.ban(); await i.response.send_message("הורחק.")

# --- 7. פקודות כלכלה ומשתמש (15 פקודות) ---
@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **{t.name}**\n💰 כסף: {b}\n⚠️ אזהרות: {w}")

@bot.tree.command(name="work")
async def wrk(i):
    g = random.randint(500, 2000); b, _ = get_data(i.user.id); update_data(i.user.id, b=b+g)
    await i.response.send_message(f"עבדת והרווחת {g} מטבעות!")

@bot.tree.command(name="shop")
async def shp(i):
    e = discord.Embed(title="🛒 חנות RAYLIWY", color=0x00ff00)
    e.add_field(name="🎫 Ticket Staff", value="25,000", inline=False)
    e.add_field(name="💎 VIP", value="50,000", inline=False)
    e.add_field(name="⚫ Supporter", value="75,000", inline=False)
    await i.response.send_message(embed=e)

@bot.tree.command(name="buy")
async def buy(i, item: str):
    b, _ = get_data(i.user.id)
    prices = {"staff": 25000, "vip": 50000, "supporter": 75000}
    if item.lower() in prices and b >= prices[item.lower()]:
        update_data(i.user.id, b=b-prices[item.lower()])
        await i.response.send_message(f"קנית {item} בהצלחה!")
    else: await i.response.send_message("אין מספיק כסף או פריט לא קיים.")

@bot.tree.command(name="daily")
async def dly(i):
    b, _ = get_data(i.user.id); update_data(i.user.id, b=b+5000)
    await i.response.send_message("קיבלת 5,000 מטבעות יומיים!")

@bot.tree.command(name="pay")
async def py(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id)
    if b1 >= a:
        b2, _ = get_data(m.id); update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
        await i.response.send_message(f"העברת {a} ל-{m.name}")
    else: await i.response.send_message("אין לך מספיק.")

# --- 8. אירועי מערכת ---
@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(CHANNELS["WELCOME"])
    if ch: await ch.send(f"👋 ברוך הבא {m.mention} ל-RAYLIWY!")
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach: await ach.send(f"⚠️ **חשוד:** {m.mention} נרשם לאחרונה.")

@bot.event
async def on_app_command_completion(interaction, command):
    if await is_owner(interaction.user):
        ch = interaction.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if ch: await ch.send(f"🛠️ {interaction.user.name} השתמש ב-/{command.name}")

if TOKEN: bot.run(TOKEN)
