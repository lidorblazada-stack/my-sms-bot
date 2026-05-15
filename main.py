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
CH_RECOMMENDATIONS = 1501947249658429470 # המלצות
CH_REPORTS = 1501946934779449505         # דיווחים על אנשים
CH_FEEDBACK = 1503475379942461522        # פידבק (עם כפתור ואנונימיות)
CH_OWNER_LOGS = 1503496964732354620      # לוג פקודות אונר
CH_ALT_LOGS = 1502014872655888554        # זיהוי אלטים
CH_WELCOME_BYE = 1501713652217282591     # וולקם וביי

# --- רולים ---
OWNER_ROLE_ID = 1499868525844627478
SUSPECT_ROLE_ID = 1503464176599695380    # רול חשוד
MUTE_ROLE_ID = 1501953906736103535       # רול מיוט (3 אזהרות)
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255

# ניהול זמן (Cooldown) ומניעת ספאם
last_feedback_time = {}
user_messages = {}

# --- פונקציות ליבה ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def log_owner_action(guild, user, command_name, details=""):
    ch = guild.get_channel(CH_OWNER_LOGS)
    if ch:
        emb = discord.Embed(title="🔨 פקודת אונר בוצעה", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="מבצע:", value=user.mention)
        emb.add_field(name="פקודה:", value=command_name)
        if details: emb.add_field(name="פרטים:", value=details, inline=False)
        await ch.send(embed=emb)

# --- מערכת אלטים (Buttons) ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i: discord.Interaction, button: ui.Button):
        m = i.guild.get_member(self.member_id)
        if m: await m.kick(); await i.message.edit(content=f"✅ {m.name} הועף.", view=None)

    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i: discord.Interaction, button: ui.Button):
        m = i.guild.get_member(self.member_id)
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.message.edit(content=f"⚠️ {m.name} קיבל רול חשוד.", view=None)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def stay_alt(self, i: discord.Interaction, button: ui.Button):
        await i.message.edit(content=f"✅ המשתמש אושר להישאר.", view=None)

# --- חלון פידבק (Modal) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק חדש'):
    text = ui.TextInput(label='מה תרצה להגיד לנו?', style=discord.TextStyle.long, required=True)
    anon = ui.TextInput(label='אנונימי? (כן/לא)', default='כן', max_length=2)

    async def on_submit(self, i: discord.Interaction):
        now = datetime.now()
        if i.user.id in last_feedback_time and (now - last_feedback_time[i.user.id]).seconds < 300:
            return await i.response.send_message("❌ ניתן לשלוח פידבק פעם ב-5 דקות!", ephemeral=True)
        
        last_feedback_time[i.user.id] = now
        ch = i.guild.get_channel(CH_FEEDBACK)
        is_anon = self.anon.value.strip() == "כן"
        emb = discord.Embed(title="📩 פידבק מהקהילה", description=self.text.value, color=0x3498db, timestamp=now)
        emb.set_author(name="🕵️ אנונימי" if is_anon else f"👤 {i.user.name}")
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ הפידבק נשלח בהצלחה!", ephemeral=True)

# --- Views עבור Setup ---
class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק חדש 📩", style=discord.ButtonStyle.primary, custom_id="f_btn_new")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️ (2000)", style=discord.ButtonStyle.secondary, custom_id="s_sup")
    async def s1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="VIP 💎 (5000)", style=discord.ButtonStyle.primary, custom_id="s_vip")
    async def s2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    async def buy(self, i, p, rid, name):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("❌ אין לך מספיק כסף!", ephemeral=True)
        update_data(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message(f"✅ תתחדש! קנית את הרול {name}", ephemeral=True)

# --- Bot Core ---
class UltimateGuard(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(FeedbackView()); self.add_view(ShopView())
        await self.tree.sync()

bot = UltimateGuard()

@bot.event
async def on_member_join(member):
    # Welcome (בידיוק כמו בתמונה)
    ch = member.guild.get_channel(CH_WELCOME_BYE)
    if ch:
        emb = discord.Embed(title="🔥 ברוך הבא לשרת ספאמר הכי טוב בארץ 🔥", description=f"שלום {member.mention}, אתה מספר **{len(member.guild.members)}** שהצטרף אלינו.\n\nעם אתה מתקשה פתח טיקט לעזרה ונדבר", color=0xff4500)
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        await ch.send(content=f"{member.mention}", embed=emb)

    # Alt Detector
    if (datetime.utcnow() - member.created_at).days < 14:
        alt_ch = member.guild.get_channel(CH_ALT_LOGS)
        if alt_ch:
            emb = discord.Embed(title="🚨 זיהוי חשבון אלט חשוד", description=f"המשתמש {member.mention} נוצר לפני פחות מ-14 יום.", color=0xffa500)
            await alt_ch.send(embed=emb, view=AltActionView(member.id))

@bot.event
async def on_member_remove(member):
    # Goodbye (בידיוק כמו בתמונה)
    ch = member.guild.get_channel(CH_WELCOME_BYE)
    if ch:
        emb = discord.Embed(title="😢 Cyber-Alt-Detector עזב.", description=f"נשארנו **{len(member.guild.members)}** חברים.", color=0xff0000)
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        await ch.send(embed=emb)

@bot.tree.command(name="report", description="דיווח על משתמש")
async def report(i, member: discord.Member, reason: str):
    ch = i.guild.get_channel(CH_REPORTS)
    emb = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c, timestamp=datetime.now())
    emb.add_field(name="מדווח:", value=i.user.mention)
    emb.add_field(name="על מי:", value=member.mention)
    emb.add_field(name="סיבה:", value=reason, inline=False)
    emb.set_footer(text="Developed by Nehoray Owner 👑")
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ הדיווח נשלח לצוות.", ephemeral=True)

@bot.tree.command(name="recommend", description="שלח המלצה לשרת")
async def recommend(i, text: str):
    ch = i.guild.get_channel(CH_RECOMMENDATIONS)
    emb = discord.Embed(title="🌟 המלצה חדשה", description=text, color=0xf1c40f)
    emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ ההמלצה פורסמה!", ephemeral=True)

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה רשמית")
async def warn(i, member: discord.Member, reason: str):
    if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
    b, w = get_data(member.id); update_data(member.id, w=w+1)
    await log_owner_action(i.guild, i.user, "Warn", f"הוזהר: {member.mention}\nסיבה: {reason}\nאזהרה מספר: {w+1}")
    if w+1 >= 3:
        r = i.guild.get_role(MUTE_ROLE_ID)
        if r: await member.add_roles(r)
        await i.channel.send(f"🔇 {member.mention} קיבל מיוט אוטומטי לאחר 3 אזהרות.")
    await i.response.send_message(f"⚠️ אזהרה נרשמה ל-{member.name}.", ephemeral=True)

@bot.tree.command(name="setup_feedback_system")
async def sfs(i):
    if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
    await i.channel.send("📩 **מערכת פידבק**\nלחצו על הכפתור למטה כדי לשלוח פידבק/הצעה (ניתן באנונימיות).", view=FeedbackView())
    await i.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="setup_shop")
async def ss(i):
    if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
    await i.channel.send("💠 **חנות השרת**", view=ShopView())
    await i.response.send_message("בוצע.", ephemeral=True)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    # כלכלה פשוטה
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+5)
    await bot.process_commands(msg)

bot.run(TOKEN)
