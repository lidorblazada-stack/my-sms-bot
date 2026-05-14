import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, re
from firebase_admin import credentials, db

# --- הגדרות וחיבורים (Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- IDs של השרת שלך ---
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

# הגנת ספאם
user_msg_count = {}

# --- פונקציות עזר ---
def get_user(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_user(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_user(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def send_log(guild, title, desc, color=0xff0000, target=None):
    ch = guild.get_channel(LOG_CH_ID)
    if ch:
        emb = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now())
        if target: emb.set_footer(text=f"ID: {target.id}")
        await ch.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ שגיאה: הפקודה מוגבלת לבעלי רול Owner בלבד!", ephemeral=True)
    return False

# --- Views (מערכות כפתורים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop_sup")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop_vip")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    @ui.button(label="Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop_staff")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF, "Staff")
    @ui.button(label="יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop_bal")
    async def b4(self, i, b):
        bal, _ = get_user(i.user.id)
        await i.response.send_message(f"💰 היתרה שלך היא: `{bal}` מטבעות.", ephemeral=True)
    async def buy(self, i, p, rid, name):
        bal, _ = get_user(i.user.id)
        if bal < p: return await i.response.send_message("❌ חסר לך כסף לרכישה!", ephemeral=True)
        update_user(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message(f"✅ תתחדש! רכשת את הרול {name} בהצלחה.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="לחץ כאן לאימות ✅", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("✅ אומתת! ברוך הבא לשרת.", ephemeral=True)

class AltAction(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="בעיטה 👞", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def k(self, i, b):
        if not await check_owner(i): return
        m = i.guild.get_member(self.mid)
        if m: 
            await m.kick(reason="אלט חשוד"); await i.message.delete()
            await send_log(i.guild, "אבטחה: אלט הועף", f"האונר {i.user.mention} העיף את {m.mention}")

# --- Core ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    is_owner = any(r.id == OWNER_ROLE_ID for r in msg.author.roles)

    # Anti-Link & Anti-Spam
    if not is_owner:
        if re.search(r'http[s]?://|discord\.gg/', msg.content):
            await msg.delete(); return
        uid = msg.author.id; now = datetime.now()
        user_msg_count[uid] = [t for t in user_msg_count.get(uid, []) if (now - t).seconds < 5]
        user_msg_count[uid].append(now)
        if len(user_msg_count[uid]) > 5:
            await msg.author.timeout(timedelta(minutes=10), reason="ספאם אוטומטי")
            return

    # מערכת כסף על הודעות
    b, w = get_user(msg.author.id); update_user(msg.author.id, b=b+5)
    await bot.process_commands(msg)

@bot.event
async def on_member_join(m):
    if (datetime.utcnow() - m.created_at).days < 14:
        ch = m.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"🚨 **זיהוי אלט (נוצר לאחרונה):** {m.mention}", view=AltAction(m.id))

# --- כל הפקודות המוגדרות ---

@bot.tree.command(name="setup_shop", description="[Owner] הקמת חנות הרולים בשרת")
async def p1(i):
    if await check_owner(i):
        await i.channel.send("══ 💠 **CYBER STORE** 💠 ══\nקנה רולים באמצעות הכסף שצברת!", view=ShopView())
        await i.response.send_message("החנות הוקמה בהצלחה.", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[Owner] הקמת מערכת אימות כניסה לשרת")
async def p2(i):
    if await check_owner(i):
        await i.channel.send("🛡️ **אימות משתמשים**\nלחץ על הכפתור כדי לקבל גישה לשאר הערוצים.", view=VerifyView())
        await i.response.send_message("מערכת האימות הוקמה.", ephemeral=True)

@bot.tree.command(name="kick", description="[Owner] העפת משתמש מהשרת")
async def p3(i, member: discord.Member, reason: str = "לא צוינה סיבה"):
    if await check_owner(i):
        await member.kick(reason=reason); await i.response.send_message(f"👞 {member.name} הועף.", ephemeral=True)
        await send_log(i.guild, "פעולת ניהול: Kick", f"המשתמש {member.mention} הועף על ידי {i.user.mention}\nסיבה: {reason}", target=member)

@bot.tree.command(name="ban", description="[Owner] הרחקת משתמש לצמיתות מהשרת")
async def p4(i, member: discord.Member, reason: str = "לא צוינה סיבה"):
    if await check_owner(i):
        await member.ban(reason=reason); await i.response.send_message(f"🚫 {member.name} הורחק.", ephemeral=True)
        await send_log(i.guild, "פעולת ניהול: Ban", f"המשתמש {member.mention} הורחק על ידי {i.user.mention}\nסיבה: {reason}", target=member)

@bot.tree.command(name="mute", description="[Owner] השתקת משתמש לזמן מוגדר (בדקות)")
async def p5(i, member: discord.Member, minutes: int):
    if await check_owner(i):
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.name} הושתק ל-{minutes} דקות.", ephemeral=True)
        await send_log(i.guild, "פעולת ניהול: Mute", f"{member.mention} הושתק ל-{minutes} דקות ע''י {i.user.mention}", target=member)

@bot.tree.command(name="unmute", description="[Owner] ביטול השתקה למשתמש")
async def p6(i, member: discord.Member):
    if await check_owner(i):
        await member.timeout(None); await i.response.send_message(f"🔊 השתקה בוטלה עבור {member.name}.", ephemeral=True)

@bot.tree.command(name="clear", description="[Owner] מחיקת כמות הודעות מהערוץ")
async def p7(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)
        await send_log(i.guild, "ניקוי ערוץ", f"נמחקו {amount} הודעות בערוץ {i.channel.mention} ע''י {i.user.mention}", color=0x00ff00)

@bot.tree.command(name="add_money", description="[Owner] הוספת כסף למשתמש")
async def p8(i, member: discord.Member, amount: int):
    if await check_owner(i):
        b, w = get_user(member.id); update_user(member.id, b=b+amount)
        await i.response.send_message(f"💰 נוספו {amount} מטבעות ל-{member.mention}.", ephemeral=True)

@bot.tree.command(name="remove_money", description="[Owner] הורדת כסף למשתמש")
async def p9(i, member: discord.Member, amount: int):
    if await check_owner(i):
        b, w = get_user(member.id); update_user(member.id, b=max(0, b-amount))
        await i.response.send_message(f"💸 הופחתו {amount} מטבעות מ-{member.mention}.", ephemeral=True)

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה למשתמש")
async def p10(i, member: discord.Member, reason: str):
    if await check_owner(i):
        b, w = get_user(member.id); update_user(member.id, w=w+1)
        await i.response.send_message(f"⚠️ {member.mention} הוזהר. אזהרות כעת: {w+1}", ephemeral=True)
        await send_log(i.guild, "אזהרה", f"המשתמש {member.mention} הוזהר ע''י {i.user.mention}\nסיבה: {reason}", target=member)

@bot.tree.command(name="clear_warns", description="[Owner] איפוס אזהרות למשתמש")
async def p11(i, member: discord.Member):
    if await check_owner(i):
        update_user(member.id, w=0); await i.response.send_message(f"✅ האזהרות של {member.name} נוקו.", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת מצב הכסף והאזהרות שלך או של משתמש אחר")
async def p12(i, member: discord.Member = None):
    t = member or i.user; b, w = get_user(t.id)
    await i.response.send_message(f"📊 **סטטיסטיקות עבור {t.name}:**\n💰 כסף: `{b}`\n⚠️ אזהרות: `{w}`", ephemeral=True)

@bot.tree.command(name="anonymous_feedback", description="שליחת משוב אנונימי לאונר")
async def p13(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"🔒 **משוב אנונימי חדש:**\n{text}")
    await i.response.send_message("✅ המשוב שלך נשלח באנונימיות.", ephemeral=True)

@bot.tree.command(name="lockdown", description="[Owner] נעילת הערוץ לכתיבה לכולם")
async def p14(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒 הערוץ ננעל הרמטית.", ephemeral=True)

@bot.tree.command(name="unlock", description="[Owner] שחרור נעילת ערוץ")
async def p15(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True)
        await i.response.send_message("🔓 הערוץ שוחרר לכתיבה.", ephemeral=True)

bot.run(TOKEN)
