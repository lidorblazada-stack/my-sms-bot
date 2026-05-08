import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID (תוודא שהן תואמות לשרת שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
VERIFY_ROLE_ID = 1501983948111352091 

user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)
feedback_cooldowns = {} # ניהול קולדאון לפי ID

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

# --- פונקציית אבטחה לניהול (לוגים + אזהרות) ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
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

# --- מערכת פידבק משודרגת (אנונימיות + קולדאון) ---
class FeedbackModal(ui.Modal, title="שלח פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, placeholder="כתוב כאן את הפידבק שלך...", required=True)
    anonymous = ui.TextInput(label="להישאר אנונימי? (כן/לא)", placeholder="כתוב 'כן' כדי להישאר אנונימי", default="לא", max_length=2, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # בדיקת קולדאון (5 דקות)
        now = datetime.now()
        last_time = feedback_cooldowns.get(interaction.user.id)
        if last_time and (now - last_time).seconds < 300:
            remaining = 300 - (now - last_time).seconds
            return await interaction.response.send_message(f"⏳ אתה בקולדאון! נסה שוב בעוד {remaining // 60} דקות.", ephemeral=True)

        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anonymous.value.strip().lower() == "כן"
            user_label = "Anonymous User" if is_anon else interaction.user.name
            icon = "https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url
            
            embed = discord.Embed(title="💬 פידבק חדש התקבל!", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=user_label, icon_url=icon)
            await ch.send(embed=embed)
            
            feedback_cooldowns[interaction.user.id] = now # עדכון זמן אחרון
            await interaction.response.send_message("✅ הפידבק שלך נשלח בהצלחה!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="fb_btn")
    async def fb_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal())

# --- מערכת אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role in interaction.user.roles:
            await interaction.response.send_message("אתה כבר מאומת!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ אומתת בהצלחה!", ephemeral=True)

# --- פקודות Setup (OWNER) ---
@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק (OWNER)")
async def setup_f(i: discord.Interaction):
    if await check_is_owner(i):
        embed = discord.Embed(title="New Feedback", description="לחצו על הכפתור למטה כדי לשלוח לנו פידבק!", color=0x3498db)
        await i.channel.send(embed=embed, view=FeedbackView())
        await i.response.send_message("פאנל פידבק הוקם!", ephemeral=True)

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות (OWNER)")
async def setup_v(i: discord.Interaction):
    if await check_is_owner(i):
        embed = discord.Embed(title="🛡️ אימות משתמש", description="לחץ על הכפתור כדי לקבל גישה לשרת", color=0x2ecc71)
        await i.channel.send(embed=embed, view=VerifyView())
        await i.response.send_message("פאנל אימות הוקם!", ephemeral=True)

# --- פקודות ניהול ואזהרות ---
@bot.tree.command(name="warn", description="מתן אזהרה (OWNER)")
async def warn(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def check_w(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    await i.response.send_message(f"📋 למשתמש {m.mention} יש {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות (OWNER)")
async def cw(i: discord.Interaction, member: discord.Member):
    if await check_is_owner(i):
        user_warnings[member.id] = 0
        await i.response.send_message(f"✅ האזהרות של {member.mention} אופסו.")

# --- אירועים: וולקם + Alt Detector ---
@bot.event
async def on_member_join(member):
    # Alt Detector ללוג
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשוד!" if age.days < 3 else "✅ תקין"
        await log_ch.send(f"👤 **כניסה:** {member.mention} | **גיל חשבון:** {age.days} ימים | **סטטוס:** {status}")
    
    # וולקם
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"**ברוך הבא {member.mention} לשרת! 🔥**", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    bot.add_view(FeedbackView())
    print(f"🛡️ Server Guard Unified is ACTIVE!")

if TOKEN: bot.run(TOKEN)
