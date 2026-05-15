import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random
from firebase_admin import credentials, dbimport discord
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

# --- הגדרות ---
OWNER_ROLE_ID = 1499868525844627478
MY_USER_ID = 1130542850883469443

# --- פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

# --- מערכת זמן המתנה (Cooldown) גלובלית ---
rob_cooldowns = {}

def check_cooldown(uid):
    if uid in rob_cooldowns:
        diff = (datetime.now() - rob_cooldowns[uid]).total_seconds()
        if diff < 3600: # שעה אחת
            return int((3600 - diff) / 60)
    return None

# --- תפריט בחירת קורבן ---
class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר קורבן מהרשימה... 😈", min_values=1, max_values=1)

    async def callback(self, i: discord.Interaction):
        # בדיקת זמן המתנה
        time_left = check_cooldown(i.user.id)
        if time_left:
            return await i.response.send_message(f"❌ אחי, המשטרה עדיין מחפשת אותך! חזור בעוד {time_left} דקות.", ephemeral=True)

        victim = self.values[0]
        if victim.id == i.user.id:
            return await i.response.send_message("❌ לשדוד את עצמך? באמת אחי?", ephemeral=True)
        if victim.bot:
            return await i.response.send_message("❌ אי אפשר לשדוד בוטים.", ephemeral=True)

        s_bal, _ = get_data(i.user.id)
        v_bal, _ = get_data(victim.id)
        
        if v_bal < 200:
            return await i.response.send_message(f"❌ {victim.name} תפרן מדי, עזוב אותו.", ephemeral=True)

        # עדכון זמן המתנה
        rob_cooldowns[i.user.id] = datetime.now()

        if random.randint(1, 100) <= 35:
            stolen = random.randint(100, int(v_bal * 0.25))
            update_data(i.user.id, b=s_bal + stolen)
            update_data(victim.id, b=v_bal - stolen)
            emb = discord.Embed(title="🎭 שוד מוצלח!", description=f"שדדת מ-{victim.mention} סכום של **{stolen}**!", color=0x2ecc71)
            await i.response.send_message(embed=emb, ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal - 300))
            await i.response.send_message("🚓 נתפסת! שילמת קנס של 300.", ephemeral=True)

class RobUserView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(VictimSelect())

# --- פאנל ראשי ---
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        time_left = check_cooldown(i.user.id)
        if time_left:
            return await i.response.send_message(f"❌ חכה {time_left} דקות לפני השוד הבא.", ephemeral=True)

        s_bal, _ = get_data(i.user.id)
        rob_cooldowns[i.user.id] = datetime.now() # עדכון זמן המתנה

        if random.randint(1, 100) <= 20:
            win = random.randint(1500, 4500)
            update_data(i.user.id, b=s_bal + win)
            emb = discord.Embed(title="💰 בנק נשדד!", description=f"לקחת **{win}** מטבעות!", color=0xf1c40f)
            await i.response.send_message(embed=emb, ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal - 600))
            await i.response.send_message("🚨 האזעקה פעלה! איבדת 600 מטבעות.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        # שולח את בחירת המשתמש רק למי שלחץ
        await i.response.send_message("מי הקורבן שלך?", view=RobUserView(), ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 יתרה: **{bal}**", ephemeral=True)

# --- Bot ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל הפשיעה")
async def s_h(i: discord.Interaction):
    if i.user.id == MY_USER_ID or any(r.id == OWNER_ROLE_ID for r in i.user.roles):
        emb = discord.Embed(title="🥷 עולם הפשע", description="שוד בנק או משתמש? הבחירה שלך.\n(ניתן לשדוד פעם בשעה)", color=0x2b2d31)
        emb.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxJmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/LdOyjZ71FyEEM/giphy.gif")
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הפאנל הוקם בהצלחה!", ephemeral=True)

bot.run(TOKEN)
