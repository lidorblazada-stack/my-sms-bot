import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים (Railway + Firebase) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    try:
        cred = credentials.Certificate(json.loads(FB_CONFIG))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
    except: pass

# --- 2. מפת ה-IDs המדויקת של לידור ---
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

# --- 3. פאנלים עם אימבדים וכל הפונקציות ---

# פאנל שודים (Heist) - כולל 10 פונקציות פנימיות
class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.secondary, custom_id="h_bank_v3")
    async def bank(self, i, b):
        embed = discord.Embed(title="🔫 שוד בנק בתהליך...", color=0x2b2d31)
        await i.response.send_message(embed=embed, ephemeral=True)
    @ui.button(label="🔓 שחרור מהכלא", style=discord.ButtonStyle.success, custom_id="h_rel_v3")
    async def rel(self, i, b):
        await i.response.send_message("💸 ניסיון שיחוד סוהרים...", ephemeral=True)

# פאנל חנות (Shop) - כולל את כל הרולים
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Ticket Staff", style=discord.ButtonStyle.primary, custom_id="s_staff_v3")
    async def buy_s(self, i, b):
        await i.response.send_message("🛒 בודק יתרה לרול Staff (25,000)...", ephemeral=True)
    @ui.button(label="💎 VIP Role", style=discord.ButtonStyle.primary, custom_id="s_vip_v3")
    async def buy_v(self, i, b):
        await i.response.send_message("🛒 בודק יתרה לרול VIP (50,000)...", ephemeral=True)

# פאנל תמיכה (Support)
class SupportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 פידבק", style=discord.ButtonStyle.primary, custom_id="sup_fb_v3")
    async def fb(self, i, b): await i.response.send_modal(SupportModal(title="פידבק לשרת"))
    @ui.button(label="🚨 דיווח", style=discord.ButtonStyle.danger, custom_id="sup_rp_v3")
    async def rp(self, i, b): await i.response.send_modal(SupportModal(title="דיווח על שחקן"))

# פאנל ניהול אונר (Admin)
class AdminView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🧹 מחיקה 100", style=discord.ButtonStyle.danger, custom_id="adm_clr_v3")
    async def clr(self, i, b):
        if not await is_owner(i.user): return
        await i.channel.purge(limit=100)
        await i.response.send_message("✅ נוקה.", ephemeral=True)

class SupportModal(ui.Modal):
    msg = ui.TextInput(label="פרטים", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        ch_id = CHANNELS["FEEDBACK"] if "פידבק" in self.title else CHANNELS["REPORTS"]
        embed = discord.Embed(title=self.title, description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        await i.guild.get_channel(ch_id).send(embed=embed)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

# --- 4. הבוט, שומר השרת ולוגים ---
class RailiwayBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistView()); self.add_view(ShopView())
        self.add_view(SupportView()); self.add_view(AdminView())
        await self.tree.sync()

bot = RailiwayBot()

@bot.event
async def on_member_join(m):
    # וולקם באימבד
    ch = m.guild.get_channel(CHANNELS["WELCOME"])
    if ch:
        e = discord.Embed(title="Welcome!", description=f"ברוך הבא {m.mention}!", color=0x00ff00)
        e.set_thumbnail(url=m.display_avatar.url)
        await ch.send(embed=e)
    # אנטי-אלט
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        ach = m.guild.get_channel(CHANNELS["ANTI_ALT"])
        if ach: await ach.send(embed=discord.Embed(title="🚨 חשוד באלט", description=f"{m.mention} נרשם לפני פחות מ-7 ימים!", color=0xff0000))

# לוג ניסיונות פריצה ופעולות אונר
@bot.event
async def on_app_command_completion(i, cmd):
    if await is_owner(i.user):
        log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
        if log_ch:
            await log_ch.send(embed=discord.Embed(title="🛠️ לוג ניהול", description=f"האונר {i.user.mention} הריץ: `/{cmd.name}`", color=0x00ff00))

# --- 5. פקודות סטאפ מופרדות (אונר בלבד) ---

@bot.tree.command(name="setup_heist", description="הקמת פאנל שודים")
async def s_h(i):
    if not await is_owner(i.user): return
    await i.channel.send(embed=discord.Embed(title="🔫 פאנל שודים", color=0x000000), view=HeistView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_shop", description="הקמת פאנל חנות")
async def s_s(i):
    if not await is_owner(i.user): return
    await i.channel.send(embed=discord.Embed(title="🛒 חנות רולים", color=0x5865f2), view=ShopView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_support", description="הקמת פאנל תמיכה")
async def s_sup(i):
    if not await is_owner(i.user): return
    await i.channel.send(embed=discord.Embed(title="📩 תמיכה ודיווחים", color=0x00fbff), view=SupportView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_admin", description="הקמת פאנל ניהול")
async def s_adm(i):
    if not await is_owner(i.user): return
    await i.channel.send(embed=discord.Embed(title="🛠️ ניהול אונר", color=0xff0000), view=AdminView())
    await i.response.send_message("הוקם.", ephemeral=True)

if TOKEN: bot.run(TOKEN)
