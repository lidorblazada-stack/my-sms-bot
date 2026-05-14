import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# --- משיכת נתונים מ-Railway (בלי לחשוף כלום בקוד!) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG_STR = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

# חיבור ל-Firebase בצורה בטוחה
if FB_CONFIG_STR and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG_STR))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
else:
    print("❌ שגיאה: חסרים משתני סביבה ב-Railway (TOKEN/CONFIG/URL)")

# --- IDs קבועים (אפשר להשאיר בקוד או לשים גם ב-Variables) ---
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380
SUSPECT_ROLE_ID = 1503464176599695380
REPORT_CH_ID = 1501946934779449505
FEEDBACK_CH_ID = 1503475379942461522
MEMBER_ROLE_ID = 1501983948111352091

ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# --- פונקציות מסד נתונים ---
def get_data(uid):
    data = db.reference(f'users/{uid}').get()
    return (data.get('bal', 0), data.get('warns', 0)) if data else (0, 0)

def set_data(uid, bal=None, warns=None):
    ref = db.reference(f'users/{uid}')
    c_bal, c_warns = get_data(uid)
    ref.set({
        'bal': bal if bal is not None else c_bal,
        'warns': warns if warns is not None else c_warns
    })

# --- הגנה על פקודות אונר ---
attack_counts = {}
async def check_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ אין לך גישה!", ephemeral=True)
    attack_counts[i.user.id] = attack_counts.get(i.user.id, 0) + 1
    c = attack_counts[i.user.id]
    log = i.guild.get_channel(LOG_CH_ID)
    if log: await log.send(f"⚠️ ניסיון פריצה: {i.user.mention} ({c}/5)")
    if c == 3: await i.user.timeout(timedelta(days=2))
    elif c >= 5: await i.user.kick(); attack_counts[i.user.id] = 0
    return False

# --- Views (חנות וניהול אלטים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, row=1)
    async def b4(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: `{bal}`", ephemeral=True)
    async def buy(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ חסר כסף!", ephemeral=True)
        set_data(i.user.id, bal=bal-p)
        await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message("✅ נרכש בהצלחה!", ephemeral=True)

class AltView(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.mid)
        if m: await m.kick(); await i.response.send_message("הועף", ephemeral=True); await i.message.delete()
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def s(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        await i.response.send_message("אושר", ephemeral=True); await i.message.delete()
    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def h(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.mid); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.response.send_message("ניתן רול חשוד", ephemeral=True); await i.message.delete()

# --- Bot ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        bal, _ = get_data(msg.author.id)
        set_data(msg.author.id, bal=bal + 5)
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ זיהוי אלט: {member.mention}", view=AltView(member.id))

# --- פקודות (דוגמאות ל-15 הפקודות) ---
@bot.tree.command(name="setup_shop")
async def ss(i):
    if await check_owner(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.add_field(name="🎗️ | Supporter", value="2,000 Coins", inline=False)
        emb.add_field(name="💎 | VIP Member", value="5,000 Coins", inline=False)
        emb.add_field(name="🛠️ | STAFF", value="15,000 Coins", inline=False)
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="stats")
async def st(i):
    b, w = get_data(i.user.id); await i.response.send_message(f"📊 כסף: {b} | אזהרות: {w}", ephemeral=True)

@bot.tree.command(name="warn")
async def wr(i, m: discord.Member, r: str):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, warns=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר ({w+1})")

# תוסיף כאן את שאר הפקודות (clear, ban, kick, mute, וכו') באותו מבנה
bot.run(TOKEN)
