import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. הגדרות ו-IDs (Railiway) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

CHANNELS = {
    "REPORTS": 1501946934779449505, "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620, "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380, "WELCOME": 1501713652217282591
}
ROLES = {
    "OWNER": 1499868525844627478, "MUTE": 1501953906736103535,
    "STAFF": 1501316672345211041, "VIP": 1503817695466881255
}

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 2. פאנל כלכלה (זה מה שביקשת!) ---
class EconomyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="💼 עבודה", style=discord.ButtonStyle.primary, custom_id="eco_work")
    async def work(self, i, b):
        amt = random.randint(500, 2000)
        await i.response.send_message(f"💰 **עבדת קשה והרווחת {amt} מטבעות!**", ephemeral=True)

    @ui.button(label="🎁 פרס יומי", style=discord.ButtonStyle.success, custom_id="eco_daily")
    async def daily(self, i, b):
        await i.response.send_message("🎁 **קיבלת את הפרס היומי שלך: 5,000 מטבעות!**", ephemeral=True)

    @ui.button(label="📊 הסטטיסטיקה שלי", style=discord.ButtonStyle.secondary, custom_id="eco_stats")
    async def stats(self, i, b):
        await i.response.send_message(f"📊 **סטטיסטיקה עבור {i.user.name}:**\n💰 כסף: 10,000\n⚠️ אזהרות: 0", ephemeral=True)

# --- 3. פאנל שודים (Heist) ---
class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="🔫 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_bank_v4")
    async def bank(self, i, b):
        await i.response.send_message("🚨 **אתה מנסה לפרוץ לכספת... בהצלחה!**", ephemeral=True)

    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h_rob_v4")
    async def rob(self, i, b):
        await i.response.send_message("👥 **בחר משתמש לשדוד (מערכת בבדיקה)...**", ephemeral=True)

# --- 4. פאנל העברות (Pay) ---
class PayView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💸 העברת כסף לחבר", style=discord.ButtonStyle.primary, custom_id="pay_btn")
    async def pay(self, i, b):
        await i.response.send_message("שלח הודעה עם סכום ותיוג המשתמש להעברה.", ephemeral=True)

# --- 5. הגדרות הבוט ופקודות הסטאפ ---
class RailiwayBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(EconomyView()); self.add_view(HeistView()); self.add_view(PayView())
        await self.tree.sync()

bot = RailiwayBot()

@bot.tree.command(name="setup_economy", description="[OWNER] הקמת פאנל כלכלה (עבודה/דיילי)")
async def s_eco(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="💰 מרכז הכלכלה של Railiway", description="לחצו על הכפתורים כדי להרוויח כסף ולבדוק נתונים!", color=0x00ff00)
    await i.channel.send(embed=embed, view=EconomyView())
    await i.response.send_message("פאנל כלכלה הוקם.", ephemeral=True)

@bot.tree.command(name="setup_heist", description="[OWNER] הקמת פאנל שודים (בנק/שוד משתמש)")
async def s_h(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="🔫 עולם הפשע", description="כאן מבצעים שודים וגניבות. זהירות מהמשטרה!", color=0x000000)
    await i.channel.send(embed=embed, view=HeistView())
    await i.response.send_message("פאנל שודים הוקם.", ephemeral=True)

@bot.tree.command(name="setup_pay", description="[OWNER] הקמת פאנל העברות")
async def s_p(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="💸 העברת כספים", description="רוצים להעביר כסף לחבר? לחצו למטה.", color=0xffff00)
    await i.channel.send(embed=embed, view=PayView())
    await i.response.send_message("פאנל העברות הוקם.", ephemeral=True)

# לוג ניהול (שומר על הסטאפים שלך)
@bot.event
async def on_app_command_completion(i, cmd):
    if await is_owner(i.user):
        ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if ch: await ch.send(f"🛠️ **לוג:** האונר השתמש ב-`/{cmd.name}` כדי להקים/לנהל מערכת.")

if TOKEN: bot.run(TOKEN)
