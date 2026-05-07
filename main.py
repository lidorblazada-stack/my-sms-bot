import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
import firebase_admin
from firebase_admin import credentials, db

# --- הגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
FIREBASE_URL = os.getenv('FIREBASE_URL')
FEEDBACK_CHANNEL_ID = 1502028905253699735 
LOG_CHANNEL_ID = 1499510962296721568 

# רשימת קללות בסיסית (תוכל להוסיף עוד)
BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

feedback_cooldowns = {}

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
            feedback_cooldowns[interaction.user.id] = datetime.now()
            await interaction.response.send_message("נשלח! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        last_sent = feedback_cooldowns.get(interaction.user.id)
        if last_sent and (datetime.now() - last_sent) < timedelta(minutes=5):
            return await interaction.response.send_message("⏳ חכה 5 דקות.", ephemeral=True)
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

# --- פקודות ניהול ---

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
    await interaction.response.send_message(f"✅ הורדה אזהרה ל-{member.mention}. מצב נוכחי: {w}/5")

@bot.tree.command(name="blacklist_add", description="חסימה מהשרת")
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

# --- הגנה אוטומטית (קללות וקישורים) ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # בדיקת רול Owner כדי לא לחסום מנהלים
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    # חסימת קישורים (רק למי שלא צוות)
    if not is_staff and re.search(r'(https?://\S+)', message.content):
        await message.delete()
        return await message.channel.send(f"❌ {message.author.mention}, אסור לשלוח קישורים בשרת!", delete_after=5)

    # חסימת קללות
    if any(word in message.content for word in BAD_WORDS):
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, שמור על שפה נקייה!", delete_after=5)
        # אופציונלי: שליחת לוג
        log_ch = bot.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(f"🛡️ **שומר השרת:** נמחקה קללה מ-{message.author.name}: ||{message.content}||")

@bot.event
async def on_member_join(member):
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted")
        return
    ch = member.guild.system_channel
    if ch:
        embed = discord.Embed(title="הגעת לשרת החזק במדינה! 🔥", description=f"{member.mention}, ברוך הבא!", color=0x2ecc71)
        await ch.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield FINAL is Online.')

if TOKEN:
    bot.run(TOKEN)
