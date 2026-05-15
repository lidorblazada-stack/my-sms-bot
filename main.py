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

# --- 2. הגדרת הבוט (חייב להופיע לפני הפקודות!) ---
class GuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

# --- 3. הגדרות ונתונים ---
OWNER_ROLE_ID = 1499868525844627478
MY_USER_ID = 1130542850883469443
rob_cooldowns = {}
last_robbed = {}

def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

# --- 4. מערכת השודים (Views) ---
class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר קורבן מהרשימה... 😈", min_values=1, max_values=1)

    async def callback(self, i: discord.Interaction):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600:
                return await i.response.send_message(f"❌ חכה עוד {int((3600-diff)/60)} דקות.", ephemeral=True)

        victim = self.values[0]
        if last_robbed.get(uid) == victim.id:
            return await i.response.send_message("❌ אי אפשר לשדוד אותו פעמיים ברצף!", ephemeral=True)
        if victim.id == uid or victim.bot:
            return await i.response.send_message("❌ טעות ביעד השוד.", ephemeral=True)

        s_bal, _ = get_data(uid)
        v_bal, _ = get_data(victim.id)
        if v_bal < 100:
            return await i.response.send_message("❌ אין לו מספיק כסף.", ephemeral=True)

        rob_cooldowns[uid] = datetime.now()
        last_robbed[uid] = victim.id

        if random.randint(1, 100) <= 35:
            max_steal = min(300, int(v_bal * 0.25))
            stolen = random.randint(50, max_steal)
            update_data(uid, b=s_bal + stolen)
            update_data(victim.id, b=v_bal - stolen)
            await i.response.send_message(embed=discord.Embed(title="🥷 שוד מוצלח!", description=f"לקחת מ-{victim.mention} סכום של **{stolen}**!", color=0x2ecc71), ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal - 300))
            await i.response.send_message("🚓 נתפסת! שילמת קנס של 300.", ephemeral=True)

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        uid = i.user.id
        if uid in rob_cooldowns:
            diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
            if diff < 3600: return await i.response.send_message(f"❌ חכה {int((3600-diff)/60)} דקות.", ephemeral=True)
        
        s_bal, _ = get_data(uid)
        rob_cooldowns[uid] = datetime.now()
        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800)
            update_data(uid, b=s_bal + win)
            await i.response.send_message(f"💰 הבנק נפרץ! השגת **{win}**!", ephemeral=True)
        else:
            update_data(uid, b=max(0, s_bal - 500))
            await i.response.send_message("🚨 נתפסת בבנק! איבדת 500.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        view = ui.View(); view.add_item(VictimSelect())
        await i.response.send_message("מי היעד?", view=view, ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: **{bal}**", ephemeral=True)

# --- 5. פקודות Slash ---
@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל הפשיעה")
async def s_h(i: discord.Interaction):
    if i.user.id == MY_USER_ID or any(r.id == OWNER_ROLE_ID for r in i.user.roles):
        emb = discord.Embed(title="🕵️ Heist Zone", description="ברוכים הבאים לעולם הפשע. שוד פעם בשעה, מקסימום 300 למשתמש.", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הפאנל הוקם!", ephemeral=True)

bot.run(TOKEN)
