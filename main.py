import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random
from firebase_admin import credentials, db

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות (ערוצים ורולים - שומר השרת) ---
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
ROLE_TICKET_STAFF = 1501316672345211041

MY_USER_ID = 1130542850883469443
user_messages = {}
rob_cooldowns = {}
last_robbed = {}

# --- 3. פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(i: discord.Interaction):
    if any(r.id == OWNER_ROLE_ID for r in i.user.roles) or i.user.id == MY_USER_ID: return True
    await i.response.send_message("❌ זה לאונר בלבד אחי!", ephemeral=True)
    return False

# --- 4. Views (שומר השרת + שודים) ---

class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר קורבן... 😈", min_values=1, max_values=1)
    async def callback(self, i: discord.Interaction):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600: return await i.response.send_message(f"❌ חכה {int((3600-diff)/60)} דקות.", ephemeral=True)
        victim = self.values[0]
        if last_robbed.get(uid) == victim.id: return await i.response.send_message("❌ לא פעמיים ברצף!", ephemeral=True)
        if victim.id == uid or victim.bot: return await i.response.send_message("❌ יעד לא חוקי.", ephemeral=True)
        s_bal, _ = get_data(uid); v_bal, _ = get_data(victim.id)
        if v_bal < 100: return await i.response.send_message("❌ הוא תפרן.", ephemeral=True)
        rob_cooldowns[uid] = datetime.now(); last_robbed[uid] = victim.id
        if random.randint(1, 100) <= 35:
            stolen = random.randint(50, min(300, int(v_bal * 0.25)))
            update_data(uid, b=s_bal+stolen); update_data(victim.id, b=v_bal-stolen)
            await i.response.send_message(f"🥷 שדדת מ-{victim.mention} סכום של {stolen}!", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal-300))
            await i.response.send_message("👮 נתפסת! קנס של 300.", ephemeral=True)

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600: return await i.response.send_message(f"❌ חכה {int((3600-diff)/60)} דקות.", ephemeral=True)
        s_bal, _ = get_data(uid); rob_cooldowns[uid] = datetime.now()
        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800)
            update_data(uid, b=s_bal+win); await i.response.send_message(f"💰 הבנק נשדד! {win} אצלך.", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת!", ephemeral=True)
    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        v = ui.View(); v.add_item(VictimSelect())
        await i.response.send_message("בחר קורבן:", view=v, ephemeral=True)
    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id); await i.response.send_message(f"💰 יתרה: {bal}", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="s2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    async def buy(self, i, p, rid):
        bal, _ = get_data(i.user.id)
        if bal < p: return await i.response.send_message("אין כסף!", ephemeral=True)
        update_data(i.user.id, b=bal-p); await i.user.add_roles(i.guild.get_role(rid))
        await i.response.send_message("תתחדש!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        r = i.guild.get_role(MEMBER_ROLE_ID)
        if r: await i.user.add_roles(r); await i.response.send_message("אומתת!", ephemeral=True)

# --- 5. הבוט ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

# --- 6. Events (שומר השרת) ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = msg.author.id; now = datetime.now()
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not any(r.id == OWNER_ROLE_ID for r in msg.author.roles):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושמת במיוט על ספאם.")
        return
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

# --- 7. פקודות Slash (החזרתי הכל!) ---

@bot.tree.command(name="setup_heist", description="[Owner] פאנל שודים")
async def s_h(i):
    if await is_owner(i):
        emb = discord.Embed(title="🕵️ Heist Zone", description="שוד בנק או משתמש? (פעם בשעה, עד 300)", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView()); await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_shop", description="[Owner] חנות")
async def s_s(i):
    if await is_owner(i): await i.channel.send("🛒 **חנות**", view=ShopView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="warn", description="[Owner] אזהרה")
async def w1(i, m: discord.Member, r: str):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.name} הוזהר.")

@bot.tree.command(name="mute", description="[Owner] מיוט")
async def m1(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message("הושתק.")

@bot.tree.command(name="clear", description="[Owner] ניקוי")
async def c1(i, a: int):
    if await is_owner(i): await i.channel.purge(limit=a); await i.response.send_message("נמחק.", ephemeral=True)

@bot.tree.command(name="stats", description="מצב")
async def s1(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id); await i.response.send_message(f"💰: {b} | ⚠️: {w}")

# --- הפעלת הבוט ---
bot.run(TOKEN)
