import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs (תואם לשרת שלך) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535
CH_RECOMMENDATIONS = 1501947249658429470
CH_REPORTS = 1501946934779449505
MY_USER_ID = 1130542850883469443

jail_list = {} 
user_messages = {}

# --- 3. פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner_check(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == MY_USER_ID

# --- 4. פאנלים קבועים (Persistent Views) ---

# פאנל חנות - כאן החנות אחי!
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="🛡️ חסינות משוד (5,000)", style=discord.ButtonStyle.success, custom_id="shop_shield_v3")
    async def buy_shield(self, i, b):
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין לך מספיק כסף בחשבון!", ephemeral=True)
        update_data(i.user.id, b=bal-5000)
        await i.response.send_message("🛡️ קנית חסינות! השודד הבא שינסה אותך יקבל בראש.", ephemeral=True)

    @ui.button(label="❌ הורדת אזהרה (10,000)", style=discord.ButtonStyle.danger, custom_id="shop_unwarn_v3")
    async def buy_unwarn(self, i, b):
        bal, warns = get_data(i.user.id)
        if bal < 10000 or warns <= 0: return await i.response.send_message("או שאין לך כסף או שאין לך אזהרות!", ephemeral=True)
        update_data(i.user.id, b=bal-10000, w=warns-1)
        await i.response.send_message("✅ אזהרה אחת נמחקה לך מהתיק האישי!", ephemeral=True)

# פאנל פשיעה
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="heist_bank_v3")
    async def bank(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.2:
            win = random.randint(700, 1500); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הצלחת! שדדת {win} מטבעות!", ephemeral=True)
        else:
            jail_list[i.user.id] = 2500; update_data(i.user.id, b=max(0, bal-500))
            await i.response.send_message("🚨 נתפסת! נכנסת לכלא. ערבות: 2500", ephemeral=True)

    @ui.button(label="💳 היתרה שלי", style=discord.ButtonStyle.secondary, custom_id="heist_bal_v3")
    async def my_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💳 יתרה נוכחית: **{bal}**", ephemeral=True)

# --- 5. בוט ופקודות הקמה נפרדות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView())
        self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_shop", description="[Owner] הקמת פאנל החנות בערוץ")
async def s_shop(i: discord.Interaction):
    if await is_owner_check(i.user):
        embed = discord.Embed(title="🛒 חנות השרת הרשמית", description="כאן תוכלו לקנות שדרוגים וחסינויות בכסף שהרווחתם!", color=0x2ecc71)
        await i.channel.send(embed=embed, view=ShopView())
        await i.response.send_message("החנות הוקמה בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל הפשיעה והשודים")
async def s_heist(i: discord.Interaction):
    if await is_owner_check(i.user):
        embed = discord.Embed(title="🕵️ עולם הפשע", description="רוצים להרוויח כסף מהיר? נסו לשדוד את הבנק!", color=0xe74c3c)
        await i.channel.send(embed=embed, view=HeistPanelView())
        await i.response.send_message("פאנל פשיעה הוקם!", ephemeral=True)

# --- פקודות ניהול (Owner Only) ---
@bot.tree.command(name="warn", description="[Owner] מתן אזהרה למשתמש")
async def warn(i, m: discord.Member, r: str):
    if await is_owner_check(i.user):
        _, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר על: {r} (אזהרה מס' {w+1})")

@bot.tree.command(name="clear", description="[Owner] מחיקת הודעות")
async def clear(i, amount: int):
    if await is_owner_check(i.user):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🗑️ נוקו {amount} הודעות.", ephemeral=True)

# --- פקודות משתמש ---
@bot.tree.command(name="stats", description="בדיקת כסף ואזהרות")
async def stats(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **{t.name}** | 💰 כסף: {b} | ⚠️ אזהרות: {w}")

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # כסף על כל הודעה
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+15)
    await bot.process_commands(msg)

bot.run(TOKEN)
