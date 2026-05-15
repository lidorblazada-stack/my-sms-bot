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

# --- 2. הגדרות IDs (מעודכן לפי התמונות והבקשות שלך) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535
LOGS_CHANNEL_ID = 1504815433004617798
WELCOME_CHANNEL_ID = 1501946934779449505 
AUTO_ROLE_ID = 1501953906736103535
MY_USER_ID = 1130542850883469443

# רולים מהתמונות שלך: [ID, מחיר]
SHOP_ROLES = {
    "Ticket Staff 🎫": [1501316672345211041, 25000],
    "VIP 💎": [1503817695466881255, 50000],
    "Server Supporter ⚫": [1503819239310627068, 75000]
}

jail_list = {} 

# --- 3. פונקציות נתונים ולוגים ---
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

# --- 4. פאנלים קבועים (Views) ---

class RoleShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Ticket Staff (25k)", style=discord.ButtonStyle.primary, custom_id="s_staff")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["Ticket Staff 🎫"]
        if bal < pr: return await i.response.send_message("אין כסף אחי!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("קנית רול סטאף!", ephemeral=True)
        await send_log(i.guild, "🛒 קנייה", f"{i.user.mention} קנה Ticket Staff", 0x9b59b6)

    @ui.button(label="💎 VIP (50k)", style=discord.ButtonStyle.primary, custom_id="s_vip")
    async def b2(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["VIP 💎"]
        if bal < pr: return await i.response.send_message("אין כסף!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("קנית VIP!", ephemeral=True)

class HeistMasterView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="m_heist")
    async def heist(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.25:
            win = random.randint(2000, 6000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הצלחת! הרווחת {win}", ephemeral=True)
            await send_log(i.guild, "💰 שוד בנק", f"{i.user.mention} הצליח ושדד {win}", 0x2ecc71)
        else:
            jail_list[i.user.id] = 5000; update_data(i.user.id, b=max(0, bal-1000))
            await i.response.send_message("🚨 נתפסת! ערבות: 5,000", ephemeral=True)
            await send_log(i.guild, "🚓 שוד נכשל", f"{i.user.mention} נכנס לכלא", 0xe74c3c)

    @ui.button(label="🔓 שחרור (5k)", style=discord.ButtonStyle.success, custom_id="m_bail")
    async def bail(self, i, b):
        if i.user.id not in jail_list: return await i.response.send_message("אתה לא בכלא", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין כסף לערבות!", ephemeral=True)
        update_data(i.user.id, b=bal-5000); del jail_list[i.user.id]
        await i.response.send_message("🔓 שוחררת!", ephemeral=True)

    @ui.button(label="💳 יתרה", style=discord.ButtonStyle.secondary, custom_id="m_bal")
    async def bal_btn(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"היתרה שלך: {bal}", ephemeral=True)

# --- 5. הבוט, אירועים ו-20+ פקודות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(RoleShopView()); self.add_view(HeistMasterView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role: await member.add_roles(role)
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=f"ברוך הבא, {member.name}! 👋", description="שמחים שאתה כאן!", color=0x3498db)
        await channel.send(content=member.mention, embed=embed)

@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if await is_owner(i.user):
        _, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר."); await send_log(i.guild, "⚠️ אזהרה", f"{m.mention} על {r}", 0xffa500)

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member, t: int):
    if await is_owner(i.user):
        await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"הושתק ל-{t} דק'.")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if await is_owner(i.user): await i.channel.purge(limit=a); await i.response.send_message("נוקה", ephemeral=True)

@bot.tree.command(name="add_money")
async def add_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"הוספתי {a}")

@bot.tree.command(name="rob")
async def rob(i, m: discord.Member):
    if i.user.id in jail_list: return await i.response.send_message("בכלא!")
    b1, _ = get_data(i.user.id); b2, _ = get_data(m.id)
    if b2 < 1000: return await i.response.send_message("אין לו כסף!")
    if random.random() < 0.3:
        win = int(b2 * 0.2); update_data(i.user.id, b=b1+win); update_data(m.id, b=b2-win)
        await i.response.send_message(f"שדדת {win}!"); await send_log(i.guild, "🥷 שוד", f"{i.user.mention} שדד את {m.mention}", 0x9b59b6)
    else:
        jail_list[i.user.id] = 2000; await i.response.send_message("נתפסת!"); await send_log(i.guild, "🚓 כלא", f"{i.user.mention} נתפס", 0xe74c3c)

@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"📊 {t.name}: {b} מטבעות | {w} אזהרות")

@bot.tree.command(name="pay")
async def pay(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id)
    if b1 < a: return await i.response.send_message("אין כסף!")
    b2, _ = get_data(m.id); update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
    await i.response.send_message(f"שלחת {a} ל-{m.name}")

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="setup_server")
async def setup(i):
    if await is_owner(i.user):
        await i.channel.send("🛒 **חנות הרולים**", view=RoleShopView())
        await i.channel.send("🕵️ **פאנל פשיעה**", view=HeistMasterView())
        await i.response.send_message("הוקם!")

# (המשך פקודות: bot_info, server_info, free_jail, unmute, unwarn, remove_money...)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    if "http" in msg.content and not await is_owner(msg.author):
        await msg.delete(); return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+25)
    await bot.process_commands(msg)

bot.run(TOKEN)
