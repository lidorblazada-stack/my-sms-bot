import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, re
from firebase_admin import credentials, db

# --- חיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- IDs מעודכנים ---
WELCOME_CH_ID = 1501713652217282591    # ערוץ וולקם ובאי
OWNER_ROLE_ID = 1499868525844627478
LOG_CH_ID = 1503496964732354620
ALT_LOG_ID = 1503464176599695380       
SUSPECT_ROLE_ID = 1503464176599695380   
MUTE_ROLE_ID = 1501953906736103535      
MEMBER_ROLE_ID = 1501983948111352091
FEEDBACK_CH_ID = 1503475379942461522

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255

user_messages = {}

# --- פונקציות עזר ---
def get_user_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_user_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_user_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def check_is_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles): return True
    await i.response.send_message("❌ פקודה לאונר בלבד!", ephemeral=True)
    return False

# --- מערכת כפתורי ניהול אלטים ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def kick_alt(self, i: discord.Interaction, button: ui.Button):
        if not await check_is_owner(i): return
        member = i.guild.get_member(self.member_id)
        if member:
            await member.kick(reason="אלט חשוד")
            await i.message.edit(content=f"✅ המשתמש הועף.", view=None)

    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_suspect")
    async def suspect_alt(self, i: discord.Interaction, button: ui.Button):
        if not await check_is_owner(i): return
        member = i.guild.get_member(self.member_id)
        role = i.guild.get_role(SUSPECT_ROLE_ID)
        if member and role:
            await member.add_roles(role)
            await i.message.edit(content=f"⚠️ הוגדר כחשוד.", view=None)

    @ui.button(label="לאשר ✅", style=discord.ButtonStyle.success, custom_id="alt_approve")
    async def approve_alt(self, i: discord.Interaction, button: ui.Button):
        if not await check_is_owner(i): return
        await i.message.edit(content=f"✅ החשבון אושר.", view=None)

# --- Views נוספים ---
class FeedbackModal(ui.Modal, title='משוב אנונימי'):
    text = ui.TextInput(label='המשוב שלך', style=discord.TextStyle.long, required=True)
    anon = ui.TextInput(label='אנונימי? (כן/לא)', default='כן', min_length=2, max_length=2)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip() == "כן"
        if ch:
            emb = discord.Embed(title="📩 משוב", description=self.text.value, color=0x3498db)
            emb.add_field(name="שולח:", value="🕵️ אנונימי" if is_anon else f"👤 {i.user.mention}")
            await ch.send(embed=emb)
            await i.response.send_message("נשלח!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r)
        await i.response.send_message("אומתת!", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s_sup")
    async def s1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="s_vip")
    async def s2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")
    async def buy(self, i, p, rid, name):
        bal, _ = get_user_data(i.user.id)
        if bal < p: return await i.response.send_message("אין כסף!", ephemeral=True)
        update_user_data(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message(f"קנית {name}!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח משוב 📩", style=discord.ButtonStyle.gray, custom_id="f_btn")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- Bot Core ---
class UltimateBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(ShopView()); self.add_view(FeedbackView())
        await self.tree.sync()

bot = UltimateBot()

@bot.event
async def on_member_join(member):
    # הודעת Welcome
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        count = len(member.guild.members)
        emb = discord.Embed(
            title="🔥 ברוך הבא לשרת ספאמר הכי טוב בארץ 🔥",
            description=f"שלום {member.mention}, אתה מספר **{count}** שהצטרף אלינו.\n\nעם אתה מתקשה פתח טיקט לעזרה ונדבר",
            color=0xff4500
        )
        emb.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        emb.set_footer(text="Developed by Nehoray Owner 👑")
        await ch.send(f"{member.mention}", embed=emb)

    # בדיקת אלטים
    if (datetime.utcnow() - member.created_at).days < 14:
        alt_ch = member.guild.get_channel(ALT_LOG_ID)
        if alt_ch:
            await alt_ch.send(f"🚨 **חשבון חדש:** {member.mention}", view=AltActionView(member.id))

@bot.event
async def on_member_remove(member):
    # הודעת Goodbye
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        count = len(member.guild.members)
        emb = discord.Embed(
            title=f"😢 Cyber-Alt-Detector עזב.",
            description=f"נשארנו **{count}** חברים.",
            color=0xff0000
        )
        emb.set_footer(text="Developed by NL Owner 👑")
        await ch.send(embed=emb)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    is_owner = any(r.id == OWNER_ROLE_ID for r in msg.author.roles)
    if not is_owner:
        if re.search(r'http[s]?://|discord\.gg/', msg.content):
            await msg.delete(); return
        uid = msg.author.id; now = datetime.now()
        user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            role = msg.guild.get_role(MUTE_ROLE_ID)
            if role: await msg.author.add_roles(role)
            return
    b, w = get_user_data(msg.author.id); update_user_data(msg.author.id, b=b+5)
    await bot.process_commands(msg)

# --- פקודות Setup ---
@bot.tree.command(name="setup_verify")
async def sv(i):
    if await check_is_owner(i):
        await i.channel.send("🛡️ **אימות**", view=VerifyView())
        await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_shop")
async def ss(i):
    if await check_is_owner(i):
        await i.channel.send("💠 **חנות**", view=ShopView())
        await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback")
async def sf(i):
    if await check_is_owner(i):
        await i.channel.send("📩 **משוב**", view=FeedbackView())
        await i.response.send_message("בוצע", ephemeral=True)

bot.run(TOKEN)
