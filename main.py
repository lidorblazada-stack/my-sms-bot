import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
import firebase_admin
from firebase_admin import credentials, db

# --- הגדרות ערוצים ---
TOKEN = os.getenv('DISCORD_TOKEN')
FIREBASE_URL = os.getenv('FIREBASE_URL')
FEEDBACK_CHANNEL_ID = 1502028905253699735 
RECOMMEND_CHANNEL_ID = 1501947249658429470 # ערוץ המלצות
REPORT_CHANNEL_ID = 1501946934779449505    # ערוץ רפורט

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

invites = {}

# --- הגנה: רק Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        has_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_role: return True
        await interaction.response.send_message("❌ פקודה זו ל-**Owner** בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מערכת פידבק ---
class FeedbackModal(ui.Modal, title='שליחת פידבק לשומר השרת'):
    feedback_msg = ui.TextInput(label='מה תרצה לרשום?', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='אנונימי? (כן/לא)', min_length=2, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        is_anon = self.anonymous.value.strip() == "כן"
        embed = discord.Embed(description=f"💬 **פידבק חדש**\n\n{self.feedback_msg.value}", color=0x2ecc71, timestamp=datetime.now(timezone.utc))
        embed.set_author(name="Anonymous" if is_anon else interaction.user.name)
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            await interaction.response.send_message("הפידבק נשלח! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
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
        msg += "\n🔇 מיוט לשעה."
    elif w >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 הוצא מהשרת."
        ref.set(0)
    await interaction.response.send_message(msg)

@bot.tree.command(name="unwarn", description="הורדת אזהרה")
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
    await interaction.response.send_message(f"🚫 {user_id} נחסם.")

@bot.tree.command(name="setup_feedback", description="פאנל פידבק")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(title="『💎』 פאנל פידבק", description="שתפו אותנו בדעתכם!", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("נוצר.", ephemeral=True)

# --- פקודות משתמשים (דיווח והמלצה) ---

@bot.tree.command(name="report", description="דיווח על משתמש בעייתי")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    embed = discord.Embed(title="🚨 דיווח משתמש חדש", color=0xff0000, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="המדווח:", value=interaction.user.mention)
    embed.add_field(name="המשתמש הבעייתי:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    if channel: await channel.send(embed=embed)
    await interaction.response.send_message("הדיווח נשלח לצוות לבדיקה.", ephemeral=True)

@bot.tree.command(name="recommend", description="שלח המלצה על השרת")
async def recommend(interaction: discord.Interaction, text: str):
    channel = bot.get_channel(RECOMMEND_CHANNEL_ID)
    embed = discord.Embed(title="⭐️ המלצה חדשה!", description=text, color=0xf1c40f, timestamp=datetime.now(timezone.utc))
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
    if channel: await channel.send(embed=embed)
    await interaction.response.send_message("תודה על ההמלצה שלך! ✨", ephemeral=True)

# --- אירועים והגנות ---

@bot.event
async def on_member_join(member):
    # בדיקת בלאקליסט
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted")
        return
    
    # הודעת וולקם
    ch = member.guild.system_channel
    if ch:
        embed = discord.Embed(title="ברוך הבא לשרת החזק במדינה! 🔥", description=f"{member.mention}, שמחים שבאת!", color=0x2ecc71)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        if re.search(r'(https?://\S+)', message.content): # מגן קישורים
            await message.delete()
            return
        if any(word in message.content for word in BAD_WORDS): # מגן קללות
            await message.delete()
            return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield Final is Online with Recommendations & Reports.')

if TOKEN:
    bot.run(TOKEN)
