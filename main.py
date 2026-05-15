import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random
from firebase_admin import credentials, db

# --- חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- הגדרת ערוצים ---
CH_OWNER_LOGS = 1503496964732354620      
CH_ALT_LOGS = 1502014872655888554        
CH_WELCOME_BYE = 1501713652217282591     

# --- רולים ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
MEMBER_ROLE_ID = 1501983948111352091

MY_USER_ID = 1130542850883469443
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
    await i.response.send_message("❌ גישה חסומה!", ephemeral=True)
    return False

# --- פאנל שודים משודרג ---
class RobUserModal(ui.Modal, title='שוד משתמש 🥷'):
    user_id = ui.TextInput(label='הכנס ID של הקורבן', placeholder='למשל: 1130542850883469443', min_length=15)
    async def on_submit(self, i: discord.Interaction):
        try:
            victim = i.guild.get_member(int(self.user_id.value))
            if not victim or victim.id == i.user.id:
                return await i.response.send_message("❌ משתמש לא נמצא או שזה אתה!", ephemeral=True)
            
            s_bal, _ = get_data(i.user.id)
            v_bal, _ = get_data(victim.id)
            if v_bal < 200: return await i.response.send_message("הוא עני מדי אחי.", ephemeral=True)

            if random.randint(1, 100) <= 35:
                stolen = random.randint(100, int(v_bal * 0.25))
                update_data(i.user.id, b=s_bal+stolen); update_data(victim.id, b=v_bal-stolen)
                emb = discord.Embed(title="✅ שוד מוצלח!", description=f"רוקנת את הכיסים של {victim.mention} ולקחת **{stolen}** מטבעות!", color=0x2ecc71)
                await i.response.send_message(embed=emb)
            else:
                update_data(i.user.id, b=max(0, s_bal-300))
                await i.response.send_message("👮 נתפסת! שילמת קנס של 300 מטבעות.", ephemeral=True)
        except:
            await i.response.send_message("❌ קרתה שגיאה, וודא שה-ID נכון.", ephemeral=True)

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק (סיכון גבוה) 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank", row=0)
    async def h_bank(self, i, b):
        s_bal, _ = get_data(i.user.id)
        if random.randint(1, 100) <= 20:
            win = random.randint(1500, 4000)
            update_data(i.user.id, b=s_bal + win)
            emb = discord.Embed(title="💰 הקופה הגדולה!", description=f"חדרת לכספת הבנק ולקחת **{win}** מטבעות!", color=0xf1c40f)
            await i.response.send_message(embed=emb, ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal - 600))
            await i.response.send_message("🚨 האזעקה הופעלה! ברחת אבל איבדת 600 מטבעות.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user", row=0)
    async def h_user(self, i, b):
        await i.response.send_modal(RobUserModal())

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal", row=1)
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 היתרה הנוכחית שלך: **{bal}**", ephemeral=True)

# --- שאר המערכות (חנות, אימות, אלטים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop_1")
    async def b1(self, i, b): await self.buy(i, 2000, 1503819239310627068)
    async def buy(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("אין כסף!", ephemeral=True)
        update_data(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message("תתחדש!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b): await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID)); await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView()); self.add_view(ShopView()); self.add_view(VerifyView())
        await self.tree.sync()

bot = GuardBot()

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

# --- פקודות הנהלה ופאנלים ---

@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל פשיעה מעוצב")
async def s_h(i):
    if await is_owner(i):
        emb = discord.Embed(title="🎭 עולם הפשע של השרת", description="כאן תוכלו להרוויח כסף מהיר, אבל תיזהרו מהמשטרה!\n\n**🏦 שוד בנק:** סיכון גבוה, פרס ענק.\n**🥷 שוד משתמש:** לגנוב מחבר (צריך ID).\n**💳 יתרה:** כמה כסף יש לך בכיס.", color=0x2b2d31)
        emb.set_image(url="https://images.alphacoders.com/519/519509.jpg")
        await i.channel.send(embed=emb, view=HeistPanelView()); await i.response.send_message("הפאנל הוקם!", ephemeral=True)

@bot.tree.command(name="setup_shop", description="[Owner] חנות")
async def s_s(i):
    if await is_owner(i): await i.channel.send("🛒 **חנות השרת**", view=ShopView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="setup_verify", description="[Owner] אימות")
async def s_v(i):
    if await is_owner(i): await i.channel.send("🛡️ **אימות**", view=VerifyView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="clear", description="[Owner] ניקוי")
async def cl(i, a: int):
    if await is_owner(i): await i.channel.purge(limit=a); await i.response.send_message("נמחקו הודעות.", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת כסף")
async def st(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"💰 כסף: {b} | ⚠️ אזהרות: {w}")

# --- שאר 15 הפקודות (Mute, Ban, Kick וכו') ---
@bot.tree.command(name="mute", description="[Owner] השתקה")
async def mu(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"{m.name} הושתק.")

@bot.tree.command(name="ban", description="[Owner] הרחקה")
async def ba(i, m: discord.Member):
    if await is_owner(i): await m.ban(); await i.response.send_message(f"{m.name} הורחק.")

@bot.tree.command(name="add_money", description="[Owner] הוספת כסף")
async def am(i, m: discord.Member, a: int):
    if await is_owner(i): b, w = get_data(m.id); update_data(m.id, b=b+a); await i.response.send_message(f"נוספו {a}")

bot.run(TOKEN)
