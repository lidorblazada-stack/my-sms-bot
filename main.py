import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים ומשתנים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. מפת ה-IDs המדויקת של לידור ---
CHANNELS = {
    "RECOMMEND": 1501947249658429470,  # המלצות
    "REPORTS": 1501946934779449505,    # דיווחים על אנשים
    "FEEDBACK": 1503475379942461522,   # פידבקים (כולל אנונימי)
    "OWNER_LOGS": 1503496964732354620, # לוגים של פקודות אונר
    "WARNS_LOG": 1502014872655888554,  # לוג אזהרות
    "ANTI_ALT": 1503464176599695380,   # מערכת אנטי-אלט
    "WELCOME": 1501713652217282591     # וולקם וביי
}

ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1501953906736103535,
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255,
    "SUPPORTER": 1503819239310627068
}

feedback_cooldown = {}
jail_list = {}

# --- 3. פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

# --- 4. מערכת פידבקים (אנונימי + כפתור מתחת לכל פידבק) ---
class FeedbackModal(ui.Modal, title="שליחת פידבק"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", min_length=2, max_length=2, default="לא")
    
    async def on_submit(self, i):
        now = datetime.now().timestamp()
        if i.user.id in feedback_cooldown and now - feedback_cooldown[i.user.id] < 300:
            return await i.response.send_message("מותר פידבק פעם ב-5 דקות אחי.", ephemeral=True)
        
        user_display = "🤫 משתמש אנונימי" if self.anon.value == "כן" else i.user.mention
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_author(name=f"מאת: {i.user.name}", icon_url=i.user.display_avatar.url)
        embed.set_footer(text=f"סטטוס: {user_display}")
        
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.primary, custom_id="trigger_feedback"))
        
        ch = i.guild.get_channel(CHANNELS["FEEDBACK"])
        await ch.send(embed=embed, view=view)
        feedback_cooldown[i.user.id] = now
        await i.response.send_message("הפידבק נשלח בהצלחה!", ephemeral=True)

# --- 5. מערכת דיווחים (אינמבד יפה של מי דיווח ועל מי) ---
class ReportModal(ui.Modal, title="דיווח על משתמש"):
    target = ui.TextInput(label="על מי הדיווח?", placeholder="שם המשתמש או ID")
    reason = ui.TextInput(label="סיבת הדיווח", style=discord.TextStyle.paragraph)
    
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח רשמי התקבל", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="👤 מדווח", value=i.user.mention, inline=True)
        embed.add_field(name="🎯 על מי", value=self.target.value, inline=True)
        embed.add_field(name="📄 סיבה", value=self.reason.value, inline=False)
        embed.set_thumbnail(url=i.user.display_avatar.url)
        
        ch = i.guild.get_channel(CHANNELS["REPORTS"])
        await ch.send(embed=embed)
        await i.response.send_message("הדיווח הועבר לטיפול הצוות.", ephemeral=True)

# --- 6. מערכת אנטי-אלט (כפתורים להעיף/להשאיר) ---
class AntiAltView(ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="העיף (Kick)", style=discord.ButtonStyle.danger)
    async def kick(self, i, b):
        if not await is_owner(i.user): return
        await self.member.kick(reason="Alt detected"); await i.response.send_message("המחשב הועף מהשרת.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success)
    async def stay(self, i, b):
        if not await is_owner(i.user): return
        await i.response.send_message("המשתמש אושר.")
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary)
    async def suspect(self, i, b):
        if not await is_owner(i.user): return
        await self.member.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("הרול 'חשוד' ניתן.")

# --- 7. הגדרת הבוט ואירועים (Welcome/Bye/Logs) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(AntiAltView(None)) # לרישום הכפתורים
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    # Welcome & Bye
    ch = member.guild.get_channel(CHANNELS["WELCOME"])
    if ch:
        embed = discord.Embed(title=f"ברוך הבא {member.name}! 👋", description="שמחים שאתה כאן!", color=0x00ff00)
        embed.set_image(url=member.display_avatar.url)
        await ch.send(content=member.mention, embed=embed)

    # Anti-Alt (פחות מ-7 ימים)
    if (datetime.now(member.created_at.tzinfo) - member.created_at).days < 7:
        log_ch = member.guild.get_channel(CHANNELS["ANTI_ALT"])
        if log_ch:
            embed = discord.Embed(title="⚠️ זיהוי אלט חשוד", description=f"{member.mention} נרשם לפני פחות משבוע!", color=0xffa500)
            await log_ch.send(embed=embed, view=AntiAltView(member))

@bot.event
async def on_member_remove(member):
    ch = member.guild.get_channel(CHANNELS["WELCOME"])
    if ch: await ch.send(f"😢 **{member.name}** עזב אותנו... נתראה!")

# --- 8. פקודות ניהול (אזהרות מילוליות/רשמיות) ---
@bot.tree.command(name="warn", description="מתן אזהרה רשמית")
async def warn(i, m: discord.Member, reason: str):
    if await is_owner(i.user):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        embed = discord.Embed(title="⚠️ אזהרה רשמית", color=0xffa500, timestamp=datetime.now())
        embed.add_field(name="משתמש", value=m.mention); embed.add_field(name="סיבה", value=reason)
        embed.add_field(name="כמות אזהרות", value=str(w+1))
        await i.guild.get_channel(CHANNELS["WARNS_LOG"]).send(embed=embed)
        if w+1 >= 3:
            await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
            await i.channel.send(f"🚫 {m.mention} הושבת אוטומטית (3 אזהרות).")
        await i.response.send_message(f"אזהרה נרשמה ל-{m.mention}.", ephemeral=True)

# --- 9. פקודות הקמה (Setup) ---
@bot.tree.command(name="setup_feedback")
async def s_fb(i):
    if await is_owner(i.user):
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="trigger_feedback"))
        await i.channel.send("📩 **מרכז הפידבקים**", view=view)
        await i.response.send_message("הוקם", ephemeral=True)

# --- האזנה לכפתורים קבועים ---
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == "trigger_feedback":
            await interaction.response.send_modal(FeedbackModal())
        elif interaction.data['custom_id'] == "open_report":
            await interaction.response.send_modal(ReportModal())

if TOKEN:
    bot.run(TOKEN)
