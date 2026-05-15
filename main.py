import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs של לידור ---
CHANNELS = {
    "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591
}

ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255,
    "SUPPORTER": 1503819239310627068
}

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 3. פאנלים עם אימבדים מושקעים ---

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.secondary, custom_id="h_bank_final")
    async def bank(self, i, b):
        embed = discord.Embed(title="🔫 ניסיון שוד בנק", description="אתה מנסה לפרוץ לכספת הראשית...", color=0x2f3136)
        await i.response.send_message(embed=embed, ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Ticket Staff", style=discord.ButtonStyle.primary, custom_id="s_staff_final")
    async def buy_s(self, i, b):
        embed = discord.Embed(title="🛒 רכישת רול", description="מעבד בקשה לרכישת **Staff Role**...", color=0x5865f2)
        await i.response.send_message(embed=embed, ephemeral=True)

class SupportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.success, custom_id="sup_fb_final")
    async def fb(self, i, b): await i.response.send_modal(SupportModal(title="שליחת פידבק לשרת"))
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="sup_rp_final")
    async def rp(self, i, b): await i.response.send_modal(SupportModal(title="דיווח על שחקן חשוד"))

class AdminView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🧹 Clear 100 Messages", style=discord.ButtonStyle.danger, custom_id="adm_clr_final")
    async def clr(self, i, b):
        if not await is_owner(i.user): return
        await i.channel.purge(limit=100)
        embed = discord.Embed(description="✅ **הערוץ נוקה בהצלחה (100 הודעות)**", color=0x43b581)
        await i.response.send_message(embed=embed, ephemeral=True)

class SupportModal(ui.Modal):
    msg = ui.TextInput(label="תוכן ההודעה", style=discord.TextStyle.paragraph, placeholder="רשום כאן את כל הפרטים...")
    async def on_submit(self, i):
        ch_id = CHANNELS["FEEDBACK"] if "פידבק" in self.title else CHANNELS["REPORTS"]
        embed = discord.Embed(title=f"📥 {self.title}", description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        embed.set_footer(text=f"ID: {i.user.id}")
        await i.guild.get_channel(ch_id).send(embed=embed)
        await i.response.send_message("✅ ההודעה נשלחה והתקבלה אצל הצוות!", ephemeral=True)

# --- 4. הגדרת הבוט ושומר השרת ---
class RailiwayBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistView()); self.add_view(ShopView())
        self.add_view(SupportView()); self.add_view(AdminView())
        await self.tree.sync()

bot = RailiwayBot()

@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(CHANNELS["WELCOME"])
    if ch:
        embed = discord.Embed(title="Welcome to Railiway!", description=f"ברוך הבא {m.mention}! שמחים שהצטרפת.", color=0x00ff00)
        embed.set_thumbnail(url=m.display_avatar.url)
        await ch.send(embed=embed)
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach:
            embed = discord.Embed(title="🚨 התראת שומר השרת", description=f"המשתמש {m.mention} נראה כחשבון אלט (נוצר לפני פחות משבוע).", color=0xff0000)
            await ach.send(embed=embed)

# --- 5. פקודות סטאפ מעוצבות ---

@bot.tree.command(name="setup_heist", description="[OWNER] הקמת פאנל שודים")
async def s_h(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="🔫 מערכת השודים", description="לחץ על הכפתורים למטה כדי להתחיל שוד או להשתחרר מהכלא.", color=0x2b2d31)
    await i.channel.send(embed=embed, view=HeistView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת פאנל חנות")
async def s_s(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="🛒 חנות הרולים", description="כאן תוכלו לקנות רולים יוקרתיים בכסף שהרווחתם!", color=0x5865f2)
    embed.add_field(name="🎫 Ticket Staff", value="Price: 25,000", inline=True)
    embed.add_field(name="💎 VIP Role", value="Price: 50,000", inline=True)
    await i.channel.send(embed=embed, view=ShopView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_support", description="[OWNER] הקמת פאנל תמיכה")
async def s_sup(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="📩 מרכז העזרה והדיווחים", description="צריך עזרה? רוצה לדווח על מישהו? לחץ על הכפתור המתאים.", color=0x00fbff)
    await i.channel.send(embed=embed, view=SupportView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_admin", description="[OWNER] הקמת פאנל ניהול")
async def s_adm(i):
    if not await is_owner(i.user): return
    embed = discord.Embed(title="🛠️ פאנל ניהול אונר", description="כאן מנהלים את השרת ביעילות.", color=0xff0000)
    await i.channel.send(embed=embed, view=AdminView())
    await i.response.send_message("הוקם.", ephemeral=True)

if TOKEN: bot.run(TOKEN)
