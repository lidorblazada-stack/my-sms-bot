import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random
from firebase_admin import credentials, db

# --- חיבור Firebase (נשאר בדיוק אותו דבר) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- הגדרות (רולים וערוצים של שומר השרת) ---
OWNER_ROLE_ID = 1499868525844627478
MY_USER_ID = 1130542850883469443

# --- מערכת זיכרון לשודים ---
rob_cooldowns = {} # זמן המתנה
last_robbed = {}   # מונע שוד של אותו משתמש פעמיים ברצף

# --- פונקציות נתונים (מתחבר לכסף של החנות) ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

# --- תפריט בחירת קורבן ---
class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר קורבן... 😈", min_values=1, max_values=1)

    async def callback(self, i: discord.Interaction):
        # 1. בדיקת Cooldown (פעם בשעה)
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600:
                return await i.response.send_message(f"❌ אחי, חכה עוד {int((3600-diff)/60)} דקות.", ephemeral=True)

        victim = self.values[0]
        
        # 2. בדיקת שוד חוזר של אותו משתמש
        if last_robbed.get(uid) == victim.id:
            return await i.response.send_message("❌ אחי, כבר שדדת אותו הרגע, תן לו לנשום... בחר מישהו אחר.", ephemeral=True)

        if victim.id == uid or victim.bot:
            return await i.response.send_message("❌ אי אפשר לשדוד את עצמך או בוטים.", ephemeral=True)

        s_bal, _ = get_data(uid)
        v_bal, _ = get_data(victim.id)
        
        if v_bal < 100:
            return await i.response.send_message("❌ אין לו מספיק כסף בשביל שזה ישתלם.", ephemeral=True)

        # עדכון נתונים
        rob_cooldowns[uid] = datetime.now()
        last_robbed[uid] = victim.id

        if random.randint(1, 100) <= 35:
            # 3. הגבלת שוד לעד 300 מטבעות
            max_steal = min(300, int(v_bal * 0.25))
            stolen = random.randint(50, max_steal)
            
            update_data(uid, b=s_bal + stolen)
            update_data(victim.id, b=v_bal - stolen)
            
            emb = discord.Embed(title="🥷 שוד מוצלח!", description=f"לקחת מ-{victim.mention} סכום של **{stolen}** מטבעות!", color=0x2ecc71)
            await i.response.send_message(embed=emb, ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal - 300))
            await i.response.send_message("🚓 נתפסת! שילמת קנס של 300 מטבעות.", ephemeral=True)

class RobUserView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(VictimSelect())

# --- פאנל שודים ראשי ---
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600:
                return await i.response.send_message(f"❌ חכה עוד {int((3600-diff)/60)} דקות.", ephemeral=True)

        s_bal, _ = get_data(uid)
        rob_cooldowns[uid] = datetime.now()

        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800) # בבנק אפשר קצת יותר אבל עדיין מוגבל
            update_data(uid, b=s_bal + win)
            await i.response.send_message(f"💰 פריצה הצליחה! השגת **{win}** מטבעות!", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal - 500))
            await i.response.send_message("🚨 האזעקה הופעלה! איבדת 500 מטבעות.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        await i.response.send_message("בחר את הקורבן שלך:", view=RobUserView(), ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה בחשבון (מחובר לחנות): **{bal}**", ephemeral=True)

# --- פקודת הקמה ---
@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל הפשיעה")
async def s_h(i: discord.Interaction):
    if i.user.id == MY_USER_ID or any(r.id == OWNER_ROLE_ID for r in i.user.roles):
        emb = discord.Embed(title="🕵️ מחלקת השודים", description="כאן הכסף של החנות עומד למבחן...\n\n- שוד משתמש: מוגבל לעד 300.\n- המתנה: שעה אחת בין ניסיונות.\n- חוק: אי אפשר לשדוד את אותו אדם פעמיים ברצף.", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הפאנל עלה אחי!", ephemeral=True)

bot.run(TOKEN)
