import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- כל ה-IDs שלך (מעודכן) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
REPORTS_CH_ID = 1501946934779449505    # ID רפורטים שהבאת
SUGGESTIONS_CH_ID = 1501947249658429470 # ID המלצות שהבאת
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

# --- הגנה לאונר ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון פריצה", color=0xff0000)
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention}")
        embed.add_field(name="פקודה:", value=f"/{interaction.command.name}")
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    msg = "❌ ל-OWNER בלבד!" if abuse_attempts[interaction.user.id] == 1 else "⚠️ אזהרה נרשמה!"
    if abuse_attempts[interaction.user.id] > 1: user_warnings[interaction.user.id] += 1
    await interaction.response.send_message(msg, ephemeral=True)
    return False

# --- מערכת פידבק עם כפתור מהיר ---
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        last = feedback_cooldowns.get(interaction.user.id)
        if last and (now - last).seconds < 300:
            return await interaction.response.send_message("⏳ חכה 5 דקות.", ephemeral=True)

        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anon.value.strip() == "כן"
            name = "Anonymous User 👤" if is_anon else interaction.user.name
            icon = "https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url
            emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            emb.set_author(name=name, icon_url=icon)
            await ch.send(embed=emb, view=QuickFeedbackView())
            feedback_cooldowns[interaction.user.id] = now
            await interaction.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="main_fb")
    async def fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

class QuickFeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.gray, custom_id="quick_fb")
    async def q_fb(self, interaction, button): await interaction.response.send_modal(FeedbackModal())

# --- פקודות דיווחים והמלצות ---

@bot.tree.command(name="report", description="דיווח על משתמש או בעיה בשרת")
async def report(i: discord.Interaction, reason: str):
    ch = i.guild.get_channel(REPORTS_CH_ID)
    if ch:
        emb = discord.Embed(title="🚨 דיווח חדש", description=reason, color=0xffa500, timestamp=datetime.now(timezone.utc))
        emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        await ch.send(embed=emb)
        await i.response.send_message("✅ הדיווח נשלח לצוות לבדיקה.", ephemeral=True)

@bot.tree.command(name="suggest", description="שליחת המלצה או רעיון לשיפור השרת")
async def suggest(i: discord.Interaction, suggestion: str):
    ch = i.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        emb = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0xfee75c, timestamp=datetime.now(timezone.utc))
        emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        await ch.send(embed=emb)
        await i.response.send_message("✅ הרעיון שלך נשלח לערוץ ההמלצות!", ephemeral=True)

# --- פקודות ניהול (Owner) ---
@bot.tree.command(name="setup_feedback", description="[OWNER] הקמת פאנל פידבק")
async def sf(i: discord.Interaction): 
    if await check_is_owner(i): 
        await i.channel.send(embed=discord.Embed(title="New Feedback", color=0x3498db), view=FeedbackView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[OWNER] הקמת פאנל אימות")
async def sv(i: discord.Interaction): 
    if await check_is_owner(i): 
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="ban", description="[OWNER] חסימת משתמש")
async def ban(i, member: discord.Member, reason: str = "ללא"):
    if await check_is_owner(i): await member.ban(reason=reason); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def clear(i, amount: int):
    if await check_is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="mute", description="[OWNER] השתקת משתמש")
async def mute(i, member: discord.Member, minutes: int):
    if await check_is_owner(i): await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.name} הושתק.")

# --- אירועים ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

@bot.event
async def on_member_join(member):
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"ברוך הבא {member.mention}! 🔥", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    bot.add_view(VerifyView()); bot.add_view(FeedbackView()); bot.add_view(QuickFeedbackView())
    print(f"🛡️ Cyber-Shield Pro IS FULLY LOADED!")

if TOKEN: bot.run(TOKEN)
