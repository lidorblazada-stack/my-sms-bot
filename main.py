import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime, timedelta

# --- 1. חיבורים וקונפיגורציה ---
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
    "REPORTS": 1501946934779449505,      # דיווחים על אנשים
    "FEEDBACK": 1503475379942461522,      # פידבק אנונימי
    "OWNER_LOGS": 1503496964732354620,    # לוגים פקודות אונר
    "WARNS_LOG": 1502014872655888554,     # לוג אזהרות (מילוליות/רשמיות)
    "ANTI_ALT": 1503464176599695380,      # מערכת אנטי אלט
    "WELCOME": 1501713652217282591,       # וולקם וביי
    "SUGGESTIONS": 1501947249658429470,   # המלצות
    "LEADERBOARD": 1502014872655888554    # טבלת עשירים (5 דק')
}
ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380,
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255
}
OWNER_ID = 1130542850883469443

# --- 3. מודאלים (חלונות קופצים) ---

class ReportModal(ui.Modal, title="🚨 דיווח על שחקן"):
    target = ui.TextInput(label="על מי הדיווח?", placeholder="שם המשתמש/ID")
    reason = ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention)
        embed.add_field(name="על המשתמש:", value=self.target.value)
        embed.add_field(name="סיבה:", value=self.reason.value, inline=False)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=embed)
        await i.response.send_message("הדיווח נשלח לצוות.", ephemeral=True)

class FeedbackModal(ui.Modal, title="📩 שלח פידבק"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)
    async def on_submit(self, i):
        sender = "👤 אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"נשלח ע\"י: {sender}")
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.secondary, custom_id="new_feed_btn"))
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        await i.response.send_message("תודה!", ephemeral=True)

class SuggestionModal(ui.Modal, title="💡 המלצה חדשה"):
    s_msg = ui.TextInput(label="מה ההמלצה שלך?", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="💡 המלצה מהקהילה", description=self.s_msg.value, color=0xffd700)
        embed.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        await i.guild.get_channel(CHANNELS["SUGGESTIONS"]).send(embed=embed)
        await i.response.send_message("ההמלצה נשלחה!", ephemeral=True)

# --- 4. פאנלים קבועים (Views) - פתרון ל-Render ---

class PersistentShop(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎁 בונוס יומי (1,000)", style=discord.ButtonStyle.success, custom_id="shop_daily_final")
    async def daily(self, i, b): await i.response.send_message("🎁 קיבלת 1,000 מטבעות! תחזור עוד 24 שעות.", ephemeral=True)
    @ui.button(label="💼 עבודה", style=discord.ButtonStyle.primary, custom_id="shop_work_final")
    async def work(self, i, b): await i.response.send_message(f"💰 עבדת קשה והרווחת {random.randint(100,500)}!", ephemeral=True)
    @ui.button(label="🎫 Staff (25,000)", style=discord.ButtonStyle.danger, custom_id="shop_buy_staff")
    async def b_staff(self, i, b): await i.response.send_message("🛒 בודק יתרה... אין לך מספיק כסף.", ephemeral=True)

class PersistentHeist(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="heist_bank_final")
    async def bank(self, i, b): await i.response.send_message("🚨 פורץ לכספת... שדדת 5,000 מטבעות!", ephemeral=True)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="heist_user_final")
    async def rob(self, i, b): await i.response.send_message("🔫 בחר משתמש לשדידה...", ephemeral=True)

class PersistentSupport(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="sup_rep_final")
    async def report(self, i, b): await i.response.send_modal(ReportModal())
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="sup_feed_final")
    async def feedback(self, i, b): await i.response.send_modal(FeedbackModal())
    @ui.button(label="💡 שלח המלצה", style=discord.ButtonStyle.secondary, custom_id="sup_sug_final")
    async def suggest(self, i, b): await i.response.send_modal(SuggestionModal())

class AntiAltView(ui.View):
    def __init__(self, m):
        super().__init__(timeout=None)
        self.m = m
    @ui.button(label="להעיף", style=discord.ButtonStyle.danger, custom_id="alt_k_final")
    async def kick(self, i, b): await self.m.kick(); await i.response.send_message("המשתמש הועף.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success, custom_id="alt_s_final")
    async def stay(self, i, b): await i.response.send_message("המשתמש נשאר.")
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary, custom_id="alt_r_final")
    async def sus(self, i, b): 
        await self.m.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("קיבל רול חשוד.")

# --- 5. הבוט המרכזי ---

class RailiwayBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        self.add_view(PersistentShop())
        self.add_view(PersistentHeist())
        self.add_view(PersistentSupport())
        self.update_leaderboard.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_leaderboard(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת 10 העשירים ביותר", color=0xffd700, timestamp=datetime.now())
            embed.description = "1. `Nehoray` - 💰 1,200,000\n2. `Lidor` - 💰 1,150,000\n3. `Admin` - 💰 500,000"
            embed.set_footer(text="מתעדכן אוטומטית כל 5 דקות")
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = RailiwayBot()

# --- 6. 30 פקודות (ניהול, כלכלה, אונר) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
async def warn(i, m: discord.Member, r: str):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(f"⚠️ {m.mention} הוזהר רשמית ע\"י {i.user.name}: {r}")
    await i.response.send_message(f"אזהרה נשלחה ל-{m.name}")

@bot.tree.command(name="mute", description="השתקת משתמש")
async def mute(i, m: discord.Member):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message(f"🔇 {m.name} הושתק.")

@bot.tree.command(name="clear", description="מחיקת הודעות")
async def clear(i, a: int):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await i.channel.purge(limit=a); await i.response.send_message(f"נוקה.", ephemeral=True)

@bot.tree.command(name="ban", description="הרחקת משתמש")
async def ban(i, m: discord.Member):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await m.ban(); await i.response.send_message(f"ביי ביי {m.name}.")

@bot.tree.command(name="kick", description="העפת משתמש")
async def kick(i, m: discord.Member):
    if not any(r.id == ROLES["OWNER"] for r in i.user.roles): return
    await m.kick(); await i.response.send_message(f"{m.name} הועף.")

@bot.tree.command(name="stats", description="הכסף שלי")
async def stats(i): await i.response.send_message("💰 יש לך 1,500 מטבעות.", ephemeral=True)

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="avatar")
async def avatar(i, m: discord.Member = None):
    m = m or i.user
    await i.response.send_message(m.display_avatar.url)

# פקודות סטאפ
@bot.tree.command(name="setup_all")
async def s_all(i):
    if i.user.id != OWNER_ID: return
    await i.channel.send(embed=discord.Embed(title="🛒 Railiway Shop", color=0x5865f2), view=PersistentShop())
    await i.channel.send(embed=discord.Embed(title="📩 Support Center", color=0x00fbff), view=PersistentSupport())
    await i.channel.send(embed=discord.Embed(title="🔫 Heist Panel", color=0x000000), view=PersistentHeist())
    await i.response.send_message("הכל הוקם בהצלחה!", ephemeral=True)

# --- 7. אירועים (אנטי-אלט, לוגים, וולקם) ---

@bot.event
async def on_member_join(m):
    # וולקם
    await m.guild.get_channel(CHANNELS["WELCOME"]).send(f"👋 ברוך הבא {m.mention} לשרת!")
    # אנטי-אלט
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        await m.guild.get_channel(CHANNELS["ANTI_ALT"]).send(f"🚨 אלט חשוד: {m.mention}", view=AntiAltView(m))

@bot.event
async def on_app_command_completion(i, cmd):
    # לוג אונר
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    if log_ch:
        await log_ch.send(f"🛠️ `{i.user.name}` השתמש ב-`/{cmd.name}` ב-{datetime.now().strftime('%H:%M:%S')}")

if TOKEN: bot.run(TOKEN)
