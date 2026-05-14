import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# --- חיבור ל-Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG_STR = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG_STR and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG_STR))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
else:
    print("❌ חסרים משתני סביבה ב-Railway!")

# --- IDs קבועים ---
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380
SUSPECT_ROLE_ID = 1503464176599695380
MEMBER_ROLE_ID = 1501983948111352091
FEEDBACK_CH_ID = 1503475379942461522

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# --- משתנים למערכות ---
user_messages = {} # Anti-Spam

# --- פונקציות עזר ---
def get_data(uid):
    data = db.reference(f'users/{uid}').get()
    return (data.get('bal', 0), data.get('warns', 0)) if data else (0, 0)

def set_data(uid, bal=None, warns=None):
    ref = db.reference(f'users/{uid}')
    c_bal, c_warns = get_data(uid)
    ref.set({'bal': bal if bal is not None else c_bal, 'warns': warns if warns is not None else c_warns})

async def send_mod_log(i, action, target, reason):
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        emb = discord.Embed(title="🛡️ דיווח פעולת אכיפה", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="המבצע:", value=i.user.mention, inline=True)
        emb.add_field(name="היעד:", value=target.mention if hasattr(target, 'mention') else str(target), inline=True)
        emb.add_field(name="פעולה:", value=action, inline=True)
        emb.add_field(name="סיבה:", value=reason, inline=False)
        await log_ch.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ אין לך גישה לפקודה זו!", ephemeral=True)
    return False

# --- Views (חנות, אימות, אלטים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh_sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    @ui.button(label="קנה Ticket Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh_stf", row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF, "Staff")
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh_bal", row=1)
    async def b4(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 היתרה שלך: `{bal}` מטבעות.", ephemeral=True)
    async def buy(self, i, p, rid, rname):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ אין לך מספיק כסף!", ephemeral=True)
        set_data(i.user.id, bal=bal-p)
        await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message(f"✅ תתחדש! קיבלת רול {rname}.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("אומתת בהצלחה בשרת!", ephemeral=True)

class AltView(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_k")
    async def k(self, i, b):
        if not await check_owner(i): return
        m = i.guild.get_member(self.mid)
        if m: 
            await m.kick(reason="חשבון אלט"); await i.message.delete()
            await send_mod_log(i, "העפה (Kick)", m, "זיהוי אלט אוטומטי")
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success, custom_id="alt_s")
    async def s(self, i, b):
        if not await check_owner(i): return
        await i.message.delete()
        await send_mod_log(i, "אישור אלט", i.guild.get_member(self.mid), "אונר אישר ידנית")
    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_h")
    async def h(self, i, b):
        if not await check_owner(i): return
        m = i.guild.get_member(self.mid); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: 
            await m.add_roles(r); await i.message.delete()
            await send_mod_log(i, "רול חשוד", m, "ניתן רול חשוד")

# --- Bot Core ---
class Guard(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

bot = Guard()

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    # Anti-Spam
    uid = msg.author.id
    now = datetime.now()
    if uid not in user_messages: user_messages[uid] = []
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).seconds < 10]
    if len(user_messages[uid]) > 5:
        await msg.author.timeout(timedelta(minutes=10), reason="ספאם")
        await msg.channel.send(f"🚫 {msg.author.mention} הושתק ל-10 דקות עקב ספאם.", delete_after=5)
    # Money
    b, w = get_data(uid); set_data(uid, bal=b+5)
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ **חשבון חשוד (פחות מ-7 ימים):** {member.mention}", view=AltView(member.id))

# --- פקודות (15 פקודות) ---

@bot.tree.command(name="setup_shop")
async def c1(i):
    if await check_owner(i):
        await i.channel.send("══ 💠 **CYBER STORE** 💠 ══", view=ShopView())
        await i.response.send_message("החנות הוקמה.", ephemeral=True)

@bot.tree.command(name="setup_verify")
async def c2(i):
    if await check_owner(i):
        await i.channel.send("🛡️ **לחץ על הכפתור למטה כדי לקבל גישה לשרת**", view=VerifyView())
        await i.response.send_message("מערכת אימות הוקמה.", ephemeral=True)

@bot.tree.command(name="kick")
async def c3(i, m: discord.Member, r: str = "לא צוין"):
    if await check_owner(i):
        await m.kick(reason=r); await i.response.send_message(f"👞 {m.name} הועף.", ephemeral=True)
        await send_mod_log(i, "העפה (Kick)", m, r)

@bot.tree.command(name="ban")
async def c4(i, m: discord.Member, r: str = "לא צוין"):
    if await check_owner(i):
        await m.ban(reason=r); await i.response.send_message(f"🚫 {m.name} הורחק.", ephemeral=True)
        await send_mod_log(i, "הרחקה (Ban)", m, r)

@bot.tree.command(name="mute")
async def c5(i, m: discord.Member, min: int, r: str = "לא צוין"):
    if await check_owner(i):
        await m.timeout(timedelta(minutes=min), reason=r)
        await i.response.send_message(f"🔇 {m.name} הושתק ל-{min} דקות.", ephemeral=True)
        await send_mod_log(i, "השתקה (Mute)", m, f"{min} דק' | {r}")

@bot.tree.command(name="unmute")
async def c6(i, m: discord.Member):
    if await check_owner(i):
        await m.timeout(None); await i.response.send_message(f"🔊 המיוט של {m.name} הוסר.", ephemeral=True)
        await send_mod_log(i, "הסרת השתקה", m, "בוצע ידנית")

@bot.tree.command(name="clear")
async def c7(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)
        await send_mod_log(i, "ניקוי צ'אט", f"{amount} הודעות", f"ערוץ {i.channel.name}")

@bot.tree.command(name="add_money")
async def c8(i, m: discord.Member, amount: int):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, bal=b+amount)
        await i.response.send_message(f"💰 הוספת {amount} מטבעות ל-{m.mention}.", ephemeral=True)
        await send_mod_log(i, "הוספת כסף", m, f"סכום: {amount}")

@bot.tree.command(name="remove_money")
async def c9(i, m: discord.Member, amount: int):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, bal=max(0, b-amount))
        await i.response.send_message(f"💸 הורדת {amount} מטבעות ל-{m.mention}.", ephemeral=True)
        await send_mod_log(i, "הורדת כסף", m, f"סכום: {amount}")

@bot.tree.command(name="warn")
async def c10(i, m: discord.Member, r: str):
    if await check_owner(i):
        b, w = get_data(m.id); set_data(m.id, warns=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר. (אזהרה {w+1})", ephemeral=True)
        await send_mod_log(i, "אזהרה", m, r)

@bot.tree.command(name="clear_warns")
async def c11(i, m: discord.Member):
    if await check_owner(i):
        set_data(m.id, warns=0); await i.response.send_message(f"✅ האזהרות של {m.mention} נוקו.", ephemeral=True)
        await send_mod_log(i, "איפוס אזהרות", m, "בוצע ידנית")

@bot.tree.command(name="stats")
async def c12(i, m: discord.Member = None):
    target = m or i.user
    b, w = get_data(target.id)
    await i.response.send_message(f"📊 **סטטיסטיקות עבור {target.name}:**\n💰 כסף: {b}\n⚠️ אזהרות: {w}", ephemeral=True)

@bot.tree.command(name="anonymous_feedback")
async def c13(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"🔒 **משוב אנונימי:** {text}")
    await i.response.send_message("המשוב נשלח באנונימיות.", ephemeral=True)

@bot.tree.command(name="ping")
async def c14(i):
    await i.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms", ephemeral=True)

@bot.tree.command(name="owner_help")
async def c15(i):
    if await check_owner(i):
        msg = "👑 **פקודות אונר:**\n/setup_shop, /setup_verify, /kick, /ban, /mute, /unmute, /clear, /add_money, /remove_money, /warn, /clear_warns"
        await i.response.send_message(msg, ephemeral=True)

bot.run(TOKEN)
