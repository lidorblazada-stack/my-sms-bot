import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs (שומר השרת) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
MEMBER_ROLE_ID = 1501983948111352091
MY_USER_ID = 1130542850883469443

# ערוצי לוגים וניהול
CH_OWNER_LOGS = 1503496964732354620      
CH_ALT_LOGS = 1502014872655888554        

# רשימות בזיכרון
user_messages = {}
rob_cooldowns = {}
jail_list = {}
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
    await i.response.send_message("❌ גישה לאונר בלבד!", ephemeral=True)
    return False

# --- 4. מערכת המשטרה והכלא ---
class PoliceCallView(ui.View):
    def __init__(self, robber, victim, amount):
        super().__init__(timeout=10)
        self.robber, self.victim, self.amount = robber, victim, amount
        self.caught = False

    @ui.button(label="🚨 קרא למשטרה!", style=discord.ButtonStyle.danger)
    async def call_police(self, i: discord.Interaction, b: ui.Button):
        self.caught = True
        self.stop()
        jail_list[self.robber.id] = datetime.now() # כניסה לכלא
        r_bal, _ = get_data(self.robber.id); v_bal, _ = get_data(self.victim.id)
        update_data(self.robber.id, b=max(0, r_bal - (self.amount + 200)))
        update_data(self.victim.id, b=v_bal + self.amount)
        await i.response.send_message(f"👮 המשטרה הגיעה! {self.robber.name} נשלח לכלא לשעתיים!", ephemeral=True)

# --- 5. מערכת השודים (Views) ---
class RobAmountSelect(ui.Select):
    def __init__(self, victim):
        self.victim = victim
        options = [
            discord.SelectOption(label="100 מטבעות", description="50% הצלחה", value="100"),
            discord.SelectOption(label="200 מטבעות", description="30% הצלחה", value="200"),
            discord.SelectOption(label="300 מטבעות", description="15% הצלחה (מסוכן!)", value="300")
        ]
        super().__init__(placeholder="כמה לשדוד?", options=options)

    async def callback(self, i: discord.Interaction):
        amount = int(self.values[0])
        uid = i.user.id
        chance = 50 if amount == 100 else 30 if amount == 200 else 15
        
        rob_cooldowns[uid] = datetime.now()
        last_robbed[uid] = self.victim.id
        s_bal, _ = get_data(uid); v_bal, _ = get_data(self.victim.id)

        if random.randint(1, 100) <= chance:
            update_data(uid, b=s_bal + amount); update_data(self.victim.id, b=v_bal - amount)
            await i.response.send_message(f"🥷 לקחת {amount}. מחכים לראות אם יקראו למשטרה...", ephemeral=True)
            view = PoliceCallView(i.user, self.victim, amount)
            try: await self.victim.send(f"⚠️ {i.user.name} שדד ממך {amount}! יש לך 10 שניות לעצור אותו!", view=view)
            except: pass
        else:
            jail_list[uid] = datetime.now() # כישלון באחוזים = כלא
            update_data(uid, b=max(0, s_bal - amount))
            await i.response.send_message(f"🚓 נתפסת על ידי המשטרה! נכנסת לכלא לשעתיים.", ephemeral=True)

class VictimSelect(ui.UserSelect):
    def __init__(self): super().__init__(placeholder="בחר קורבן מהרשימה...", min_values=1, max_values=1)
    async def callback(self, i: discord.Interaction):
        victim = self.values[0]
        if victim.id == i.user.id or victim.bot: return await i.response.send_message("יעד לא חוקי", ephemeral=True)
        v = ui.View(); v.add_item(RobAmountSelect(victim))
        await i.response.send_message(f"בחרת ב-{victim.name}. מה הסכום?", view=v, ephemeral=True)

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        uid = i.user.id
        if uid in jail_list and (datetime.now() - jail_list[uid]).total_seconds() < 7200:
            return await i.response.send_message("🔒 אתה בכלא אחי!", ephemeral=True)
        if uid in rob_cooldowns and (datetime.now() - rob_cooldowns[uid]).total_seconds() < 3600:
            return await i.response.send_message("⏳ חכה שעה בין שודים.", ephemeral=True)
        s_bal, _ = get_data(uid); rob_cooldowns[uid] = datetime.now()
        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800); update_data(uid, b=s_bal+win)
            await i.response.send_message(f"💰 הבנק נפרץ! השגת {win}!", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת בבנק! איבדת 500.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        uid = i.user.id
        if uid in jail_list and (datetime.now() - jail_list[uid]).total_seconds() < 7200:
            return await i.response.send_message("🔒 אתה בכלא אחי!", ephemeral=True)
        if uid in rob_cooldowns and (datetime.now() - rob_cooldowns[uid]).total_seconds() < 3600:
            return await i.response.send_message("⏳ חכה שעה בין שודים.", ephemeral=True)
        v = ui.View(); v.add_item(VictimSelect())
        await i.response.send_message("מי הקורבן?", view=v, ephemeral=True)

# --- 6. בוט ואירועים (שומר השרת - הכל בפנים!) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = msg.author.id; now = datetime.now()
    # אנטי ספאם
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not any(r.id == OWNER_ROLE_ID for r in msg.author.roles):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    # כסף על הודעות
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

# --- 7. פקודות Slash (ניהול שומר השרת + שודים) ---

@bot.tree.command(name="setup_heist", description="[Owner] פאנל פשיעה")
async def s_h(i: discord.Interaction):
    if await is_owner(i):
        emb = discord.Embed(title="🥷 HEIST ZONE", description="סיכוי מול סיכון. כלא לשעתיים למפסידים!", color=0x2b2d31)
        emb.add_field(name="💰 סכומי שוד", value="`100` (50%) | `200` (30%) | `300` (15%)", inline=False)
        emb.set_image(url="https://images2.alphacoders.com/519/519509.jpg")
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("✅ הוקם!", ephemeral=True)

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה")
async def warn(i: discord.Interaction, m: discord.Member, r: str):
    if await is_owner(i):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} קיבל אזהרה על: {r}. (סה\"כ: {w+1})")

@bot.tree.command(name="mute", description="[Owner] השתקת משתמש")
async def mute(i: discord.Interaction, m: discord.Member):
    if await is_owner(i):
        await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"🔇 {m.mention} הושתק.")

@bot.tree.command(name="clear", description="[Owner] מחיקת הודעות")
async def clear(i: discord.Interaction, a: int):
    if await is_owner(i):
        await i.channel.purge(limit=a)
        await i.response.send_message(f"🗑️ נמחקו {a} הודעות.", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת נתונים")
async def stats(i: discord.Interaction, m: discord.Member = None):
    t = m or i.user
    b, w = get_data(t.id)
    await i.response.send_message(f"📊 **סטטיסטיקה עבור {t.name}:**\n💰 כסף: {b}\n⚠️ אזהרות: {w}")

bot.run(TOKEN)
