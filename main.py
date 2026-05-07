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
FEEDBACK_CHANNEL_ID = 1502028905253699735 # ה-ID החדש שלך

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
        # בודק אם לאחד הרולים של המשתמש קוראים Owner
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
        embed = discord.Embed(
            description=f"💬 **פידבק חדש שהתקבל**\n\n{self.feedback_msg.value}", 
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        if is_anon:
            embed.set_author(name="משתמש אנונימי", icon_url="https://i.imgur.com/8fS0S9G.png")
        else:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            feedback_cooldowns[interaction.user.id] = datetime.now()
            await interaction.response.send_message("הפידבק נשלח בהצלחה! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        last_sent = feedback_cooldowns.get(interaction.user.id)
        if last_sent and (datetime.now() - last_sent) < timedelta(minutes=5):
            return await interaction.response.send_message("⏳ ניתן לשלוח פידבק פעם ב-5 דקות.", ephemeral=True)
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

# --- פקודות ניהול (מוגנות ב-Owner) ---

@bot.tree.command(name="setup_feedback", description="יצירת פאנל פידבק (Owner Only)")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(
        title="『💎』 מערכת פידבק שומר השרת",
        description="לחצו על הכפתור למטה כדי לשתף את החוויה שלכם איתנו!",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר בהצלחה!", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש (Owner Only)")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    ref = db.reference(f'users/{member.id}/warnings')
    warnings = ref.get() or 0
    warnings += 1
    ref.set(warnings)
    
    msg = f"⚠️ {member.mention} קיבל אזהרה! ({warnings}/5)\nסיבה: {reason}"
    if warnings == 3:
        await member.timeout(timedelta(hours=1), reason="3 אזהרות")
        msg += "\n🔇 המשתמש הושם במיוט לשעה."
    elif warnings >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 המשתמש הוצא מהשרת לצמיתות."
        ref.set(0)
    await interaction.response.send_message(msg)

@bot.tree.command(name="blacklist_add", description="הוספת משתמש לרשימה שחורה (Owner Only)")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').set(True)
    await interaction.response.send_message(f"🚫 המשתמש עם ה-ID {user_id} נוסף לבלאקליסט.")

@bot.tree.command(name="blacklist_remove", description="הסרת משתמש מרשימה שחורה (Owner Only)")
@is_owner()
async def blacklist_remove(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').delete()
    await interaction.response.send_message(f"✅ המשתמש עם ה-ID {user_id} הוסר מהבלאקליסט.")

# --- אירועים ---

@bot.event
async def on_member_join(member):
    # הגנה מפני בלאקליסט
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted user")
        return

    channel = member.guild.system_channel
    if channel:
        embed = discord.Embed(
            title="ברוך הבא לשרת החזק במדינה! 🔥",
            description=f"שלום {member.mention}, אנחנו שמחים שאתה כאן!",
            color=0x2ecc71
        )
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield is ONLINE and Secured.')

if TOKEN:
    bot.run(TOKEN)
