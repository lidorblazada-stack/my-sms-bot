import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import firebase_admin
from firebase_admin import credentials, db

# --- הגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
FIREBASE_URL = os.getenv('FIREBASE_URL')
FEEDBACK_CHANNEL_ID = 1502028905253699735 
LOG_CHANNEL_ID = 1499510962296721568 # ערוץ הלוגים/דיווחים שדיברנו עליו

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_URL
    })

feedback_cooldowns = {}

# --- פונקציית הגנה: רק Owner יכול להשתמש ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        has_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_role:
            return True
        await interaction.response.send_message("❌ פקודה זו שמורה ל-**Owner** בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מערכת הפידבק ---
class FeedbackModal(ui.Modal, title='שליחת פידבק לשומר השרת'):
    feedback_msg = ui.TextInput(label='מה תרצה לרשום?', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='אנונימי? (כן/לא)', min_length=2, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        is_anon = self.anonymous.value.strip() == "כן"
        embed = discord.Embed(description=f"💬 **פידבק חדש**\n\n{self.feedback_msg.value}", color=0x2ecc71, timestamp=datetime.now(timezone.utc))
        if is_anon:
            embed.set_author(name="Anonymous User", icon_url="https://i.imgur.com/8fS0S9G.png")
        else:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            feedback_cooldowns[interaction.user.id] = datetime.now()
            await interaction.response.send_message("הפידבק נשלח! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        last_sent = feedback_cooldowns.get(interaction.user.id)
        if last_sent and (datetime.now() - last_sent) < timedelta(minutes=5):
            return await interaction.response.send_message("⏳ חכה 5 דקות.", ephemeral=True)
        await interaction.response.send_modal(FeedbackModal())

# --- הגדרת הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- כל הפקודות שחזרו (Owner Only) ---

@bot.tree.command(name="warn", description="מתן אזהרה")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    ref = db.reference(f'users/{member.id}/warnings')
    warnings = ref.get() or 0
    warnings += 1
    ref.set(warnings)
    msg = f"⚠️ {member.mention} קיבל אזהרה! ({warnings}/5)\nסיבה: {reason}"
    if warnings == 3:
        await member.timeout(timedelta(hours=1))
        msg += "\n🔇 הושם במיוט לשעה."
    elif warnings >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 הוצא מהשרת."
        ref.set(0)
    await interaction.response.send_message(msg)

@bot.tree.command(name="mute", description="השתקת משתמש")
@is_owner()
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int = 60):
    await member.timeout(timedelta(minutes=minutes))
    await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

@bot.tree.command(name="kick", description="הוצאת משתמש מהשרת")
@is_owner()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} הוצא מהשרת. סיבה: {reason}")

@bot.tree.command(name="blacklist_add", description="הוספה לבלאקליסט")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').set(True)
    await interaction.response.send_message(f"🚫 ID {user_id} נחסם מהשרת.")

@bot.tree.command(name="blacklist_remove", description="הסרה מבלאקליסט")
@is_owner()
async def blacklist_remove(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').delete()
    await interaction.response.send_message(f"✅ ID {user_id} שוחרר מהחסימה.")

@bot.tree.command(name="setup_feedback", description="הצבת פאנל פידבק")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(title="『💎』 מערכת פידבק", description="לחצו למטה לשתף פידבק!", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר.", ephemeral=True)

# --- אירועים והודעות אוטומטיות ---

@bot.event
async def on_member_join(member):
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted")
        return
    channel = member.guild.system_channel
    if channel:
        embed = discord.Embed(title="ברוך הבא לשרת החזק במדינה! 🔥", description=f"{member.mention}, שמחים לראות אותך!", color=0x2ecc71)
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ All systems ONLINE.')

if TOKEN:
    bot.run(TOKEN)
