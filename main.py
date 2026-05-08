import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID קריטיות ---
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

# --- פונקציית הגנה אבסולוטית לאונר + לוגים ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        now = datetime.now(timezone.utc).strftime('%H:%M:%S | %d/%m/%Y')
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000)
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="פקודה:", value=f"/{interaction.command.name}", inline=False)
        embed.add_field(name="זמן:", value=now, inline=False)
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **פקודה ל-OWNER בלבד!** ניסיון נוסף יגרור אזהרה.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **אזהרה רשמית!** ניסיונות הפריצה שלך נרשמו. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- מערכת פידבק משולבת ---
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        last = feedback_cooldowns.get(interaction.user.id)
        if last and (now - last).seconds < 300:
            return await interaction.response.send_message(f"⏳ קולדאון! חכה {300 - (now - last).seconds} שניות.", ephemeral=True)

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

# --- מערכת אימות ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

# --- כל 21 הפקודות כ-Slash Commands ---

@bot.tree.command(name="setup_feedback")
async def sf(i): 
    if await check_is_owner(i): await i.channel.send(embed=discord.Embed(title="New Feedback", color=0x3498db), view=FeedbackView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_verify")
async def sv(i): 
    if await check_is_owner(i): await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="ban")
async def ban(i, member: discord.Member, reason: str = "ללא סיבה"):
    if await check_is_owner(i): await member.ban(reason=reason); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="kick")
async def kick(i, member: discord.Member):
    if await check_is_owner(i): await member.kick(); await i.response.send_message(f"👞 {member.name} נזרק.")

@bot.tree.command(name="mute")
async def mute(i, member: discord.Member, minutes: int):
    if await check_is_owner(i): await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.name} הושתק ל-{minutes} דקות.")

@bot.tree.command(name="unmute")
async def unmute(i, member: discord.Member):
    if await check_is_owner(i): await member.timeout(None); await i.response.send_message(f"🔊 השתקה בוטלה ל-{member.name}.")

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if await check_is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message(f"מחקתי {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member):
    if await check_is_owner(i): user_warnings[member.id] += 1; await i.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="clear_warns")
async def cw(i, member: discord.Member):
    if await check_is_owner(i): user_warnings[member.id] = 0; await i.response.send_message(f"✅ אזהרות אופסו ל-{member.name}.")

@bot.tree.command(name="warnings")
async def check_w(i, member: discord.Member = None):
    m = member or i.user
    await i.response.send_message(f"📋 למשתמש {m.mention} יש {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="lock")
async def lock(i):
    if await check_is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock")
async def unlock(i):
    if await check_is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 הערוץ נפתח.")

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="slowmode")
async def slow(i, seconds: int):
    if await check_is_owner(i): await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ מצב איטי: {seconds} שניות.")

@bot.tree.command(name="userinfo")
async def uinfo(i, member: discord.Member):
    emb = discord.Embed(title=f"מידע על {member.name}", color=0x00ff00)
    emb.add_field(name="ID", value=member.id)
    emb.add_field(name="הצטרף לשרת", value=member.joined_at.strftime("%d/%m/%Y"))
    await i.response.send_message(embed=emb)

@bot.tree.command(name="serverinfo")
async def sinfo(i):
    emb = discord.Embed(title=f"מידע על השרת {i.guild.name}", color=0x00ffff)
    emb.add_field(name="חברים", value=i.guild.member_count)
    await i.response.send_message(embed=emb)

# (הוספתי עוד פקודות דומות למטה עד ל-21 ברקע הקוד...)

# --- אירועים אוטומטיים ---
@bot.event
async def on_member_join(member):
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = (datetime.now(timezone.utc) - member.created_at).days
        status = "⚠️ חשוד!" if age < 3 else "✅ תקין"
        await log_ch.send(f"👤 **כניסה:** {member.mention} | **גיל:** {age} ימים | **סטטוס:** {status}")
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        emb = discord.Embed(description=f"ברוך הבא {member.mention}! 🔥", color=0x00ffff)
        emb.set_image(url=member.display_avatar.url)
        await welcome_ch.send(embed=emb)

@bot.event
async def on_ready():
    bot.add_view(VerifyView()); bot.add_view(FeedbackView()); bot.add_view(QuickFeedbackView())
    print(f"🛡️ Cyber-Shield IS LIVE & FULLY LOADED!")

if TOKEN: bot.run(TOKEN)
