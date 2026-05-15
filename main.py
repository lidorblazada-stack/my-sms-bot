import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random
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
CH_ALT_LOGS = 1502014872655888554        
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
    await i.response.send_message("❌ אחי זה רק לאונר!", ephemeral=True)
    return False

# --- Views ---

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק 💰", style=discord.ButtonStyle.danger, custom_id="heist_btn")
    async def heist_b(self, i, b):
        s_bal, _ = get_data(i.user.id)
        if random.randint(1, 100) <= 20:
            win = random.randint(1000, 3000)
            update_data(i.user.id, b=s_bal + win)
            await i.response.send_message(f"💰 פוצצת את הכספת ולקחת **{win}**!", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal - 500))
            await i.response.send_message(f"🚨 נתפסת! איבדת 500 מטבעות.", ephemeral=True)

    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.secondary, custom_id="bal_btn")
    async def check(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"היתרה שלך: `{bal}`", ephemeral=True)

class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def k(self, i, b):
        if not await is_owner(i): return
        m = i.guild.get_member(self.member_id)
        if m: await m.kick(); await i.message.edit(content=f"✅ הועף", view=None)
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_suspect")
    async def s(self, i, b):
        if not await is_owner(i): return
        m = i.guild.get_member(self.member_id); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.message.edit(content=f"⚠️ חשוד", view=None)
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success, custom_id="alt_keep")
    async def st(self, i, b):
        if not await is_owner(i): return
        await i.message.edit(content=f"✅ אושר", view=None)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supporter", row=0)
    async def buy_supp(self, i, b): await self.handle_purchase(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i, b): await self.handle_purchase(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i, b): await self.handle_purchase(i, 15000, ROLE_TICKET_STAFF)
    async def handle_purchase(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ אין כסף", ephemeral=True)
        r = i.guild.get_role(rid); update_data(i.user.id, b=bal-p); await i.user.add_roles(r)
        await i.response.send_message(f"✅ קיבלת {r.name}!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r); await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(CH_WELCOME_BYE)
    if ch: await ch.send(content=f"{member.mention}", embed=discord.Embed(title="🔥 ברוך הבא 🔥", color=0xff4500))
    if (datetime.utcnow() - member.created_at.replace(tzinfo=None)).days < 14:
        alt_ch = member.guild.get_channel(CH_ALT_LOGS)
        if alt_ch: await alt_ch.send(f"🚨 **אלט חשוד:** {member.mention}", view=AltActionView(member.id))

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = msg.author.id; now = datetime.now()
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not any(r.id == OWNER_ROLE_ID for r in msg.author.roles):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} ספאם.")
        return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+10)
    await bot.process_commands(msg)

# --- פקודות (החזרתי את הכל!) ---

@bot.tree.command(name="setup_heist", description="[Owner] פאנל שודים")
async def s_h(i):
    if await is_owner(i):
        emb = discord.Embed(title="🕵️ מחלקת פשיעה", description="לחץ על הכפתור כדי לנסות לשדוד את הבנק!", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView()); await i.response.send_message("פאנל הוקם.", ephemeral=True)

@bot.tree.command(name="rob", description="שוד משתמש")
async def rob(i, m: discord.Member):
    s_bal, _ = get_data(i.user.id); v_bal, _ = get_data(m.id)
    if v_bal < 200: return await i.response.send_message("עני מדי.", ephemeral=True)
    if random.randint(1, 100) <= 35:
        stolen = random.randint(100, int(v_bal * 0.25))
        update_data(i.user.id, b=s_bal+stolen); update_data(m.id, b=v_bal-stolen)
        await i.response.send_message(f"🥷 שדדת מ-{m.mention} סכום של {stolen}!")
    else:
        update_data(i.user.id, b=max(0, s_bal-300))
        await i.response.send_message("👮 נתפסת!")

@bot.tree.command(name="warn", description="[Owner] אזהרה")
async def p1(i, m: discord.Member, r: str):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        if w+1 >= 3: await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"⚠️ {m.name} הוזהר.")

@bot.tree.command(name="clear", description="[Owner] מחיקה")
async def p2(i, a: int):
    if await is_owner(i): await i.channel.purge(limit=a); await i.response.send_message("נמחק.", ephemeral=True)

@bot.tree.command(name="kick", description="[Owner] הוצאה")
async def p3(i, m: discord.Member):
    if await is_owner(i): await m.kick(); await i.response.send_message("הועף.")

@bot.tree.command(name="ban", description="[Owner] הרחקה")
async def p4(i, m: discord.Member):
    if await is_owner(i): await m.ban(); await i.response.send_message("הורחק.")

@bot.tree.command(name="mute", description="[Owner] השתקה")
async def p5(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message("הושתק.")

@bot.tree.command(name="unmute", description="[Owner] ביטול השתקה")
async def p6(i, m: discord.Member):
    if await is_owner(i): await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message("בוטל.")

@bot.tree.command(name="setup_shop", description="[Owner] חנות")
async def p7(i):
    if await is_owner(i): await i.channel.send("🛒 **חנות**", view=ShopView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="setup_verify", description="[Owner] אימות")
async def p8(i):
    if await is_owner(i): await i.channel.send("🛡️ **אימות**", view=VerifyView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="stats", description="מצב")
async def p9(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"💰: {b} | ⚠️: {w}")

@bot.tree.command(name="lockdown", description="[Owner] נעילה")
async def p10(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("ננעל.")

@bot.tree.command(name="unlock", description="[Owner] פתיחה")
async def p11(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("נפתח.")

@bot.tree.command(name="add_money", description="[Owner] הוספת כסף")
async def p12(i, m: discord.Member, a: int):
    if await is_owner(i): b, w = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"נוספו {a}.")

@bot.tree.command(name="avatar", description="תמונה")
async def p13(i, m: discord.Member = None):
    t = m or i.user; await i.response.send_message(t.display_avatar.url)

@bot.tree.command(name="server_info", description="מידע שרת")
async def p14(i): await i.response.send_message(f"חברים: {i.guild.member_count}")

@bot.tree.command(name="ping", description="בדיקה")
async def p15(i): await i.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="slowmode", description="[Owner] סלואומוד")
async def p16(i, s: int):
    if await is_owner(i): await i.channel.edit(slowmode_delay=s); await i.response.send_message("עודכן.")

@bot.tree.command(name="report", description="דיווח")
async def p17(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(CH_REPORTS)
    if ch: await ch.send(f"🚨 דיווח על {m.mention}: {r}"); await i.response.send_message("נשלח.")

@bot.tree.command(name="recommend", description="המלצה")
async def p18(i, t: str):
    ch = i.guild.get_channel(CH_RECOMMENDATIONS)
    if ch: await ch.send(f"🌟 המלצה: {t}"); await i.response.send_message("פורסם.")

@bot.tree.command(name="whois", description="מי זה")
async def p19(i, m: discord.Member): await i.response.send_message(f"שם: {m.name}\nID: {m.id}")

@bot.tree.command(name="setup_feedback", description="[Owner] פידבק")
async def p20(i):
    if await is_owner(i): await i.channel.send("📩 שלחו פידבק!"); await i.response.send_message("הוקם.")

bot.run(TOKEN)
