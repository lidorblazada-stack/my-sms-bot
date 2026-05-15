import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- 1. חיבורים (Firebase & TOKEN) ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. מפת ה-IDs של לידור (לפי המגילה) ---
CHANNELS = {
    "RECOMMEND": 1501947249658429470,  # המלצות
    "REPORTS": 1501946934779449505,    # דיווחים על אנשים
    "FEEDBACK": 1503475379942461522,   # פידבק (אנונימי/גלוי)
    "OWNER_LOGS": 1503496964732354620, # לוגים של פקודות אונר
    "ANTI_ALT": 1503464176599695380,   # מערכת אנטי-אלט (חשודים)
    "WELCOME": 1501713652217282591,    # וולקם וביי
    "WARNS_LOG": 1502014872655888554   # לוג אזהרות (מילוליות/רשמיות)
}

ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,      # רול מיוט (3 אזהרות)
    "SUSPECT": 1501953906736103535,   # רול חשוד
    "STAFF": 1501316672345211041,
    "VIP": 1503817695466881255,
    "SUPPORTER": 1503819239310627068
}

feedback_cooldown = {} # למניעת ספאם פידבקים (5 דקות)

# --- 3. פונקציות עזר ולוגים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == ROLES["OWNER"] for r in user.roles) or user.id == 1130542850883469443

async def log_action(guild, channel_key, embed):
    channel = guild.get_channel(CHANNELS[channel_key])
    if channel: await channel.send(embed=embed)

# --- 4. פאנלים (Views & Modals) ---

# פאנל דיווחים (Report)
class ReportModal(ui.Modal, title="דיווח על משתמש"):
    target = ui.TextInput(label="על מי הדיווח? (שם/ID)", placeholder="למשל: Lidor#1234")
    reason = ui.TextInput(label="סיבת הדיווח", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        embed = discord.Embed(title="🚨 דיווח חדש התקבל", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="מדווח:", value=i.user.mention, inline=True)
        embed.add_field(name="נגד:", value=self.target.value, inline=True)
        embed.add_field(name="סיבה:", value=self.reason.value, inline=False)
        await log_action(i.guild, "REPORTS", embed)
        await i.response.send_message("הדיווח נשלח לצוות.", ephemeral=True)

# פאנל פידבק (Feedback)
class FeedbackModal(ui.Modal, title="שליחת פידבק"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", min_length=2, max_length=2, default="לא")
    async def on_submit(self, i):
        now = datetime.now().timestamp()
        if i.user.id in feedback_cooldown and now - feedback_cooldown[i.user.id] < 300:
            return await i.response.send_message("חכה 5 דקות בין פידבק לפידבק אחי.", ephemeral=True)
        
        user_display = "אנונימי" if self.anon.value == "כן" else i.user.mention
        embed = discord.Embed(title="📩 פידבק חדש", description=self.msg.value, color=0x00fbff)
        embed.set_footer(text=f"נשלח על ידי: {user_display}")
        
        view = ui.View()
        btn = ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.grey, custom_id="new_fb")
        view.add_item(btn) # כפתור למטה לפי בקשתך
        
        ch = i.guild.get_channel(CHANNELS["FEEDBACK"])
        await ch.send(embed=embed, view=view)
        feedback_cooldown[i.user.id] = now
        await i.response.send_message("תודה על הפידבק!", ephemeral=True)

# פאנל אנטי-אלט (Anti-Alt)
class AntiAltView(ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף (Kick)", style=discord.ButtonStyle.danger)
    async def kick(self, i, b):
        await self.member.kick(); await i.response.send_message("הועף.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success)
    async def stay(self, i, b):
        await i.response.send_message("המשתמש אושר.")
    @ui.button(label="חשוד (Role)", style=discord.ButtonStyle.secondary)
    async def suspect(self, i, b):
        await self.member.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("קיבל רול חשוד.")

# --- 5. אירועים (Welcome/Alt/Logs) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_member_join(member):
    # Welcome & Bye (ID: 1501713652217282591)
    ch = member.guild.get_channel(CHANNELS["WELCOME"])
    if ch:
        embed = discord.Embed(title=f"ברוך הבא {member.name}!", description="הצטרפת לאימפריה של לידור!", color=0x00ff00)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)

    # Anti-Alt (ID: 1503464176599695380)
    if (datetime.now(member.created_at.tzinfo) - member.created_at).days < 7:
        log_ch = member.guild.get_channel(CHANNELS["ANTI_ALT"])
        embed = discord.Embed(title="⚠️ זיהוי משתמש חשוד (אלט)", description=f"{member.mention} נרשם לפני פחות משבוע!", color=0xffa500)
        await log_ch.send(embed=embed, view=AntiAltView(member))

@bot.event
async def on_app_command_completion(interaction, command):
    # לוג פקודות אונר (ID: 1503496964732354620)
    if await is_owner(interaction.user):
        embed = discord.Embed(title="🛠️ שימוש בפקודת אונר", color=0x3498db, timestamp=datetime.now())
        embed.add_field(name="אונר:", value=interaction.user.mention)
        embed.add_field(name="פקודה:", value=f"/{command.name}")
        await log_action(interaction.guild, "OWNER_LOGS", embed)

# --- 6. פקודות הקמה ---
@bot.tree.command(name="setup_feedback")
async def s_fb(i):
    if await is_owner(i.user):
        view = ui.View(); view.add_item(ui.Button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="open_fb_modal"))
        await i.channel.send("📩 **מרכז הפידבקים**\nלחצו למטה כדי לשלוח פידבק לצוות.", view=view)
        await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_report")
async def s_rp(i):
    if await is_owner(i.user):
        view = ui.View(); view.add_item(ui.Button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="open_report"))
        await i.channel.send("🚨 **מרכז דיווחים**\nראיתם מישהו עובר על החוקים? דווחו כאן.", view=view)
        await i.response.send_message("הוקם.", ephemeral=True)

# פקודת אזהרה רשמית (ID: 1502014872655888554)
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, reason: str):
    if await is_owner(i.user):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        embed = discord.Embed(title="⚠️ אזהרה רשמית", color=0xffa500)
        embed.add_field(name="משתמש:", value=m.mention)
        embed.add_field(name="סיבה:", value=reason)
        embed.add_field(name="מספר אזהרה:", value=str(w+1))
        await log_action(i.guild, "WARNS_LOG", embed)
        if w+1 >= 3:
            await m.add_roles(i.guild.get_role(ROLES["MUTE"]))
            await i.channel.send(f"{m.mention} קיבל מיוט אוטומטי על 3 אזהרות!")
        await i.response.send_message("האזהרה נרשמה.")

bot.run(TOKEN)
