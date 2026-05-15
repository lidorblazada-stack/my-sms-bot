import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים ומשתני סביבה ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs המדויקת של לידור ---
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

# --- 3. ניהול נתונים וקירור ---
feedback_cooldown = {}
rob_cooldown = {}
work_cooldown = {}
jail_list = {}

def get_data(uid):
    try:
        d = db.reference(f'users/{uid}').get()
        if d: return d.get('bal', 0), d.get('warns', 0)
    except: pass
    return 0, 0

def update_data(uid, b=None, w=None):
    try:
        ref = db.reference(f'users/{uid}')
        curr_b, curr_w = get_data(uid)
        ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})
    except: pass

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 4. מודאלים ופאנלים (Views) ---

class FeedbackModal(ui.Modal, title="שליחת פידבק"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא")
    async def on_submit(self, i):
        now = datetime.now().timestamp()
        if i.user.id in feedback_cooldown and now - feedback_cooldown[i.user.id] < 300:
            return await i.response.send_message("מותר פידבק פעם ב-5 דקות אחי.", ephemeral=True)
        user_info = "🤫 אנונימי" if self.anon.value == "כן" else i.user.mention
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"מאת: {user_info}")
        view = ui.View(timeout=None).add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.primary, custom_id="btn_fb"))
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        feedback_cooldown[i.user.id] = now
        await i.response.send_message("נשלח!", ephemeral=True)

class ReportModal(ui.Modal, title="דיווח על משתמש"):
    target = ui.TextInput(label="על מי?")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח רשמי", color=0xff0000)
        embed.add_field(name="מדווח", value=i.user.mention).add_field(name="נגד", value=self.target.value)
        embed.add_field(name="סיבה", value=self.reason.value, inline=False)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("דווח לצוות.", ephemeral=True)

class AntiAltView(ui.View):
    def __init__(self, m):
        super().__init__(timeout=None)
        self.m = m
    @ui.button(label="Kick", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        if await is_owner(i.user): await self.m.kick(); await i.response.send_message("הועף.")
    @ui.button(label="Keep", style=discord.ButtonStyle.success)
    async def s(self, i, b):
        if await is_owner(i.user): await i.response.send_message("אושר.")

# --- 5. הגדרת הבוט ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(AntiAltView(None))
        await self.tree.sync()

bot = GuardBot()

# --- 6. פקודות אונר וניהול ---

@bot.tree.command(name="setup_feedback")
async def s_fb(i):
    if not await is_owner(i.user): return
    v = ui.View(timeout=None).add_item(ui.Button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="btn_fb"))
    await i.channel.send("📩 **מרכז הפידבקים**", view=v); await i.response.send_message("הוקם")

@bot.tree.command(name="setup_report")
async def s_rp(i):
    if not await is_owner(i.user): return
    v = ui.View(timeout=None).add_item(ui.Button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="btn_rp"))
    await i.channel.send("🚨 **מרכז הדיווחים**", view=v); await i.response.send_message("הוקם")

@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if not await is_owner(i.user): return
    _, w = get_data(m.id); update_data(m.id, w=w+1)
    e = discord.Embed(title="⚠️ אזהרה", description=f"למשתמש: {m.mention}\nסיבה: {r}\nאזהרות: {w+1}", color=0xffa500)
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(embed=e)
    if w+1 >= 3: await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("אזהרה נרשמה.")

@bot.tree.command(name="clear")
async def clr(i, amount: int):
    if not await is_owner(i.user): return
    await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="add_money")
async def am(i, m: discord.Member, a: int):
    if not await is_owner(i.user): return
    b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message("בוצע")

# --- 7. פקודות כלכלה ומשתמש ---

@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **{t.name}**\n💰 כסף: {b}\n⚠️ אזהרות: {w}")

@bot.tree.command(name="work")
async def wrk(i):
    now = datetime.now().timestamp()
    if i.user.id in work_cooldown and now - work_cooldown[i.user.id] < 3600:
        return await i.response.send_message("חכה שעה!", ephemeral=True)
    gain = random.randint(500, 1500); b, _ = get_data(i.user.id); update_data(i.user.id, b=b+gain)
    work_cooldown[i.user.id] = now
    await i.response.send_message(f"עבדת והרווחת {gain} מטבעות!")

@bot.tree.command(name="rob")
async def rb(i, m: discord.Member):
    if i.user.id in rob_cooldown and datetime.now().timestamp() - rob_cooldown[i.user.id] < 3600:
        return await i.response.send_message("חכה שעה!", ephemeral=True)
    b1, _ = get_data(i.user.id); b2, _ = get_data(m.id)
    if b2 < 1000: return await i.response.send_message("הוא עני.", ephemeral=True)
    rob_cooldown[i.user.id] = datetime.now().timestamp()
    if random.random() < 0.3:
        win = int(b2 * 0.2); update_data(i.user.id, b=b1+win); update_data(m.id, b=b2-win)
        await i.response.send_message(f"גנבת {win} מ-{m.name}!")
    else:
        jail_list[i.user.id] = 5000; await i.response.send_message("נתפסת! עפת לכלא.")

# --- 8. אירועים (Welcome/Alt/Logs) ---

@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(CHANNELS["WELCOME"])
    if ch: await ch.send(f"ברוך הבא {m.mention} לאימפריה!")
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach: await ach.send(f"⚠️ חשוד: {m.mention}", view=AntiAltView(m))

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == "btn_fb": await interaction.response.send_modal(FeedbackModal())
        elif interaction.data['custom_id'] == "btn_rp": await interaction.response.send_modal(ReportModal())

@bot.event
async def on_app_command_completion(interaction, command):
    if await is_owner(interaction.user):
        ch = interaction.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if ch: await ch.send(f"🛠️ {interaction.user.name} השתמש ב-/{command.name}")

# --- 9. הפעלה ---
if TOKEN:
    bot.run(TOKEN)
