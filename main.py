import alts
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

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

feedback_cooldowns = {}
message_counts = defaultdict(list) # למערכת האנטי-ספאם

# --- הגנה: רק Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        has_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_role: return True
        await interaction.response.send_message("❌ פקודה זו ל-**Owner** בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מערכת פידבק (5 דקות המתנה) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק לשומר השרת'):
    feedback_msg = ui.TextInput(label='מה תרצה לרשום?', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='אנונימי? (כן/לא)', min_length=2, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        is_anon = self.anonymous.value.strip() == "כן"
        embed = discord.Embed(title="💎 פידבק חדש", description=self.feedback_msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
        embed.set_author(name="אנונימי" if is_anon else interaction.user.name)
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            feedback_cooldowns[interaction.user.id] = datetime.now()
            await interaction.response.send_message("נשלח בהצלחה!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.blurple, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        last_sent = feedback_cooldowns.get(interaction.user.id)
        if last_sent and (datetime.now() - last_sent) < timedelta(minutes=5):
            return await interaction.response.send_message("⏳ ניתן לשלוח פידבק פעם ב-5 דקות.", ephemeral=True)
        await interaction.response.send_modal(FeedbackModal())

# --- הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות ניהול (Owner Only) ---

@bot.tree.command(name="warn", description="מתן אזהרה")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    ref = db.reference(f'users/{member.id}/warnings')
    w = (ref.get() or 0) + 1
    ref.set(w)
    msg = f"⚠️ {member.mention} הוזהר ({w}/5). סיבה: {reason}"
    if w == 3:
        await member.timeout(timedelta(hours=1))
        msg += "\n🔇 מיוט אוטומטי לשעה."
    elif w >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 המשתמש הועף מהשרת."
        ref.set(0)
    await interaction.response.send_message(msg)

@bot.tree.command(name="unwarn", description="הסרת אזהרה")
@is_owner()
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    ref = db.reference(f'users/{member.id}/warnings')
    w = max(0, (ref.get() or 0) - 1)
    ref.set(w)
    await interaction.response.send_message(f"✅ הורדה אזהרה ל-{member.mention}. מצב: {w}/5")

@bot.tree.command(name="blacklist_add", description="חסימת ID")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').set(True)
    await interaction.response.send_message(f"🚫 {user_id} נחסם מהשרת.")

@bot.tree.command(name="setup_feedback", description="פאנל פידבק")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(title="『💎』 מערכת פידבק שומר השרת", description="דעתכם חשובה לנו! לחצו למטה.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("נוצר.", ephemeral=True)

# --- פקודות קהילה ---

@bot.tree.command(name="report", description="דיווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = bot.get_channel(REPORT_CHANNEL_ID)
    embed = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c)
    embed.add_field(name="מדווח:", value=interaction.user.mention)
    embed.add_field(name="נילוֹן:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    if ch: await ch.send(embed=embed)
    await interaction.response.send_message("הדיווח התקבל בחדר המבצעים.", ephemeral=True)

@bot.tree.command(name="recommend", description="המלצה על השרת")
async def recommend(interaction: discord.Interaction, text: str):
    ch = bot.get_channel(RECOMMEND_CHANNEL_ID)
    embed = discord.Embed(title="⭐ המלצה חדשה", description=text, color=0xf1c40f)
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
    if ch: await ch.send(embed=embed)
    await interaction.response.send_message("תודה על ההמלצה!", ephemeral=True)

# --- הגנות אוטומטיות מתקדמות ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # 1. אנטי-ספאם
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now - t).total_seconds() < 3]
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10), reason="Spamming")
            await message.channel.send(f"🔇 {message.author.mention} הושתק ל-10 דקות עקב ספאם.")
            return

        # 2. מגן קישורים והזמנות לשרתים אחרים
        if re.search(r'(https?://\S+|discord\.gg/\S+)', message.content):
            await message.delete()
            log_ch = bot.get_channel(LOG_CHANNEL_ID)
            if log_ch: await log_ch.send(f"🛡️ **קישור נמחק:** {message.author.mention} ניסה לשלוח קישור.")
            return

        # 3. מגן קללות
        if any(word in message.content for word in BAD_WORDS):
            await message.delete()
            return

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted")
        return
    ch = member.guild.system_channel
    if ch:
        embed = discord.Embed(title="ברוך הבא לשרת החזק במדינה! 🔥", description=f"{member.mention}, שמחים שבאת!", color=0x2ecc71)
        embed.set_image(url="https://i.imgur.com/your_welcome_image.png") # תוכל להוסיף לינק לתמונה
        await ch.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ CYBER-SHIELD ULTIMATE ONLINE.')

if TOKEN:
    bot.run(TOKEN)
