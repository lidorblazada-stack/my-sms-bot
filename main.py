import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# --- משיכת נתונים מ-Railway ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG_STR = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG_STR and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG_STR))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
else:
    print("❌ חסרים משתני סביבה!")

# --- IDs קבועים ---
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380
SUSPECT_ROLE_ID = 1503464176599695380
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# --- מערכת Anti-Spam ---
user_messages = {} # {user_id: [timestamps]}

# --- פונקציות עזר ---
def get_data(uid):
    data = db.reference(f'users/{uid}').get()
    return (data.get('bal', 0), data.get('warns', 0)) if data else (0, 0)

def set_data(uid, bal=None, warns=None):
    ref = db.reference(f'users/{uid}')
    c_bal, c_warns = get_data(uid)
    ref.set({'bal': bal if bal is not None else c_bal, 'warns': warns if warns is not None else c_warns})

async def send_mod_log(i, action, target, reason):
    log_ch = i.guild.get_channel(LOG_CH_ID) if hasattr(i, 'guild') else i.get_channel(LOG_CH_ID)
    if log_ch:
        emb = discord.Embed(title="🛡️ דיווח פעולת אכיפה", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="המבצע:", value=i.user.mention if hasattr(i, 'user') else "מערכת אוטומטית", inline=True)
        emb.add_field(name="היעד:", value=target.mention if hasattr(target, 'mention') else str(target), inline=True)
        emb.add_field(name="פעולה:", value=action, inline=True)
        emb.add_field(name="סיבה:", value=reason, inline=False)
        await log_ch.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ אין גישה!", ephemeral=True)
    return False

# --- Views ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh_sup")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_vip")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh_bal")
    async def b4(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: `{bal}`", ephemeral=True)
    async def buy(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ חסר כסף!", ephemeral=True)
        set_data(i.user.id, bal=bal-p)
        await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message("✅ נרכש!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("אומתת!", ephemeral=True)

class AltView(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_k")
    async def k(self, i, b):
        if not await check_owner(i): return
        m = i.guild.get_member(self.mid)
        if m: 
            await m.kick(reason="אלט חשוד")
            await send_mod_log(i, "העפה (Kick)", m, "זיהוי אלט")
            await i.message.delete()
    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_h")
    async def h(self, i, b):
        if not await check_owner(i): return
        m = i.guild.get_member(self.mid); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: 
            await m.add_roles(r); await send_mod_log(i, "רול חשוד", m, "ניתן ידנית")
            await i.message.delete()

# --- Bot Core ---
class Guard(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

bot = Guard()

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return

    # Anti-Spam Logic
    uid = msg.author.id
    now = datetime.now()
    if uid not in user_messages: user_messages[uid] = []
    user_messages[uid].append(now)
    # שמירת הודעות מה-10 שניות האחרונות בלבד
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).seconds < 10]

    if len(user_messages[uid]) > 5:
        try:
            await msg.author.timeout(timedelta(minutes=10), reason="ספאם אוטומטי")
            await msg.channel.send(f"🚫 {msg.author.mention} הושתק ל-10 דקות עקב ספאם.", delete_after=5)
            log_ch = msg.guild.get_channel(LOG_CH_ID)
            if log_ch: await log_ch.send(f"🚨 **ספאם זוהה:** {msg.author.mention} הושתק אוטומטית.")
        except: pass

    # כסף על הודעה
    b, w = get_data(uid); set_data(uid, bal=b+5)
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ זיהוי אלט: {member.mention}", view=AltView(member.id))

# --- פקודות ---
@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)
        await send_mod_log(i, "ניקוי", f"{amount} הודעות", f"בערוץ {i.channel.name}")

@bot.tree.command(name="kick")
async def ki(i, m: discord.Member, r: str = "לא צוין"):
    if await check_owner(i):
        await m.kick(reason=r); await i.response.send_message(f"👞 {m.name} הועף", ephemeral=True)
        await send_mod_log(i, "העפה", m, r)

@bot.tree.command(name="setup_shop")
async def ss(i):
    if await check_owner(i):
        emb = discord.Embed(title="══ 💠 CYBER STORE 💠 ══", color=0x2b2d31)
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("בוצע", ephemeral=True)

bot.run(TOKEN)
