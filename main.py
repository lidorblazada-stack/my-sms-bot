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

# --- הגדרות בסיס (IDs שלך) ---
CH_OWNER_LOGS = 1503496964732354620      
OWNER_ROLE_ID = 1499868525844627478
MEMBER_ROLE_ID = 1501983948111352091
MUTE_ROLE_ID = 1501953906736103535
MY_USER_ID = 1130542850883469443

# --- פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

# --- מערכת בחירת קורבן לשוד ---
class VictimSelect(ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="בחר את המשתמש שברצונך לשדוד... 😈", min_values=1, max_values=1)

    async def callback(self, i: discord.Interaction):
        victim = self.values[0]
        if victim.id == i.user.id:
            return await i.response.send_message("אחי, אתה לא יכול לשדוד את עצמך... תהיה רציני.", ephemeral=True)
        if victim.bot:
            return await i.response.send_message("אתה מנסה לשדוד בוט? אין להם רגשות (או כסף).", ephemeral=True)

        s_bal, _ = get_data(i.user.id)
        v_bal, _ = get_data(victim.id)
        
        if v_bal < 200:
            return await i.response.send_message(f"עזוב את {victim.name}, הוא תפרן... אין לו מה לקחת.", ephemeral=True)

        # 35% סיכוי הצלחה
        if random.randint(1, 100) <= 35:
            stolen = random.randint(100, int(v_bal * 0.25))
            update_data(i.user.id, b=s_bal + stolen)
            update_data(victim.id, b=v_bal - stolen)
            
            emb = discord.Embed(title="🎭 שוד מוצלח!", 
                                description=f"הפתעת את {victim.mention} בסימטה חשוכה ולקחת לו **{stolen}** מטבעות!", 
                                color=0x2ecc71)
            await i.response.send_message(embed=emb)
        else:
            penalty = 300
            update_data(i.user.id, b=max(0, s_bal - penalty))
            emb = discord.Embed(title="🚓 המשטרה בדרך!", 
                                description=f"ניסית לשדוד את {victim.name} אבל הוא הזעיק עזרה!\nשילמת קנס של **{penalty}** מטבעות.", 
                                color=0xe74c3c)
            await i.response.send_message(embed=emb)

class RobUserView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(VictimSelect())

# --- פאנל ראשי ---
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        s_bal, _ = get_data(i.user.id)
        if random.randint(1, 100) <= 20:
            win = random.randint(1500, 4500)
            update_data(i.user.id, b=s_bal + win)
            emb = discord.Embed(title="💰 פריצת המאה!", description=f"הכספת נפתחה! ברחת עם **{win}** מטבעות!", color=0xf1c40f)
            await i.response.send_message(embed=emb, ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal - 600))
            await i.response.send_message("🚨 נכשלת! השומרים תפסו אותך. איבדת 600 מטבעות.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        await i.response.send_message("בחר מישהו מהרשימה למטה:", view=RobUserView(), ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal")
    async def h_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💰 היתרה שלך: **{bal}** מטבעות.", ephemeral=True)

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
        emb = discord.Embed(title="🥷 עולם הפשע של השרת", 
                            description="ברוך הבא לצד האפל... בחר את הפעולה שלך:\n\n"
                                        "🏦 **שוד בנק:** סיכון ענק, פרס מטורף (20% הצלחה).\n"
                                        "🥷 **שוד משתמש:** בחר מישהו מהשרת וקח לו כסף (35% הצלחה).\n"
                                        "💳 **יתרה:** בדוק כמה כסף נשאר לך בכיס.", 
                            color=0x2b2d31)
        emb.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxN2I1MmIxJmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/LdOyjZ71FyEEM/giphy.gif")
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הפאנל הוקם!", ephemeral=True)

bot.run(TOKEN)
