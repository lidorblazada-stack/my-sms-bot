import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin
from firebase_admin import credentials, db

# --- חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- הגדרת ערוצים ---
CH_RECOMMENDATIONS = 1501947249658429470 
CH_REPORTS = 1501946934779449505         
CH_FEEDBACK = 1503475379942461522        
CH_OWNER_LOGS = 1503496964732354620      
CH_ALT_LOGS = 1502014872655888554        # הערוץ שנתת לי אחי
CH_WELCOME_BYE = 1501713652217282591     

# --- רולים ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
SUSPECT_ROLE_ID = 1503464176599695380    
MEMBER_ROLE_ID = 1501983948111352091

ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

MY_USER_ID = 1130542850883469443
last_feedback_time = {}
user_messages = {}

# --- פונקציות עזר ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles) or i.user.id == MY_USER_ID: return True
    await i.response.send_message("❌ פקודה זו סגורה לאונר השרת בלבד!", ephemeral=True)
    return False

# --- מערכת אלטים (Alt Detector) המעודכנת ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def k(self, i: discord.Interaction, b: ui.Button):
        if not await is_owner(i): return
        m = i.guild.get_member(self.member_id)
        if m: 
            await m.kick(reason="אלט חשוד")
            await i.message.edit(content=f"✅ המשתמש {m.name} הועף מהשרת.", view=None)
        else:
            await i.response.send_message("❌ המשתמש כבר לא בשרת.", ephemeral=True)

    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_suspect")
    async def s(self, i: discord.Interaction, b: ui.Button):
        if not await is_owner(i): return
        m = i.guild.get_member(self.member_id)
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: 
            await m.add_roles(r)
            await i.message.edit(content=f"⚠️ רול חשוד ניתן ל-{m.name}.", view=None)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success, custom_id="alt_keep")
    async def st(self, i: discord.Interaction, b: ui.Button):
        if not await is_owner(i): return
        await i.message.edit(content=f"✅ המשתמש אושר על ידי האונר.", view=None)

# --- שאר ה-Views ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r); await i.response.send_message("אומתת!", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supporter", row=0)
    async def buy_supp(self, i, b): await self.handle_purchase(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i, b): await self.handle_purchase(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i, b): await self.handle_purchase(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop:bal", row=1)
    async def check_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: `{bal}`", ephemeral=True)
    async def handle_purchase(self, i, price, rid):
        bal, _ = get_data(i.user.id)
        if bal < price: return await i.response.send_message("❌ אין כסף", ephemeral=True)
        r = i.guild.get_role(rid)
        update_data(i.user.id, b=bal-price); await i.user.add_roles(r)
        await i.response.send_message(f"✅ תתחדש על {r.name}!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 📩", style=discord.ButtonStyle.primary, custom_id="f_btn")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

class FeedbackModal(ui.Modal, title='שליחת פידבק'):
    text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long)
    anon = ui.TextInput(label='אנונימי? (כן/לא)', default='כן', max_length=2)
    async def on_submit(self, i):
        ch = i.guild.get_channel(CH_FEEDBACK)
        emb = discord.Embed(title="📩 פידבק חדש", description=self.text.value, color=0x3498db)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

# --- בוט ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(FeedbackView()); self.add_view(VerifyView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    # Welcome Message
    ch = member.guild.get_channel(CH_WELCOME_BYE)
    if ch:
        emb = discord.Embed(title="🔥 ברוך הבא לשרת ספאמר 🔥", description=f"שלום {member.mention}, אתה מספר **{len(member.guild.members)}**.", color=0xff4500)
        await ch.send(content=f"{member.mention}", embed=emb)
    
    # Alt Detector FIX
    days_old = (datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
    if days_old < 14:
        alt_ch = member.guild.get_channel(CH_ALT_LOGS)
        if alt_ch:
            await alt_ch.send(f"🚨 **אלט חשוד זוהה:** {member.mention}\n**גיל חשבון:** {days_old} ימים.", view=AltActionView(member.id))

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+10)
    await bot.process_commands(msg)

# --- פקודות (20 פקודות בסיסיות) ---
@bot.tree.command(name="setup_shop", description="[Owner] הקמת חנות")
async def s_s(i):
    if await is_owner(i):
        emb = discord.Embed(title="💠 חנות השרת", color=0x2b2d31)
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="setup_verify", description="[Owner] הקמת אימות")
async def s_v(i):
    if await is_owner(i):
        await i.channel.send("🛡️ **אימות כניסה**", view=VerifyView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="setup_feedback", description="[Owner] הקמת פידבק")
async def s_f(i):
    if await is_owner(i):
        await i.channel.send("📩 **פידבק**", view=FeedbackView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה")
async def wa(i, m: discord.Member, r: str):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        if w+1 >= 3: await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"⚠️ {m.name} הוזהר.")

@bot.tree.command(name="clear", description="[Owner] מחיקת הודעות")
async def cl(i, a: int):
    if await is_owner(i): await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a}", ephemeral=True)

@bot.tree.command(name="kick", description="[Owner] הוצאת משתמש")
async def ki(i, m: discord.Member):
    if await is_owner(i): await m.kick(); await i.response.send_message(f"ועף {m.name}")

@bot.tree.command(name="ban", description="[Owner] הרחקת משתמש")
async def ba(i, m: discord.Member):
    if await is_owner(i): await m.ban(); await i.response.send_message(f"הורחק {m.name}")

@bot.tree.command(name="mute", description="[Owner] השתקה")
async def mu(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"הושתק {m.name}")

@bot.tree.command(name="unmute", description="[Owner] ביטול השתקה")
async def umu(i, m: discord.Member):
    if await is_owner(i): await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"בוטל מיוט ל-{m.name}")

@bot.tree.command(name="add_money", description="[Owner] הוספת כסף")
async def am(i, m: discord.Member, a: int):
    if await is_owner(i): b, w = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"נוספו {a}")

@bot.tree.command(name="stats", description="בדיקת מצב")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"💰: {b} | ⚠️: {w}")

@bot.tree.command(name="report", description="דיווח")
async def re(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(CH_REPORTS)
    if ch: await ch.send(f"🚨 דיווח על {m.mention} מ-{i.user.mention}: {r}")
    await i.response.send_message("נשלח")

@bot.tree.command(name="recommend", description="המלצה")
async def reco(i, t: str):
    ch = i.guild.get_channel(CH_RECOMMENDATIONS)
    if ch: await ch.send(f"🌟 המלצה מ-{i.user.mention}: {t}")
    await i.response.send_message("פורסם")

@bot.tree.command(name="avatar", description="אווטאר")
async def av(i, m: discord.Member = None):
    t = m or i.user; await i.response.send_message(t.display_avatar.url)

@bot.tree.command(name="lockdown", description="[Owner] נעילה")
async def lo(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("ננעל")

@bot.tree.command(name="unlock", description="[Owner] פתיחה")
async def unl(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("נפתח")

@bot.tree.command(name="slowmode", description="[Owner] סלואומוד")
async def sl(i, s: int):
    if await is_owner(i): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"עודכן ל-{s}")

@bot.tree.command(name="server_info", description="מידע שרת")
async def si(i): await i.response.send_message(f"חברים: {i.guild.member_count}")

@bot.tree.command(name="ping", description="פינג")
async def pi(i): await i.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="whois", description="מי זה")
async def wh(i, m: discord.Member): await i.response.send_message(f"שם: {m.name}\nID: {m.id}")

bot.run(TOKEN)
