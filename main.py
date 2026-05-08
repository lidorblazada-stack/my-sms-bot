import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
from collections import defaultdict

# --- הגדרות ערוצים ורולים (וודא שה-IDs נכונים!) ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1499510962296721568 
FEEDBACK_CHANNEL_ID = 1502028905253699735 
VERIFY_ROLE_ID = 123456789012345678  # שים כאן את ה-ID של הרול "Member" או "Verified"
BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"] 

# מאגרי נתונים בזיכרון
user_warnings = defaultdict(int)
message_counts = defaultdict(list)
nuke_monitoring = defaultdict(list)

# --- 1. מערכת אימות (Verification) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='לחץ כאן כדי להיכנס לשרת ✅', style=discord.ButtonStyle.green, custom_id='persistent:verify')
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה! ברוך הבא לשרת.", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה: רול האימות לא נמצא. פנה למנהל.", ephemeral=True)

# --- 2. מערכת פידבק (Feedback) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק לצוות'):
    feedback_msg = ui.TextInput(label='מה תרצה לומר לנו?', style=discord.TextStyle.long, placeholder="כתוב כאן...", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💎 פידבק חדש", description=self.feedback_msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel: 
            await channel.send(embed=embed)
            await interaction.response.send_message("הפידבק שלך נשלח בהצלחה, תודה!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.blurple, custom_id='persistent:feedback')
    async def feedback_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FeedbackModal())

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        # טעינת הכפתורים כך שיעבדו גם אחרי ריסטארט
        self.add_view(VerifyView())
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# בדיקת צוות (Owner)
def is_owner():
    async def predicate(interaction: discord.Interaction):
        is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if is_owner_role or interaction.user.id == interaction.guild.owner_id: return True
        await interaction.response.send_message("❌ הרשאת Owner נדרשת!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- פקודות סלאש ---

@bot.tree.command(name="setup_verify", description="שליחת הודעת האימות (Verify)")
@is_owner()
async def setup_verify(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ אימות משתמש", description="כדי לקבל גישה לשאר הערוצים בשרת, לחץ על הכפתור למטה.", color=0x2ecc71)
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("מערכת האימות הוקמה!", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="שליחת כפתור פידבק")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(title="💎 הצעות ופידבק", description="יש לך רעיון לשיפור השרת? לחץ על הכפתור וספר לנו!", color=0x3498db)
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("מערכת הפידבק הוקמה!", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    user_warnings[member.id] += 1
    if user_warnings[member.id] >= 5:
        await member.kick(reason="5 אזהרות")
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת (5 אזהרות).")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5). סיבה: {reason}")

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 למשתמש {m.mention} יש **{user_warnings[m.id]}/5** אזהרות.")

@bot.tree.command(name="clear", description="ניקוי צ'אט")
@is_owner()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=min(amount, 100))
    await interaction.followup.send(f"🧹 נמחקו {len(deleted)} הודעות.")

# --- הגנות אוטומטיות ולוגים ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    if not is_staff:
        # אנטי-ספאם
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now-t).total_seconds() < 3]
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10))
            return
        # סינון
        if any(word in message.content for word in BAD_WORDS) or re.search(r'(https?://\S+|discord\.gg/\S+)', message.content):
            await message.delete()
            return
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(title="🗑️ הודעה נמחקה", color=0xe74c3c, timestamp=datetime.now())
        embed.add_field(name="משתמש:", value=message.author.mention)
        embed.add_field(name="תוכן:", value=message.content or "תמונה/קובץ")
        await log_ch.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.user.id == channel.guild.owner_id: return
        user_id = entry.user.id
        now = datetime.now()
        nuke_monitoring[user_id].append(now)
        if len(nuke_monitoring[user_id]) >= 2:
            member = await channel.guild.fetch_member(user_id)
            for role in member.roles:
                try: await member.remove_roles(role)
                except: continue
            log = bot.get_channel(LOG_CHANNEL_ID)
            if log: await log.send(f"🚨 **ניסיון פריצה:** {member.mention} ניסה למחוק ערוצים!")

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield הופעל עם כל המערכות!')

if TOKEN: bot.run(TOKEN)
