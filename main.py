import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict

# --- הגדרות ערוצים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FIREBASE_URL = os.getenv('FIREBASE_URL')
FEEDBACK_CHANNEL_ID = 1502028905253699735 
RECOMMEND_CHANNEL_ID = 1501947249658429470 
REPORT_CHANNEL_ID = 1501946934779449505      
LOG_CHANNEL_ID = 1499510962296721568 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

# --- משתני מערכת בזיכרון ---
message_counts = defaultdict(list) # לאנטי-ספאם
nuke_monitoring = defaultdict(list) # לאנטי-ניוק

# --- הגנה: רק Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if is_owner_role or interaction.user.id == interaction.guild.owner_id: return True
        await interaction.response.send_message("❌ פקודה זו למנהלי העל בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מערכת פידבק ---
class FeedbackModal(ui.Modal, title='שליחת פידבק'):
    feedback_msg = ui.TextInput(label='מה תרצה לרשום?', style=discord.TextStyle.long, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💎 פידבק חדש", description=self.feedback_msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel: await channel.send(embed=embed)
        await interaction.response.send_message("הפידבק נשלח בהצלחה!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.blurple, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FeedbackModal())

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות ניהול והגנה ---

@bot.tree.command(name="warnings", description="בדיקת אזהרות של משתמש")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    w = db.reference(f'users/{m.id}/warnings').get() or 0
    await interaction.response.send_message(f"📋 למשתמש {m.mention} יש **{w}/5** אזהרות.")

@bot.tree.command(name="clear", description="ניקוי הודעות")
@is_owner()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=min(amount, 100))
    await interaction.followup.send(f"🧹 נמחקו {len(deleted)} הודעות.")

@bot.tree.command(name="warn", description="מתן אזהרה")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    ref = db.reference(f'users/{member.id}/warnings')
    w = (ref.get() or 0) + 1
    ref.set(w)
    if w >= 5:
        await member.kick(reason="5 אזהרות")
        ref.set(0)
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת עקב 5 אזהרות.")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({w}/5). סיבה: {reason}")

@bot.tree.command(name="mute", description="השתקת משתמש")
@is_owner()
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    await member.timeout(timedelta(minutes=minutes))
    await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

# --- אירועי מערכת (Events) ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # 1. אנטי-ספאם (נשאר לבקשתך!)
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now - t).total_seconds() < 3]
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10), reason="Spamming")
            await message.channel.send(f"🔇 {message.author.mention} הושתקת ל-10 דקות עקב ספאם.")
            return

        # 2. סינון תוכן (מילים רעות וקישורים)
        if any(w in message.content for w in BAD_WORDS) or re.search(r'(https?://\S+|discord\.gg/\S+)', message.content):
            await message.delete()
            return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(title="🗑️ הודעה נמחקה", color=0xe74c3c, timestamp=datetime.now())
        embed.add_field(name="מאת:", value=message.author.mention)
        embed.add_field(name="תוכן:", value=message.content or "תמונה/קובץ")
        embed.set_footer(text=f"ערוץ: {message.channel.name}")
        await log_ch.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.user.id == channel.guild.owner_id: return
        user_id = entry.user.id
        now = datetime.now()
        nuke_monitoring[user_id].append(now)
        nuke_monitoring[user_id] = [t for t in nuke_monitoring[user_id] if (now-t).total_seconds() < 60]
        if len(nuke_monitoring[user_id]) >= 2:
            member = await channel.guild.fetch_member(user_id)
            for role in member.roles:
                try: await member.remove_roles(role)
                except: continue
            log = bot.get_channel(LOG_CHANNEL_ID)
            if log: await log.send(f"🚨 **Anti-Nuke:** הוסרו הרולים ל-{member.mention} עקב מחיקת ערוצים!")

@bot.event
async def on_member_join(member):
    # הודעת ברוך הבא פשוטה
    ch = member.guild.system_channel
    if ch:
        embed = discord.Embed(title=f"ברוך הבא {member.name}! 🔥", description="שמחים שבאת לשרת. קרא חוקים ותהנה!", color=0x2ecc71)
        await ch.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ CYBER-SHIELD V5 ONLINE (Anti-Spam ON | Economy OFF).')

if TOKEN: bot.run(TOKEN)
