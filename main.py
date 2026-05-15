import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, re
from firebase_admin import credentials, db

# --- חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- הגדרת ערוצים (IDs מהמגילה שלך) ---
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

# רולים לחנות
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

async def log_action(guild, user, cmd, details=""):
    ch = guild.get_channel(CH_OWNER_LOGS)
    if ch:
        emb = discord.Embed(title="🔧 לוג פקודות אונר", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="אונר:", value=user.mention)
        emb.add_field(name="פקודה:", value=cmd)
        if details: emb.add_field(name="פרטים:", value=details, inline=False)
        await ch.send(embed=emb)

# --- מערכת אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r); await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- מערכת פידבק (Feedback) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק'):
    text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long)
    anon = ui.TextInput(label='אנונימי? (כן/לא)', default='כן', max_length=2)
    async def on_submit(self, i):
        now = datetime.now()
        if i.user.id in last_feedback_time and (now - last_feedback_time[i.user.id]).seconds < 300:
            return await i.response.send_message("❌ חכה 5 דקות בין פידבקים!", ephemeral=True)
        last_feedback_time[i.user.id] = now
        ch = i.guild.get_channel(CH_FEEDBACK)
        is_anon = self.anon.value.strip() == "כן"
        emb = discord.Embed(title="📩 פידבק חדש", description=self.text.value, color=0x3498db)
        emb.set_author(name="🕵️ אנונימי" if is_anon else f"👤 {i.user.name}")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 📩", style=discord.ButtonStyle.primary, custom_id="f_btn")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- חנות (Shop) - מבנה זוגות ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supporter", row=0)
    async def buy_supp(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 2000, ROLE_SUPPORTER)

    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 5000, ROLE_VIP)

    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 15000, ROLE_TICKET_STAFF)

    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop:bal", row=1)
    async def check_bal(self, i: discord.Interaction, b: ui.Button):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: `{bal}` מטבעות.", ephemeral=True)

    async def handle_purchase(self, i, price, role_id):
        bal, _ = get_data(i.user.id)
        if bal < price: return await i.response.send_message(f"❌ חסר לך `{price - bal}` מטבעות!", ephemeral=True)
        role = i.guild.get_role(role_id)
        if role in i.user.roles: return await i.response.send_message("❌ כבר יש לך את הרול!", ephemeral=True)
        update_data(i.user.id, b=bal - price); await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש! קיבלת **{role.name}**!", ephemeral=True)

# --- מערכת אלטים (Alt Detector) ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        m = i.guild.get_member(self.member_id)
        if m: await m.kick(); await i.message.edit(content="✅ הועף", view=None)
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def s(self, i, b):
        m = i.guild.get_member(self.member_id)
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.message.edit(content="⚠️ רול חשוד ניתן", view=None)
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def st(self, i, b): await i.message.edit(content="✅ אושר", view=None)

# --- הבוט המאוחד ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(FeedbackView()); self.add_view(VerifyView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(CH_WELCOME_BYE)
    if ch:
        emb = discord.Embed(title="🔥 ברוך הבא לשרת ספאמר 🔥", description=f"שלום {member.mention}, אתה מספר **{len(member.guild.members)}**.\nפתח טיקט לעזרה!", color=0xff4500)
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        await ch.send(content=f"{member.mention}", embed=emb)
    if (datetime.utcnow() - member.created_at).days < 14:
        alt_ch = member.guild.get_channel(CH_ALT_LOGS)
        if alt_ch: await alt_ch.send(f"🚨 **זיהוי אלט חשוד:** {member.mention}", view=AltActionView(member.id))

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    # Anti-Spam
    uid = msg.author.id; now = datetime.now()
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not any(r.id == OWNER_ROLE_ID for r in msg.author.roles):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+10)
    await bot.process_commands(msg)

# --- 20 פקודות (ניהול, קהילה, מערכות) ---

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה רשמית (מיוט ב-3)")
async def p1(i, m: discord.Member, r: str):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await log_action(i.guild, i.user, "Warn", f"למשתמש: {m.mention}, סיבה: {r}")
        if w+1 >= 3: await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"⚠️ אזהרה נרשמה ל-{m.name}.", ephemeral=True)

@bot.tree.command(name="unwarn", description="[Owner] הורדת אזהרה למשתמש")
async def p2(i, m: discord.Member):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=max(0, w-1))
        await log_action(i.guild, i.user, "Unwarn", f"למשתמש: {m.mention}")
        await i.response.send_message(f"✅ הורדה אזהרה ל-{m.name}.", ephemeral=True)

@bot.tree.command(name="clear", description="[Owner] מחיקת כמות הודעות בצ'אט")
async def p3(i, a: int):
    if await is_owner(i):
        await i.channel.purge(limit=a); await log_action(i.guild, i.user, "Clear", f"כמות: {a}")
        await i.response.send_message(f"🗑️ נמחקו {a} הודעות.", ephemeral=True)

@bot.tree.command(name="kick", description="[Owner] העפת משתמש מהשרת")
async def p4(i, m: discord.Member, r: str = "ללא"):
    if await is_owner(i):
        await m.kick(reason=r); await log_action(i.guild, i.user, "Kick", f"משתמש: {m.name}")
        await i.response.send_message(f"👞 {m.name} הועף.", ephemeral=True)

@bot.tree.command(name="ban", description="[Owner] הרחקת משתמש מהשרת לתמיד")
async def p5(i, m: discord.Member, r: str = "ללא"):
    if await is_owner(i):
        await m.ban(reason=r); await log_action(i.guild, i.user, "Ban", f"משתמש: {m.name}")
        await i.response.send_message(f"🔨 {m.name} הורחק.", ephemeral=True)

@bot.tree.command(name="mute", description="[Owner] השתקת משתמש ידנית")
async def p6(i, m: discord.Member):
    if await is_owner(i):
        await m.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await log_action(i.guild, i.user, "Mute", f"משתמש: {m.mention}")
        await i.response.send_message(f"🔇 {m.name} הושתק.", ephemeral=True)

@bot.tree.command(name="unmute", description="[Owner] ביטול השתקת משתמש")
async def p7(i, m: discord.Member):
    if await is_owner(i):
        await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID)); await log_action(i.guild, i.user, "Unmute", f"משתמש: {m.mention}")
        await i.response.send_message(f"🔊 {m.name} חזר לדבר.", ephemeral=True)

@bot.tree.command(name="lockdown", description="[Owner] נעילת הערוץ לכתיבה")
async def p8(i):
    if await is_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await log_action(i.guild, i.user, "Lockdown"); await i.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock", description="[Owner] פתיחת הערוץ לכתיבה")
async def p9(i):
    if await is_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True)
        await log_action(i.guild, i.user, "Unlock"); await i.response.send_message("🔓 הערוץ נפתח.")

@bot.tree.command(name="add_money", description="[Owner] הוספת כסף למשתמש")
async def p10(i, m: discord.Member, a: int):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, b=b+a); await log_action(i.guild, i.user, "Add Money", f"ל-{m.name}, כמות: {a}")
        await i.response.send_message(f"💵 נוספו `{a}` מטבעות.", ephemeral=True)

@bot.tree.command(name="remove_money", description="[Owner] הורדת כסף למשתמש")
async def p11(i, m: discord.Member, a: int):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, b=max(0, b-a)); await log_action(i.guild, i.user, "Remove Money", f"ל-{m.name}, כמות: {a}")
        await i.response.send_message(f"💸 הורדו `{a}` מטבעות.", ephemeral=True)

@bot.tree.command(name="setup_shop", description="[Owner] הקמת חנות השרת (מבנה זוגות)")
async def p12(i):
    if await is_owner(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.description = "👋 **ברוכים הבאים לחנות!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🎗️ | Supporter (2,000)\n💎 | VIP Member (5,000)\n🛠️ | TICKET-STAFF (15,000)"
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("החנות הוקמה.", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[Owner] הקמת מערכת אימות")
async def p13(i):
    if await is_owner(i):
        await i.channel.send("🛡️ **אימות כניסה**", view=VerifyView()); await i.response.send_message("מערכת אימות הוקמה.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="[Owner] הקמת מערכת פידבק")
async def p14(i):
    if await is_owner(i):
        await i.channel.send("📩 **שלחו לנו פידבק!**", view=FeedbackView()); await i.response.send_message("מערכת פידבק הוקמה.", ephemeral=True)

@bot.tree.command(name="report", description="דיווח על משתמש לצוות")
async def p15(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(CH_REPORTS)
    emb = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c); emb.add_field(name="מדווח:", value=i.user.mention); emb.add_field(name="על:", value=m.mention); emb.add_field(name="סיבה:", value=r)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="recommend", description="שליחת המלצה לשרת")
async def p16(i, t: str):
    ch = i.guild.get_channel(CH_RECOMMENDATIONS)
    emb = discord.Embed(title="🌟 המלצה", description=t, color=0xf1c40f); emb.set_author(name=i.user.name)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ פורסם!", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת כסף ואזהרות")
async def p17(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **{t.name}**: 💰 `{b}` | ⚠️ `{w}`", ephemeral=True)

@bot.tree.command(name="slowmode", description="[Owner] הגדרת Slowmode לערוץ")
async def p18(i, s: int):
    if await is_owner(i):
        await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"⏲️ הוגדר Slowmode של {s} שניות.")

@bot.tree.command(name="avatar", description="צפייה בתמונת פרופיל")
async def p19(i, m: discord.Member = None):
    t = m or i.user; await i.response.send_message(t.display_avatar.url)

@bot.tree.command(name="server_info", description="פרטי השרת")
async def p20(i):
    emb = discord.Embed(title=f"ℹ️ מידע על {i.guild.name}", color=0x3498db)
    emb.add_field(name="חברים:", value=str(i.guild.member_count))
    emb.add_field(name="נוצר ב-:", value=i.guild.created_at.strftime("%d/%m/%Y"))
    await i.response.send_message(embed=emb)

bot.run(TOKEN)
