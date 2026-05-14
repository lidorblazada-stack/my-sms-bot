import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# --- חיבור ל-Firebase ---
fb_config = os.getenv('FIREBASE_CONFIG')
if fb_config:
    cred = credentials.Certificate(json.loads(fb_config))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://vouge-guard-default-rtdb.firebaseio.com/' # תוודא שזה ה-URL שלך
    })
else:
    print("❌ שגיאה: חסר FIREBASE_CONFIG ב-Variables")

# --- הגדרות IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380
SUSPECT_ROLE_ID = 1503464176599695380
REPORT_CH = 1501946934779449505
FEEDBACK_CH = 1503475379942461522
MEMBER_ROLE = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# --- פונקציות ענן ---
def get_data(uid):
    data = db.reference(f'users/{uid}').get()
    return (data.get('bal', 0), data.get('warns', 0)) if data else (0, 0)

def set_data(uid, bal=None, warns=None):
    ref = db.reference(f'users/{uid}')
    c_bal, c_warns = get_data(uid)
    ref.set({'bal': bal if bal is not None else c_bal, 'warns': warns if warns is not None else c_warns})

# --- הגנה על אונר ---
attack_counts = {}
async def check_owner(i):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ אזהרה מילולית! אין לך גישה.", ephemeral=True)
    attack_counts[i.user.id] = attack_counts.get(i.user.id, 0) + 1
    c = attack_counts[i.user.id]
    log = i.guild.get_channel(LOG_CH_ID)
    if log: await log.send(f"⚠️ פריצה: {i.user.mention} ניסה פקודת אונר ({c}/5)")
    if c == 3: await i.user.timeout(timedelta(days=2))
    elif c >= 5: await i.user.kick(); attack_counts[i.user.id] = 0
    return False

# --- Views (חנות ואימות) ---
class ShopV(ui.View):
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
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

class VerifyV(ui.View):
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green)
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE))
        await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot ---
class Guard(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(ShopV()); self.add_view(VerifyV()); await self.tree.sync()

bot = Guard()

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        bal, _ = get_data(msg.author.id)
        set_data(msg.author.id, bal=bal + 5)
    await bot.process_commands(msg)

# --- פקודות ---
@bot.tree.command(name="setup_shop")
async def ss(i):
    if await check_owner(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.add_field(name="🎗️ | Supporter", value="2,000 Coins", inline=False)
        emb.add_field(name="💎 | VIP Member", value="5,000 Coins", inline=False)
        emb.add_field(name="🛠️ | STAFF", value="15,000 Coins", inline=False)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopV()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await check_owner(i): await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="warn")
async def wr(i, m: discord.Member, r: str):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, warns=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר ({w+1}) על: {r}")

@bot.tree.command(name="add_money")
async def am(i, m: discord.Member, a: int):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, bal=b+a)
        await i.response.send_message(f"💵 נוספו {a} ל-{m.name}")

@bot.tree.command(name="report")
async def rep(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(REPORT_CH)
    if ch: await ch.send(f"🚨 דיווח מ{i.user.name} על {m.name}: {r}")
    await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="stats")
async def st(i):
    b, w = get_data(i.user.id)
    await i.response.send_message(f"📊 כסף: {b} | אזהרות: {w}", ephemeral=True)

@bot.tree.command(name="ping")
async def pi(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="anonymous_feedback")
async def af(i, t: str):
    ch = i.guild.get_channel(FEEDBACK_CH)
    if ch: await ch.send(f"🔒 פידבק אנונימי: {t}")
    await i.response.send_message("נשלח אנונימית", ephemeral=True)

# תוסיף כאן עוד פקודות (ban, kick, mute) באותו מבנה של check_owner
bot.run(TOKEN)
