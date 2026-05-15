import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs ---
OWNER_ROLE_ID = 1499868525844627478
MY_USER_ID = 1130542850883469443
LOGS_CHANNEL_ID = 1504815433004617798 # ערוץ הלוגים של השודים והניהול

SHOP_ROLES = {
    "Ticket Staff 🎫": [1501316672345211041, 25000],
    "VIP 💎": [1503817695466881255, 50000],
    "Server Supporter ⚫": [1503819239310627068, 75000]
}

jail_list = {} 

# --- 3. פונקציות עזר ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == MY_USER_ID

async def send_log(guild, title, text, color):
    ch = guild.get_channel(LOGS_CHANNEL_ID)
    if ch:
        embed = discord.Embed(title=title, description=text, color=color, timestamp=datetime.now())
        await ch.send(embed=embed)

# --- 4. פאנלים (Views) ---

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_master_v5")
    async def heist(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        
        if random.random() < 0.25: # הצלחה
            win = random.randint(2000, 4500)
            update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הצלחת! הרווחת {win}", ephemeral=True)
            # לוג הצלחה
            await send_log(i.guild, "💰 שוד בנק מוצלח!", f"**השודד:** {i.user.mention}\n**סכום שנגנב:** {win} מטבעות", 0x2ecc71)
        else: # כישלון
            jail_list[i.user.id] = 5000
            update_data(i.user.id, b=max(0, bal-1000))
            await i.response.send_message("🚨 נתפסת! אתה בכלא. ערבות: 5000", ephemeral=True)
            # לוג כישלון
            await send_log(i.guild, "🚓 שוד בנק נכשל!", f"**החשוד:** {i.user.mention}\n**סטטוס:** נכנס לכלא (ערבות 5000)", 0xe74c3c)

    @ui.button(label="🔓 שחרור בערבות", style=discord.ButtonStyle.success, custom_id="b_master_v5")
    async def bail(self, i, b):
        if i.user.id not in jail_list: return await i.response.send_message("אתה לא בכלא", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין לך מספיק כסף לערבות!", ephemeral=True)
        update_data(i.user.id, b=bal-5000); del jail_list[i.user.id]
        await i.response.send_message("🔓 שילמת ויצאת!", ephemeral=True)
        await send_log(i.guild, "🔓 שחרור מהכלא", f"**המשתמש:** {i.user.mention}\n**סטטוס:** שילם ערבות ויצא", 0xf1c40f)

# --- 5. בוט ופקודות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_heist")
async def s_h(i):
    if await is_owner(i.user):
        await i.channel.send("🕵️ **פאנל פשיעה ושחרור**", view=HeistView())
        await i.response.send_message("הוקם!", ephemeral=True)

@bot.tree.command(name="add_money")
async def add_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=b+a)
        await i.response.send_message(f"הוספתי {a} ל-{m.mention}")
        await send_log(i.guild, "💸 העברת כסף (אונר)", f"**אונר:** {i.user.mention}\n**מקבל:** {m.mention}\n**סכום:** {a}", 0x3498db)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # הגנה בסיסית ומתן כסף
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+25)
    await bot.process_commands(msg)

bot.run(TOKEN)
