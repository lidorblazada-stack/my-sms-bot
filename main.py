import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, re, asyncio
from firebase_admin import credentials, db

# --- הגדרות וחיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# IDs קבועים
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

# זיכרון זמני לאבטחה
user_msg_count = {}

# --- פונקציות ליבה ---
def get_user(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_user(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_user(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def send_mod_log(guild, title, desc, color=0xff0000, member=None):
    ch = guild.get_channel(LOG_CH_ID)
    if ch:
        e = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now())
        if member: e.set_footer(text=f"User ID: {member.id}")
        await ch.send(embed=e)

async def is_owner_check(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ פקודה לאונר בלבד!", ephemeral=True)
    return False

# --- Views (מערכות כפתורים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh_sup")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_vip")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    @ui.button(label="Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh_stf")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF, "Ticket Staff")
    @ui.button(label="יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh_bal")
    async def b4(self, i, b):
        bal, _ = get_user(i.user.id)
        await i.response.send_message(f"💰 היתרה שלך: `{bal}`", ephemeral=True)
    async def buy(self, i, p, rid, name):
        bal, _ = get_user(i.user.id); role = i.guild.get_role(rid)
        if bal < p: return await i.response.send_message("❌ חסר לך כסף!", ephemeral=True)
        if role in i.user.roles: return await i.response.send_message("✅ כבר יש לך את הרול!", ephemeral=True)
        update_user(i.user.id, b=bal-p); await i.user.add_roles(role)
        await i.response.send_message(f"✅ קנית {name}!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r)
        await i.response.send_message("אומתת!", ephemeral=True)

class AltAction(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="ak")
    async def k(self, i, b):
        if not await is_owner_check(i): return
        m = i.guild.get_member(self.mid)
        if m: 
            await m.kick(reason="אלט חשוד"); await i.message.delete()
            await send_mod_log(i.guild, "אבטחה: אלט הועף", f"האונר {i.user.mention} העיף את {m.mention}")
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="as")
    async def s(self, i, b):
        if not await is_owner_check(i): return
        m = i.guild.get_member(self.mid); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.message.delete()

# --- Bot Core ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    is_owner = any(r.id == OWNER_ROLE_ID for r in msg.author.roles)

    # Anti-Link
    if not is_owner and re.search(r'http[s]?://|discord\.gg/', msg.content):
        await msg.delete(); return

    # Anti-Spam
    uid = msg.author.id; now = datetime.now()
    user_msg_count[uid] = [t for t in user_msg_count.get(uid, []) if (now - t).seconds < 5]
    user_msg_count[uid].append(now)
    if len(user_msg_count[uid]) > 5 and not is_owner:
        await msg.author.timeout(timedelta(minutes=10), reason="Spam")
        await send_mod_log(msg.guild, "🛡️ אבטחה: מיוט אוטומטי", f"{msg.author.mention} הושתק עקב ספאם.")
        return

    # Money
    b, w = get_user(uid); update_user(uid, b=b+5)
    await bot.process_commands(msg)

@bot.event
async def on_message_delete(msg):
    if msg.mentions and not msg.author.bot:
        await send_mod_log(msg.guild, "⚠️ Ghost Ping!", f"מאת: {msg.author.mention}\nתוכן: {msg.content}")

@bot.event
async def on_member_join(m):
    if (datetime.utcnow() - m.created_at).days < 14:
        ch = m.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"🚨 **חשבון חשוד:** {m.mention}", view=AltAction(m.id))

# --- פקודות ניהול ואבטחה ---
@bot.tree.command(name="lockdown")
async def lock(i):
    if await is_owner_check(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒 הערוץ ננעל.", ephemeral=True)
        await send_mod_log(i.guild, "מצב חירום", f"הערוץ {i.channel.mention} ננעל.")

@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await is_owner_check(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="kick")
async def ki(i, m: discord.Member, r: str = "לא צוין"):
    if await is_owner_check(i):
        await m.kick(reason=r); await i.response.send_message("הועף", ephemeral=True)
        await send_mod_log(i.guild, "העפה ידנית", f"{m.name} הועף ע''י {i.user.name}", member=m)

@bot.tree.command(name="add_money")
async def am(i, m: discord.Member, amount: int):
    if await is_owner_check(i):
        b, w = get_user(m.id); update_user(m.id, b=b+amount)
        await i.response.send_message(f"💰 הוספו {amount} ל-{m.name}", ephemeral=True)

@bot.tree.command(name="warn")
async def wr(i, m: discord.Member, r: str):
    if await is_owner_check(i):
        b, w = get_user(m.id); update_user(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.name} הוזהר", ephemeral=True)
        await send_mod_log(i.guild, "אזהרה", f"{m.mention} קיבל אזהרה: {r}", member=m)

@bot.tree.command(name="setup_shop")
async def ss(i):
    if await is_owner_check(i):
        await i.channel.send("══ 💠 **CYBER STORE** 💠 ══", view=ShopView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_verify")
async def sv(i):
    if await is_owner_check(i):
        await i.channel.send("🛡️ **אימות כניסה**", view=VerifyView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="anonymous_feedback")
async def fb(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"🔒 **פידבק אנונימי:** {text}")
    await i.response.send_message("נשלח!", ephemeral=True)

bot.run(TOKEN)
