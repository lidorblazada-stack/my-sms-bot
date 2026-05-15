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

# --- 2. הגדרות IDs (מעודכן לפי הבקשות שלך) ---
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

# --- 3. פונקציות עזר ונתונים ---
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
    
    @ui.button(label="🎫 Ticket Staff (25k)", style=discord.ButtonStyle.primary, custom_id="buy_staff_imp")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["Ticket Staff 🎫"]
        if bal < pr: return await i.response.send_message("אין לך מספיק כסף!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("מזל טוב! קנית רול סטאף 🎫", ephemeral=True)
        await send_log(i.guild, "🛍️ קנייה בחנות", f"{i.user.mention} קנה את הרול Ticket Staff", 0x9b59b6)

    @ui.button(label="💎 VIP (50k)", style=discord.ButtonStyle.primary, custom_id="buy_vip_imp")
    async def b2(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["VIP 💎"]
        if bal < pr: return await i.response.send_message("חסר לך כסף ל-VIP!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("שיחקת אותה! קיבלת VIP 💎", ephemeral=True)

class HeistMasterView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="bank_h_imp")
    async def heist(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא אחי!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.25:
            win = random.randint(2000, 5000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הפיצוח הצליח! לקחת {win}!", ephemeral=True)
            await send_log(i.guild, "💰 שוד בנק מוצלח", f"השודד: {i.user.mention}\nסכום: {win}", 0x2ecc71)
        else:
            jail_list[i.user.id] = 5000; update_data(i.user.id, b=max(0, bal-1000))
            await i.response.send_message("🚨 נתפסת! אתה בכלא. ערבות: 5,000", ephemeral=True)
            await send_log(i.guild, "🚓 שוד בנק נכשל", f"החשוד: {i.user.mention}\nסטטוס: נכנס לכלא", 0xe74c3c)

    @ui.button(label="🔓 שחרור בערבות (5k)", style=discord.ButtonStyle.success, custom_id="bail_h_imp")
    async def bail(self, i, b):
        if i.user.id not in jail_list: return await i.response.send_message("אתה לא בכלא אחי.", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין כסף לערבות!", ephemeral=True)
        update_data(i.user.id, b=bal-5000); del jail_list[i.user.id]
        await i.response.send_message("🔓 שילמת ויצאת!", ephemeral=True)
        await send_log(i.guild, "🔓 שחרור מהכלא", f"{i.user.mention} שילם ערבות ויצא", 0xf1c40f)

    @ui.button(label="💳 בדיקת יתרה", style=discord.ButtonStyle.secondary, custom_id="bal_h_imp")
    async def balance(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💳 היתרה שלך: **{bal}**", ephemeral=True)

# --- 5. הבוט והפקודות (20+ פקודות) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(RoleShopView()); self.add_view(HeistMasterView())
        await self.tree.sync()

bot = GuardBot()

# --- פקודות ניהול (אונר בלבד + לוגים) ---
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if await is_owner(i.user):
        _, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} קיבל אזהרה."); await send_log(i.guild, "⚠️ אזהרה", f"ל-{m.mention} על {r} על ידי {i.user.mention}", 0xffa500)

@bot.tree.command(name="unwarn")
async def unwarn(i, m: discord.Member):
    if await is_owner(i.user):
        _, w = get_data(m.id); update_data(m.id, w=max(0, w-1))
        await i.response.send_message("הורדתי אזהרה."); await send_log(i.guild, "✅ הסרת אזהרה", f"ל-{m.mention} על ידי {i.user.mention}", 0x00ff00)

@bot.tree.command(name="mute")
async def mute(i, m: discord.Member, t: int):
    if await is_owner(i.user):
        role = i.guild.get_role(MUTE_ROLE_ID); await m.add_roles(role)
        await i.response.send_message(f"הושתק ל-{t} דקות."); await asyncio.sleep(t*60); await m.remove_roles(role)

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if await is_owner(i.user): await i.channel.purge(limit=a); await i.response.send_message("נוקה", ephemeral=True)

@bot.tree.command(name="add_money")
async def add_m(i, m: discord.Member, a: int):
    if await is_owner(i.user):
        b, _ = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"הוספתי {a} ל-{m.mention}")
        await send_log(i.guild, "💰 תוספת כסף", f"האונר הוסיף {a} ל-{m.mention}", 0x3498db)

@bot.tree.command(name="free_jail")
async def free(i, m: discord.Member):
    if await is_owner(i.user) and m.id in jail_list:
        del jail_list[m.id]; await i.response.send_message(f"שחררת את {m.mention} בחינם!")

# --- פקודות משתמש וכלכלה ---
@bot.tree.command(name="rob", description="לשדוד משתמש אחר")
async def rob(i, m: discord.Member):
    if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!")
    if await is_owner(m): return await i.response.send_message("❌ אל תתעסק עם האונר!")
    b1, _ = get_data(i.user.id); b2, _ = get_data(m.id)
    if b2 < 500: return await i.response.send_message("אין לו מספיק כסף לשדוד אחי.")
    if random.random() < 0.3:
        win = int(b2 * 0.2); update_data(i.user.id, b=b1+win); update_data(m.id, b=b2-win)
        await i.response.send_message(f"🥷 שדדת {win} מ-{m.name}!"); await send_log(i.guild, "🥷 שוד משתמש", f"{i.user.mention} שדד את {m.mention}", 0x9b59b6)
    else:
        jail_list[i.user.id] = 2000; await i.response.send_message("🚓 נתפסת! נכנסת לכלא."); await send_log(i.guild, "🚓 שוד נכשל", f"{i.user.mention} ניסה לשדוד את {m.mention} ונתפס", 0xe74c3c)

@bot.tree.command(name="stats")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"📊 **{t.name}** | כסף: {b} | אזהרות: {w}")

@bot.tree.command(name="pay")
async def pay(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id)
    if b1 < a: return await i.response.send_message("אין לך מספיק כסף!")
    b2, _ = get_data(m.id); update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
    await i.response.send_message(f"העברת {a} מטבעות ל-{m.mention}")

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms")

# פקודות הקמה
@bot.tree.command(name="setup_server")
async def s_s(i):
    if await is_owner(i.user):
        await i.channel.send("🛒 **חנות הרולים**", view=RoleShopView())
        await i.channel.send("🕵️ **מרחב הפשיעה**", view=HeistMasterView())
        await i.response.send_message("הוקם!")

# --- 6. הגנות (אנטי לינקים וכסף על הודעה) ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    if "http" in msg.content and not await is_owner(msg.author):
        await msg.delete(); await msg.channel.send(f"{msg.author.mention}, בלי לינקים!", delete_after=3); return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+25)
    await bot.process_commands(msg)

bot.run(TOKEN)
