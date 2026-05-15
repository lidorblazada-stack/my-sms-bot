import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime
import os, json, firebase_admin, random
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

# --- 4. מודאלים (חלונות קופצים) ---
class RecommendationModal(ui.Modal, title="💡 המלצה חדשה לשרת"):
    rec = ui.TextInput(label="מה ההמלצה שלך?", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_RECOMMENDATIONS)
        if ch: await ch.send(embed=discord.Embed(title="💡 המלצה חדשה", description=self.rec.value, color=0x00ff00).set_footer(text=f"מאת: {i.user}"))
        await i.response.send_message("ההמלצה נשלחה בהצלחה!", ephemeral=True)

class ReportModal(ui.Modal, title="🚨 דיווח חדש"):
    target = ui.TextInput(label="על מי/מה הדיווח?", required=True)
    reason = ui.TextInput(label="פירוט הדיווח", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_REPORTS)
        if ch: await ch.send(embed=discord.Embed(title="🚨 דיווח חדש", description=f"**יעד:** {self.target.value}\n**פירוט:** {self.reason.value}", color=0xff0000).set_footer(text=f"מאת: {i.user}"))
        await i.response.send_message("הדיווח התקבל ויועבר לטיפול.", ephemeral=True)

# --- 5. פאנלים קבועים (Persistent Views) ---
class RecommendationView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח המלצה 💡", style=discord.ButtonStyle.success, custom_id="btn_rec_kill")
    async def rec_b(self, i, b): await i.response.send_modal(RecommendationModal())

class ReportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="דווח כאן 🚨", style=discord.ButtonStyle.danger, custom_id="btn_rep_kill")
    async def rep_b(self, i, b): await i.response.send_modal(ReportModal())

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank_kill")
    async def bank(self, i, b):
        bal, _ = get_data(i.user.id)
        if random.random() < 0.2:
            win = random.randint(300, 800); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 שוד הבנק הצליח! הרווחת {win} מטבעות!", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, bal-500)); await i.response.send_message("🚨 האזעקה הופעלה! נתפסת ונקנסת ב-500 מטבעות.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user_kill")
    async def user_rob(self, i, b):
        await i.response.send_message("כדי לשדוד משתמש, השתמש בפקודת הסלאש הייעודית (בקרוב בממשק הכפתורים).", ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal_kill")
    async def my_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💳 היתרה הנוכחית שלך: **{bal}** מטבעות.", ephemeral=True)

# --- 6. בוט ופקודות Setup ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        self.add_view(RecommendationView())
        self.add_view(ReportView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_heist")
async def s_h(i: discord.Interaction):
    if await is_owner_check(i.user):
        emb = discord.Embed(title="🕵️ Heist Zone", description="ברוכים הבאים לעולם הפשע. שוד פעם בשעה, מקסימום 300 למשתמש.", color=0x2b2d31)
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("פאנל שודים הוקם!", ephemeral=True)

@bot.tree.command(name="setup_recommendations")
async def s_rec(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("💡 **יש לכם המלצה לשיפור השרת? נשמח לשמוע!**", view=RecommendationView())
        await i.response.send_message("פאנל המלצות הוקם!", ephemeral=True)

@bot.tree.command(name="setup_reports")
async def s_rep(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("🚨 **דיווחים על תקלות או משתמשים בעייתיים:**", view=ReportView())
        await i.response.send_message("פאנל דיווחים הוקם!", ephemeral=True)

bot.run(TOKEN)
