import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# --- חיבור ל-Firebase (שימוש ב-Variables מ-Railway) ---
fb_config = os.getenv('FIREBASE_CONFIG')
if fb_config:
    cred = credentials.Certificate(json.loads(fb_config))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://vouge-guard-default-rtdb.firebaseio.com/' 
    })
else:
    print("❌ שגיאה: חסר FIREBASE_CONFIG ב-Railway Variables!")

# --- הגדרות ו-IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380
SUSPECT_ROLE_ID = 1503464176599695380
REPORT_CH_ID = 1501946934779449505
FEEDBACK_CH_ID = 1503475379942461522
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# --- פונקציות ענן (Firebase) ---
def get_data(uid):
    data = db.reference(f'users/{uid}').get()
    return (data.get('bal', 0), data.get('warns', 0)) if data else (0, 0)

def set_data(uid, bal=None, warns=None):
    ref = db.reference(f'users/{uid}')
    c_bal, c_warns = get_data(uid)
    ref.set({
        'bal': bal if bal is not None else c_bal,
        'warns': warns if warns is not None else c_warns,
        'last_update': str(datetime.now())
    })

# --- הגנה על פקודות אונר ---
attack_counts = {}
async def check_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    
    await i.response.send_message(f"❌ {i.user.mention}, אזהרה מילולית! אין גישה לפקודה.", ephemeral=True)
    attack_counts[i.user.id] = attack_counts.get(i.user.id, 0) + 1
    count = attack_counts[i.user.id]
    
    log = i.guild.get_channel(LOG_CH_ID)
    if log: await log.send(f"⚠️ **ניסיון פריצה:** {i.user.mention} ניסה `/{i.command.name}`. אזהרה: {count}/5")
    
    if count == 3: await i.user.timeout(timedelta(days=2), reason="ניסיון פריצה")
    elif count >= 5: 
        await i.user.kick(reason="ניסיונות פריצה חוזרים")
        attack_counts[i.user.id] = 0
    return False

# --- Views (חנות, אימות, אלטים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh:sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh:vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh:stf", row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh:bal", row=1)
    async def b4(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 היתרה שלך: `{bal}` מטבעות.", ephemeral=True)
    async def buy(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message(f"❌ חסר לך `{p-bal}` מטבעות!", ephemeral=True)
        set_data(i.user.id, bal=bal-p)
        await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message("✅ תתחדש! הרול נוסף.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v:btn")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

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

# --- Bot Core ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

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

# --- פקודות (15 פקודות) ---

@bot.tree.command(name="setup_shop", description="הקמת חנות")
async def ss(i):
    if await check_owner(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.description = "👋 **ברוכים הבאים לחנות!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        emb.add_field(name="🎗️ | Supporter", value="2,000 Coins", inline=False)
        emb.add_field(name="💎 | VIP Member", value="5,000 Coins", inline=False)
        emb.add_field(name="🛠️ | TICKET-STAFF", value="15,000 Coins", inline=False)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_verify", description="הקמת אימות")
async def sv(i):
    if await check_owner(i):
        await i.channel.send("🛡️ לחץ לאימות", view=VerifyView()); await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="add_money", description="הוספת כסף")
async def am(i, m: discord.Member, a: int):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, bal=b+a); await i.response.send_message(f"💵 נוספו {a} ל-{m.mention}")

@bot.tree.command(name="remove_money", description="הורדת כסף")
async def rm(i, m: discord.Member, a: int):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, bal=b-a); await i.response.send_message(f"📉 הורדו {a} מ-{m.mention}")

@bot.tree.command(name="clear", description="ניקוי הודעות")
async def cl(i, amount: int):
    if await check_owner(i): await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="kick", description="העפה")
async def ki(i, m: discord.Member, r: str = "N/A"):
    if await check_owner(i): await m.kick(reason=r); await i.response.send_message(f"{m.name} הועף")

@bot.tree.command(name="ban", description="הרחקה")
async def ba(i, m: discord.Member, r: str = "N/A"):
    if await check_owner(i): await m.ban(reason=r); await i.response.send_message(f"{m.name} הורחק")

@bot.tree.command(name="mute", description="השתקה")
async def mu(i, m: discord.Member, min: int):
    if await check_owner(i): await m.timeout(timedelta(minutes=min)); await i.response.send_message(f"{m.name} הושתק")

@bot.tree.command(name="warn", description="אזהרה")
async def wr(i, m: discord.Member, r: str):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, warns=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר ({w+1})")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות")
async def cw(i, m: discord.Member):
    if await check_owner(i): set_data(m.id, warns=0); await i.response.send_message("אופס")

@bot.tree.command(name="report", description="דיווח")
async def rep(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(REPORT_CH_ID)
    if ch: await ch.send(f"🚨 דיווח מ{i.user.name} על {m.name}: {r}")
    await i.response.send_message("דווח", ephemeral=True)

@bot.tree.command(name="recommend", description="המלצה")
async def rec(i, t: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"⭐ המלצה מ{i.user.name}: {t}")
    await i.response.send_message("תודה!", ephemeral=True)

@bot.tree.command(name="ping", description="בדיקת דיליי")
async def pi(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="stats", description="סטטיסטיקה")
async def st(i):
    b, w = get_data(i.user.id); await i.response.send_message(f"📊 כסף: {b} | אזהרות: {w}", ephemeral=True)

@bot.tree.command(name="anonymous_feedback", description="פידבק אנונימי")
async def af(i, t: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"🔒 אנונימי: {t}")
    await i.response.send_message("נשלח", ephemeral=True)

bot.run(TOKEN)
