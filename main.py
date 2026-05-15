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
MUTE_ROLE_ID = 1501953906736103535
LOGS_CHANNEL_ID = 1504815433004617798
MY_USER_ID = 1130542850883469443

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

class RoleShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Staff", style=discord.ButtonStyle.primary, custom_id="s1")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["Ticket Staff 🎫"]
        if bal < pr: return await i.response.send_message("אין כסף!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("קנית!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🏦 שוד", style=discord.ButtonStyle.danger, custom_id="h1")
    async def b1(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.3:
            win = random.randint(2000, 5000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"הצלחתי! {win}", ephemeral=True)
            await send_log(i.guild, "💰 שוד", f"{i.user.mention} הצליח!", 0x2ecc71)
        else:
            jail_list[i.user.id] = 5000
            await i.response.send_message("נתפסת!", ephemeral=True)
            await send_log(i.guild, "🚓 שוד", f"{i.user.mention} נכשל!", 0xe74c3c)

# --- 5. הבוט והפקודות (20+) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(RoleShopView()); self.add_view(HeistView())
        await self.tree.sync()

bot = GuardBot()

# --- פקודות ניהול (Owner) ---
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if await is_owner(i.user):
        _, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"אזהרה ל-{m.mention}"); await send_log(i.guild, "⚠️ אזהרה", f"ל-{m.mention} על {r}", 0xff0000)

@bot.tree.command(name="unwarn")
async def unwarn(i, m: discord.Member):
    if await is_owner(i.user):
        _, w = get_data(m.id); update_data(m.id, w=max(0, w-1))
        await i.response.send_message("הורדתי אזהרה"); await send_log(i.guild, "✅ הורדת אזהרה", f"ל-{m.mention}", 0x00ff00)

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member, t: int):
    if await is_owner(i.user):
        await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"הושתק ל-{t} דקות"); await asyncio.sleep(t*60)
        await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID))

@bot.tree.command(name="unmute")
async def unmute(i, m: discord.Member):
    if await is_owner(i.user):
        await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message("שוחרר")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if await is_owner(i.user): await i.channel.purge(limit=a); await i.response.send_message("נוקה", ephemeral=True)

@bot.tree.command(name="add_money")
async def add_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"הוספתי {a}")
        await send_log(i.guild, "💰 כסף", f"נוסף ל-{m.mention}", 0x3498db)

@bot.tree.command(name="remove_money")
async def rem_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=max(0, b-a)); await i.response.send_message(f"הורדתי {a}")

@bot.tree.command(name="free_jail")
async def free(i, m: discord.Member):
    if await is_owner(i.user) and m.id in jail_list:
        del jail_list[m.id]; await i.response.send_message("שוחרר בחינם")

# --- פקודות משתמש ומידע ---
@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"📊 {t.name}: כסף {b} | אזהרות {w}")

@bot.tree.command(name="pay")
async def pay(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id)
    if b1 < a: return await i.response.send_message("אין כסף!")
    b2, _ = get_data(m.id); update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
    await i.response.send_message("הועבר!")

@bot.tree.command(name="top_rich")
async def top(i):
    await i.response.send_message("הכי עשירים: בקרוב!")

@bot.tree.command(name="jail_status")
async def j_s(i):
    text = "רשימת כלואים: " + ", ".join([str(k) for k in jail_list.keys()])
    await i.response.send_message(text or "אין כלואים")

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"פונג! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="server_info")
async def s_i(i): await i.response.send_message(f"שרת: {i.guild.name} | משתמשים: {i.guild.member_count}")

@bot.tree.command(name="bot_info")
async def b_i(i): await i.response.send_message("אני שומר השרת, הבוט הכי חזק פה!")

# פקודות הקמה
@bot.tree.command(name="setup_shop")
async def s_s(i):
    if await is_owner(i.user): await i.channel.send("🛒 חנות", view=RoleShopView()); await i.response.send_message("הוקם")

@bot.tree.command(name="setup_heist")
async def s_h(i):
    if await is_owner(i.user): await i.channel.send("🕵️ שוד", view=HeistView()); await i.response.send_message("הוקם")

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # הגנה פשוטה
    if "http" in msg.content and not await is_owner(msg.author): await msg.delete(); return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+25)
    await bot.process_commands(msg)

bot.run(TOKEN)
