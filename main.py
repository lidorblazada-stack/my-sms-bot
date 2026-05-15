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

# --- 2. הגדרות IDs ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
MEMBER_ROLE_ID = 1501983948111352091
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
    await i.response.send_message("❌ גישה לאונר בלבד!", ephemeral=True)
    return False

# --- 4. מערכת "קרא למשטרה" (Counter-Rob) ---
class PoliceCallView(ui.View):
    def __init__(self, robber, victim, amount):
        super().__init__(timeout=10)
        self.robber = robber
        self.victim = victim
        self.amount = amount
        self.caught = False

    @ui.button(label="🚨 קרא למשטרה! (10 שניות)", style=discord.ButtonStyle.danger)
    async def call_police(self, i: discord.Interaction, b: ui.Button):
        self.caught = True
        self.stop()
        
        # החזרת הכסף וקנס לשודד
        r_bal, _ = get_data(self.robber.id)
        v_bal, _ = get_data(self.victim.id)
        update_data(self.robber.id, b=max(0, r_bal - (self.amount + 200))) # קנס נוסף
        update_data(self.victim.id, b=v_bal + self.amount)
        
        await i.response.send_message(f"👮 המשטרה הגיעה! תפסת את {self.robber.name} והכסף הוחזר בתוספת פיצוי!", ephemeral=True)
        try: await self.robber.send(f"🚨 נתפסת! {self.victim.name} קרא למשטרה. איבדת את השלל וקיבלת קנס!")
        except: pass

# --- 5. מערכת השודים ---
class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר קורבן מהרשימה... 😈", min_values=1, max_values=1)

    async def callback(self, i: discord.Interaction):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600: return await i.response.send_message(f"❌ חכה {int((3600-diff)/60)} דקות.", ephemeral=True)
        
        victim = self.values[0]
        if last_robbed.get(uid) == victim.id: return await i.response.send_message("❌ לא פעמיים ברצף!", ephemeral=True)
        if victim.id == uid or victim.bot: return await i.response.send_message("❌ יעד לא חוקי.", ephemeral=True)
        
        s_bal, _ = get_data(uid); v_bal, _ = get_data(victim.id)
        if v_bal < 100: return await i.response.send_message("❌ אין לו מספיק כסף.", ephemeral=True)

        rob_cooldowns[uid] = datetime.now(); last_robbed[uid] = victim.id

        if random.randint(1, 100) <= 35:
            stolen = random.randint(50, min(300, int(v_bal * 0.25)))
            update_data(uid, b=s_bal + stolen); update_data(victim.id, b=v_bal - stolen)
            
            await i.response.send_message(f"🥷 השוד הצליח! לקחת {stolen} מטבעות. לקורבן יש 10 שניות לקרוא למשטרה...", ephemeral=True)
            
            # שליחת הודעה לקורבן
            view = PoliceCallView(i.user, victim, stolen)
            try:
                msg = await victim.send(f"⚠️ **שוד בתהליך!** {i.user.name} שדד ממך {stolen} מטבעות! יש לך 10 שניות לעצור אותו!", view=view)
                await asyncio.sleep(10)
                if not view.caught:
                    await msg.edit(content="Too late... השודד נמלט עם הכסף. 🏃‍♂️💨", view=None)
            except: pass
        else:
            update_data(uid, b=max(0, s_bal - 300))
            await i.response.send_message("🚓 נתפסת על חם! שילמת קנס של 300.", ephemeral=True)

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
            update_data(uid, b=s_bal+win); await i.response.send_message(f"💰 פריצה הצליחה! השגת **{win}**!", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת בבנק!", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        v = ui.View(); v.add_item(VictimSelect())
        await i.response.send_message("בחר קורבן:", view=v, ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id); await i.response.send_message(f"💰 יתרה: **{bal}**", ephemeral=True)

# --- 6. בוט ואירועים ---
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
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not any(r.id == OWNER_ROLE_ID for r in msg.author.roles):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

# --- 7. פקודות Slash ---
@bot.tree.command(name="setup_heist", description="[Owner] פאנל פשיעה מעוצב")
async def s_h(i: discord.Interaction):
    if await is_owner(i):
        emb = discord.Embed(title="🥷 HEIST ZONE | עולם הפשע", description="כאן עושים כסף מלוכלך. ככל שהפרס גדול, הסיכון עולה.", color=0x2b2d31)
        emb.add_field(name="🏦 שוד בנק (20% הצלחה)", value="
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1

### מה שדרגנו פה אחי:
1.  **מערכת מרדף (Police Call):** ברגע ששוד משתמש מצליח, הבוט שולח הודעה לקורבן בפרטי. יש לו כפתור אדום ל-10 שניות. אם הוא לוחץ – השודד מקבל קנס והכסף חוזר.
2.  **אחוזי הצלחה רשומים:** הכל מופיע באימבד בצורה ברורה (20% לבנק, 35% למשתמש).
3.  **הודעות פרטיות:** הבוט מעדכן את השודד אם הקורבן הצליח לתפוס אותו.
4.  **קוד מלא:** הכל בפנים, כולל האנטי-ספאם והכלכלה של "שומר השרת".

תעלה את זה ל-Railway ויהיה לך שרת ברמה של RP מקצועי! 🚀👮‍♂️🥷
