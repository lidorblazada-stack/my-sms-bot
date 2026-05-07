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

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

invites = {}

# --- הגנה: פונקציה שבודקת רק רול Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        has_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_role: return True
        await interaction.response.send_message("❌ פקודה זו שמורה ל-**Owner** בלבד!", ephemeral=True)
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

# --- פקודות ניהול (כולן מוגנות ב-Owner) ---

@bot.tree.command(name="warn", description="מתן אזהרה (Owner Only)")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    ref = db.reference(f'users/{member.id}/warnings')
    w = (ref.get() or 0) + 1
    ref.set(w)
    msg = f"⚠️ {member.mention} הוזהר ({w}/5). סיבה: {reason}"
    if w == 3:
        await member.timeout(timedelta(hours=1))
        msg += "\n🔇 הושם במיוט לשעה."
    elif w >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 הוצא מהשרת."
        ref.set(0)
    await interaction.response.send_message(msg)

@bot.tree.command(name="unwarn", description="הורדת אזהרה (Owner Only)")
@is_owner()
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    ref = db.reference(f'users/{member.id}/warnings')
    w = max(0, (ref.get() or 0) - 1)
    ref.set(w)
    await interaction.response.send_message(f"✅ הורדה אזהרה ל-{member.mention}. מצב: {w}/5")

@bot.tree.command(name="blacklist_add", description="חסימת ID מהשרת (Owner Only)")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').set(True)
    await interaction.response.send_message(f"🚫 {user_id} נחסם מהשרת.")

@bot.tree.command(name="blacklist_remove", description="הסרת ID מחסימה (Owner Only)")
@is_owner()
async def blacklist_remove(interaction: discord.Interaction, user_id: str):
    db.reference(f'blacklist/{user_id}').delete()
    await interaction.response.send_message(f"✅ {user_id} הוסר מהחסימה.")

@bot.tree.command(name="setup_feedback", description="הצבת פאנל פידבק (Owner Only)")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(title="『💎』 פאנל פידבק שומר השרת", description="לחצו למטה כדי לשתף פידבק!", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר בהצלחה!", ephemeral=True)

@bot.tree.command(name="report", description="דיווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000)
    embed.add_field(name="מדווח:", value=interaction.user.mention)
    embed.add_field(name="נדון:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    if log_ch: await log_ch.send(embed=embed)
    await interaction.response.send_message("הדיווח התקבל.", ephemeral=True)

# --- אירועים והגנות אוטומטיות ---

@bot.event
async def on_ready():
    for guild in bot.guilds:
        invites[guild.id] = await guild.invites()
    print(f'🛡️ Cyber-Shield ULTIMATE is Online.')

@bot.event
async def on_member_join(member):
    if db.reference(f'blacklist/{member.id}').get():
        await member.kick(reason="Blacklisted")
        return
    
    # Invite Tracker
    invs_before = invites.get(member.guild.id, [])
    invs_after = await member.guild.invites()
    for invite in invs_before:
        for new_invite in invs_after:
            if invite.code == new_invite.code and invite.uses < new_invite.uses:
                ref = db.reference(f'users/{invite.inviter.id}/credits')
                ref.set((ref.get() or 0) + 3)
    invites[member.guild.id] = invs_after

    ch = member.guild.system_channel
    if ch:
        embed = discord.Embed(title="הגעת לשרת החזק במדינה! 🔥", description=f"{member.mention}, ברוך הבא!", color=0x2ecc71)
        await ch.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # מגן קישורים
        if re.search(r'(https?://\S+)', message.content):
            await message.delete()
            return
        # מגן קללות
        if any(word in message.content for word in BAD_WORDS):
            await message.delete()
            return

    await bot.process_commands(message)

if TOKEN:
    bot.run(TOKEN)
