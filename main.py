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
CH_RECOMMENDATIONS = 1501947249658429470 
CH_REPORTS = 1501946934779449505         
CH_HEIST_LOGS = 1504815433004617798
MY_USER_ID = 1130542850883469443

user_messages = {}
rob_cooldowns = {}
jail_list = {} 

# --- 3. פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner_check(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == MY_USER_ID

# --- 4. מודאלים ---
class RecommendationModal(ui.Modal, title="המלצה חדשה לשרת"):
    rec_input = ui.TextInput(label="מה ההמלצה שלך?", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_RECOMMENDATIONS)
        emb = discord.Embed(title="💡 המלצה חדשה", description=self.rec_input.value, color=discord.Color.green())
        emb.set_footer(text=f"מאת: {i.user}", icon_url=i.user.display_avatar.url)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("ההמלצה נשלחה אחי!", ephemeral=True)

class ReportModal(ui.Modal, title="דיווח חדש"):
    target = ui.TextInput(label="על מי/מה הדיווח?", required=True)
    reason = ui.TextInput(label="פירוט הדיווח", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_REPORTS)
        emb = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red())
        emb.add_field(name="נושא", value=self.target.value)
        emb.add_field(name="פירוט", value=self.reason.value)
        emb.set_footer(text=f"דווח ע\"י {i.user}")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("הדיווח התקבל.", ephemeral=True)

# --- 5. פאנלים קבועים (Persistent Views) ---
class RecommendationView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח המלצה 💡", style=discord.ButtonStyle.success, custom_id="btn_rec_main")
    async def rec_btn(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_modal(RecommendationModal())

class ReportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="דווח כאן 🚨", style=discord.ButtonStyle.danger, custom_id="btn_rep_main")
    async def rep_btn(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_modal(ReportModal())

class PoliceCallView(ui.View):
    def __init__(self, robber, victim, amount):
        super().__init__(timeout=10)
        self.robber, self.victim, self.amount = robber, victim, amount
    @ui.button(label="🚨 קרא למשטרה!", style=discord.ButtonStyle.danger)
    async def call_police(self, i, b):
        jail_list[self.robber.id] = [datetime.now(), self.amount * 10]
        update_data(self.victim.id, b=get_data(self.victim.id)[0] + self.amount)
        await i.response.send_message("👮 תפסת את השודד!", ephemeral=True)

# --- 6. פאנל שודים ---
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        s_bal, _ = get_data(i.user.id)
        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800)
            update_data(i.user.id, b=s_bal+win); await i.response.send_message(f"💰 הצלחת! קיבלת {win}.", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת בבנק!", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        v = ui.View(); v.add_item(VictimSelectView())
        await i.response.send_message("בחר קורבן:", view=v, ephemeral=True)

class VictimSelectView(ui.UserSelect):
    def __init__(self): super().__init__(placeholder="בחר קורבן...", min_values=1, max_values=1)
    async def callback(self, i: discord.Interaction):
        victim = self.values[0]
        if await is_owner_check(victim): return await i.response.send_message("❌ אונר חסין!", ephemeral=True)
        # כאן אפשר להוסיף את בחירת הסכום כפי שעשינו קודם
        await i.response.send_message(f"בחרת ב-{victim.name}. (מערכת בחירת סכום תופעל)", ephemeral=True)

# --- 7. הבוט הראשי ---
class GuardBot(commands.Bot):
    def __init__(self): 
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        # טעינת פאנלים קבועים כדי שלא יקרסו אחרי ריסטארט
        self.add_view(HeistPanelView())
        self.add_view(RecommendationView())
        self.add_view(ReportView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_recommendations")
async def s_rec(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("💡 **יש לכם רעיון לשיפור השרת? נשמח לשמוע!**", view=RecommendationView())
        await i.response.send_message("הפאנל הוקם.", ephemeral=True)

@bot.tree.command(name="setup_reports")
async def s_rep(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("🚨 **דיווחים על משתמשים או תקלות בשרת:**", view=ReportView())
        await i.response.send_message("הפאנל הוקם.", ephemeral=True)

@bot.tree.command(name="setup_heist")
async def s_h(i: discord.Interaction):
    if await is_owner_check(i.user):
        emb = discord.Embed(title="🥷 HEIST ZONE", description="עולם הפשע של השרת", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הוקם.", ephemeral=True)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+10)
    await bot.process_commands(msg)

bot.run(TOKEN)
