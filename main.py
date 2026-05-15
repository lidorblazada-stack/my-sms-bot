import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבור משתני סביבה (חובה עבור Render!) ---
# תוודא ששמת את אלו ב-Variables ב-Render
TOKEN = os.getenv('DISCORD_TOKEN') 
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

# חיבור ל-Firebase
if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535
LOGS_CHANNEL_ID = 1504815433004617798
VERIFY_ROLE_ID = 1501953906736103535 
FEEDBACK_CHANNEL_ID = 1504815433004617798
WELCOME_CHANNEL_ID = 1501946934779449505
AUTO_ROLE_ID = 1501953906736103535

SHOP_ROLES = {
    "Ticket Staff 🎫": [1501316672345211041, 25000],
    "VIP 💎": [1503817695466881255, 50000],
    "Server Supporter ⚫": [1503819239310627068, 75000]
}

jail_list = {}

# --- פונקציות עזר ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == 1130542850883469443

# --- פאנלים (Views) ---

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="✅ אימות חשבון", style=discord.ButtonStyle.success, custom_id="v_lidor")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(VERIFY_ROLE_ID))
        await i.response.send_message("אומתת!", ephemeral=True)

class FeedbackModal(ui.Modal, title="פידבק ללידור"):
    msg = ui.TextInput(label="מה תרצה להגיד לנו?", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CHANNEL_ID)
        await ch.send(f"📩 **פידבק מ-{i.user.mention}:**\n{self.msg.value}")
        await i.response.send_message("נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="f_lidor")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

class RoleShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Ticket Staff (25k)", style=discord.ButtonStyle.primary, custom_id="s_1")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["Ticket Staff 🎫"]
        if bal < pr: return await i.response.send_message("אין כסף!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("קנית!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_1")
    async def h(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.25:
            win = random.randint(2000, 6000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הצלחת! {win}", ephemeral=True)
        else:
            jail_list[i.user.id] = 5000; await i.response.send_message("🚓 נתפסת!", ephemeral=True)

# --- הקמת הבוט ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView())
        self.add_view(RoleShopView()); self.add_view(HeistView())
        await self.tree.sync()

bot = GuardBot()

# --- פקודות הקמה מופרדות ---
@bot.tree.command(name="setup_verify")
async def s_v(i):
    if await is_owner(i.user):
        await i.channel.send("🛡️ **אימות**", view=VerifyView()); await i.response.send_message("הוקם")

@bot.tree.command(name="setup_feedback")
async def s_f(i):
    if await is_owner(i.user):
        await i.channel.send("📩 **פידבקים**", view=FeedbackView()); await i.response.send_message("הוקם")

@bot.tree.command(name="setup_shop")
async def s_s(i):
    if await is_owner(i.user):
        await i.channel.send("🛒 **חנות**", view=RoleShopView()); await i.response.send_message("הוקם")

@bot.tree.command(name="setup_heist")
async def s_h(i):
    if await is_owner(i.user):
        await i.channel.send("🕵️ **פשיעה**", view=HeistView()); await i.response.send_message("הוקם")

# --- פקודות ניהול וכלכלה (השאר) ---
@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"📊 {t.name}: {b} מטבעות")

@bot.tree.command(name="add_money")
async def add_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message("בוצע")

# --- אירועים ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+25)
    await bot.process_commands(msg)

# הפעלה סופית - TOKEN חייב להיות מוגדר למעלה!
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: TOKEN is missing!")
