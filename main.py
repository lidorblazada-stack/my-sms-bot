import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID (תוודא שהן מעודכנות ב-Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
VERIFY_ROLE_ID = 1501983948111352091 

user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)
feedback_cooldowns = {}

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

# --- פונקציית הגנה (לוגים + אזהרות) ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון פריצה לפקודה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention} ({interaction.user.id})")
        embed.add_field(name="פקודה:", value=f"/{interaction.command.name}")
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **פקודה ל-OWNER בלבד!** ניסיון נוסף יגרור אזהרה.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **אזהרה רשמית!** ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- מערכת פידבק (חלון אחד + אנונימיות) ---
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, placeholder="מה תרצה להגיד לנו?", required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        last = feedback_cooldowns.get(interaction.user.id)
        if last and (now - last).seconds < 300:
            return await interaction.response.send_message(f"⏳ חכה {300 - (now - last).seconds} שניות.", ephemeral=True)

        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anon.value.strip() == "כן"
            name = "Anonymous User 👤" if is_anon else interaction.user.name
            icon = "https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url
            
            emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            emb.set_author(name=name, icon_url=icon)
            
            # שליחת הפידבק עם הכפתור המבוקש תחתיו
            await ch.send(embed=emb, view=QuickFeedbackView())
            feedback_cooldowns[interaction.user.id] = now
            await interaction.response.send_message("✅ הפידבק נשלח בהצלחה!", ephemeral=True)

class FeedbackView(ui.View): # פאנל ראשי
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="main_fb")
    async def fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

class QuickFeedbackView(ui.View): # כפתור מתחת להודעות
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.gray, custom_id="quick_fb")
    async def q_fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

# --- פקודות Setup וניהול ---
@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק")
async def sf(i: discord.Interaction):
    if await check_is_owner(i):
        await i.channel.send(embed=discord.Embed(title="New Feedback", description="לחצו למטה כדי לשלוח פידבק!", color=0x3498db), view=FeedbackView())
        await i.response.send_message("הוקם בהצלחה", ephemeral=True)

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות")
async def sv(i: discord.Interaction):
    if await check_is_owner(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות משתמש", color=0x2ecc71), view=VerifyView())
        await i.response.send_message("הוקם בהצלחה", ephemeral=True)

# --- פאנל אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await i.user.add_roles(role)
            await i.response.send_message("אומתת!", ephemeral=True)

@bot.event
async def on_member_join(member):
    # וולקם
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"ברוך הבא {member.mention}! 🔥", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    bot.add_view(FeedbackView())
    bot.add_view(QuickFeedbackView())
    print(f"🛡️ Cyber-Shield IS LIVE & UPDATED!")

if TOKEN: bot.run(TOKEN)
