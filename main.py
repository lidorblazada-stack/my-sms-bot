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

# --- 4. מערכת החנות ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="קנה חסינות משוד (5000)", style=discord.ButtonStyle.success, custom_id="shop_shield")
    async def buy_shield(self, i, b):
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין לך מספיק כסף אחי!", ephemeral=True)
        update_data(i.user.id, b=bal-5000)
        await i.response.send_message("🛡️ קנית חסינות! (זמני למחזור הקרוב)", ephemeral=True)

    @ui.button(label="הורדת אזהרה (10000)", style=discord.ButtonStyle.danger, custom_id="shop_warn")
    async def buy_warn_rem(self, i, b):
        bal, warns = get_data(i.user.id)
        if bal < 10000 or warns <= 0: return await i.response.send_message("או שאין לך כסף או שאין לך אזהרות!", ephemeral=True)
        update_data(i.user.id, b=bal-10000, w=warns-1)
        await i.response.send_message("✅ אזהרה אחת הוסרה מחשבונך!", ephemeral=True)

# --- 5. פאנלים קבועים (Heist, Rec, Rep) ---
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank_final")
    async def bank(self, i, b):
        bal, _ = get_data(i.user.id)
        if random.random() < 0.2:
            win = random.randint(500, 1000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הבנק נפרץ! הרווחת {win}!", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, bal-600)); await i.response.send_message("🚨 נתפסת!", ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal_final")
    async def my_bal(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💳 יתרה: **{bal}**", ephemeral=True)

class RecommendationView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח המלצה 💡", style=discord.ButtonStyle.success, custom_id="rec_final")
    async def rec_b(self, i, b):
        modal = ui.Modal(title="💡 המלצה")
        inp = ui.TextInput(label="מה ההמלצה?", style=discord.TextStyle.paragraph)
        modal.add_item(inp)
        async def callback(inter):
            ch = inter.guild.get_channel(CH_RECOMMENDATIONS)
            if ch: await ch.send(f"💡 המלצה מ{inter.user}: {inp.value}")
            await inter.response.send_message("נשלח!", ephemeral=True)
        modal.on_submit = callback
        await i.response.send_modal(modal)

# --- 6. בוט ופקודות Setup ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        self.add_view(RecommendationView())
        self.add_view(ShopView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_shop", description="הקמת החנות")
async def s_shop(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("🛒 **ברוכים הבאים לחנות השרת!**", view=ShopView())
        await i.response.send_message("החנות הוקמה!", ephemeral=True)

@bot.tree.command(name="setup_heist")
async def s_h(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("🕵️ **פאנל פשיעה**", view=HeistPanelView())
        await i.response.send_message("הוקם!", ephemeral=True)

@bot.tree.command(name="setup_recommendations")
async def s_r(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("💡 **שלחו המלצות כאן:**", view=RecommendationView())
        await i.response.send_message("הוקם!", ephemeral=True)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    b, w = get_data(msg.author.id); update_data(msg.author.id, b=b+10)
    await bot.process_commands(msg)

bot.run(TOKEN)
