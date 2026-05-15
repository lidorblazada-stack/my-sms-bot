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

# --- הגדרת ערוצים (לפי המגילה שלך) ---
CH_RECOMMENDATIONS = 1501947249658429470 
CH_REPORTS = 1501946934779449505         
CH_FEEDBACK = 1503475379942461522        
CH_OWNER_LOGS = 1503496964732354620      
CH_ALT_LOGS = 1502014872655888554        
CH_WELCOME_BYE = 1501713652217282591     

OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
SUSPECT_ROLE_ID = 1503464176599695380    
MEMBER_ROLE_ID = 1501983948111352091

ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255

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
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ פקודה זו סגורה לאונר השרת בלבד!", ephemeral=True)
    return False

async def log_action(guild, user, cmd, details=""):
    ch = guild.get_channel(CH_OWNER_LOGS)
    if ch:
        emb = discord.Embed(title="🔧 לוג פקודות אונר", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="אונר:", value=user.mention)
        emb.add_field(name="פקודה:", value=cmd)
        if details: emb.add_field(name="מידע נוסף:", value=details, inline=False)
        await ch.send(embed=emb)

# --- Views & Modals ---

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def v(self, i: discord.Interaction, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: 
            await i.user.add_roles(r)
            await i.response.send_message("✅ אומתת בהצלחה! ברוך הבא לשרת.", ephemeral=True)
        else:
            await i.response.send_message("❌ רול האימות לא נמצא, פנה לאונר.", ephemeral=True)

class FeedbackModal(ui.Modal, title='שליחת פידבק'):
    text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long)
    anon = ui.TextInput(label='אנונימי? (כן/לא)', default='כן', max_length=2)
    async def on_submit(self, i):
        now = datetime.now()
        if i.user.id in last_feedback_time and (now - last_feedback_time[i.user.id]).seconds < 300:
            return await i.response.send_message("❌ חכה 5 דקות!", ephemeral=True)
        last_feedback_time[i.user.id] = now
        ch = i.guild.get_channel(CH_FEEDBACK)
        is_anon = self.anon.value.strip() == "כן"
        emb = discord.Embed(title="📩 פידבק חדש", description=self.text.value, color=0x3498db)
        emb.set_author(name="🕵️ אנונימי" if is_anon else f"👤 {i.user.name}")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

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

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️ (2000)", style=discord.ButtonStyle.secondary, custom_id="s1")
    async def s1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="VIP 💎 (5000)", style=discord.ButtonStyle.primary, custom_id="s2")
    async def s2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    async def buy(self, i, p, rid, n):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ אין כסף", ephemeral=True)
        update_data(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message(f"✅ קנית {n}!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 📩", style=discord.ButtonStyle.primary, custom_id="f1")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- בוט ---
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
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        await ch.send(content=f"{member.mention}", embed=emb)
    if (datetime.utcnow() - member.created_at).days < 14:
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
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+5)
    await bot.process_commands(msg)

# --- פקודות ---

@bot.tree.command(name="setup_verify", description="[Owner] הקמת מערכת אימות")
async def sv(i: discord.Interaction):
    if await is_owner(i):
        await i.channel.send("🛡️ **אימות כניסה לשרת**\nלחצו על הכפתור למטה כדי לקבל גישה לשאר החדרים.", view=VerifyView())
        await i.response.send_message("מערכת האימות הוקמה.", ephemeral=True)

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה רשמית")
async def w(i, m: discord.Member, r: str):
    if await is_owner(i):
        bal, w = get_data(m.id); update_data(m.id, w=w+1)
        await log_action(i.guild, i.user, "Warn", f"משתמש: {m.mention}\nסיבה: {r}")
        if w+1 >= 3: await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"⚠️ {m.name} הוזהר.", ephemeral=True)

@bot.tree.command(name="clear", description="[Owner] ניקוי הודעות")
async def cl(i, a: int):
    if await is_owner(i):
        await i.channel.purge(limit=a); await log_action(i.guild, i.user, "Clear", f"כמות: {a}")
        await i.response.send_message(f"נמחקו {a} הודעות.", ephemeral=True)

@bot.tree.command(name="kick", description="[Owner] הוצאת משתמש")
async def ki(i, m: discord.Member, r: str = "ללא"):
    if await is_owner(i):
        await m.kick(reason=r); await log_action(i.guild, i.user, "Kick", f"משתמש: {m.name}")
        await i.response.send_message(f"👞 {m.name} הועף.", ephemeral=True)

@bot.tree.command(name="ban", description="[Owner] הרחקת משתמש")
async def ba(i, m: discord.Member, r: str = "ללא"):
    if await is_owner(i):
        await m.ban(reason=r); await log_action(i.guild, i.user, "Ban", f"משתמש: {m.name}")
        await i.response.send_message(f"🔨 {m.name} הורחק.", ephemeral=True)

@bot.tree.command(name="report", description="דיווח על משתמש")
async def rep(i, m: discord.Member, r: str):
    ch = i.guild.get_channel(CH_REPORTS)
    emb = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c); emb.add_field(name="מדווח:", value=i.user.mention); emb.add_field(name="על מי:", value=m.mention); emb.add_field(name="סיבה:", value=r)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="recommend", description="שלח המלצה")
async def reco(i, t: str):
    ch = i.guild.get_channel(CH_RECOMMENDATIONS)
    emb = discord.Embed(title="🌟 המלצה", description=t, color=0xf1c40f); emb.set_author(name=i.user.name)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ פורסם!", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת מצב")
async def st(i, m: discord.Member = None):
    target = m or i.user; b, w = get_data(target.id)
    await i.response.send_message(f"📊 **{target.name}**: 💰 `{b}` | ⚠️ `{w}`", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="[Owner] הקמת מערכת פידבק")
async def s_f(i):
    if await is_owner(i):
        await i.channel.send("📩 **שלחו לנו פידבק!**", view=FeedbackView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="setup_shop", description="[Owner] הקמת חנות")
async def s_s(i):
    if await is_owner(i):
        await i.channel.send("💠 **חנות רולים**", view=ShopView()); await i.response.send_message("הוקם.")

bot.run(TOKEN)
