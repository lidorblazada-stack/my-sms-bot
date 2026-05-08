import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 # ה-ID החדש לדיווחים
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int) 
feedback_cooldowns = {}

# --- פונקציית אבטחה חכמה ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    
    if is_owner:
        return True
    
    # דיווח ללוג אבטחה על הניסיון
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה שנוסתה:", value=f"/{interaction.command.name}", inline=False)
        await log_ch.send(embed=embed)
    
    # מערכת אזהרות אוטומטית
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **זהירות!** פקודה זו ל-OWNER בלבד. ניסיון נוסף יגרור אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **קיבלת אזהרה!** אל תנסה להשתמש בפקודות לא שלך. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    
    return False

# --- מודאל פידבק ---
class FeedbackModal(ui.Modal, title='💎 שליחת פידבק'):
    fb_text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='אנונימי? (כן/לא)', default='לא', max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = time.time()
        if user_id in feedback_cooldowns and now - feedback_cooldowns[user_id] < 300:
            rem = int(300 - (now - feedback_cooldowns[user_id]))
            await interaction.response.send_message(f"⏳ חכה {rem // 60} דקות נוספות לפני הפידבק הבא.", ephemeral=True)
            return
        
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anonymous.value.strip() == "כן"
            author = "אנונימי" if is_anon else interaction.user.name
            embed = discord.Embed(title="💎 פידבק חדש", description=self.fb_text.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"מאת: {author}")
            await ch.send(embed=embed)
            feedback_cooldowns[user_id] = now
            await interaction.response.send_message("✅ תודה על הפידבק!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='אימות כניסה ✅', style=discord.ButtonStyle.green, custom_id='v_final_secure')
    async def v_callback(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה!", ephemeral=True)

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות ניהול (OWNER בלבד) ---

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות למשתמשים (OWNER בלבד)")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.send("🛡️ **לחצו לאימות:**", view=VerifyView())
        await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק אנונימי (OWNER בלבד)")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        view = ui.View(timeout=None)
        btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="fb_btn_final")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal())
        view.add_item(btn)
        await interaction.channel.send("💎 **פידבקים לשיפור השרת:**", view=view)
        await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="clear", description="ניקוי הודעות מהערוץ (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="השתקת משתמש לזמן מסוים (OWNER בלבד)")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="unmute", description="ביטול השתקה למשתמש (OWNER בלבד)")
async def umt(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 {member.mention} חזר לדבר.")

@bot.tree.command(name="kick", description="הוצאת משתמש מהשרת (OWNER בלבד)")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick()
        await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="חסימת משתמש מהשרת (OWNER בלבד)")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="warn", description="מתן אזהרה רשמית למשתמש (OWNER בלבד)")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="clear_warns", description="איפוס כל האזהרות של משתמש (OWNER בלבד)")
async def cwr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"✅ האזהרות של {member.mention} אופסו.")

@bot.tree.command(name="lock", description="נעילת הערוץ לכתיבה (OWNER בלבד)")
async def lock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock", description="פתיחת הערוץ לכתיבה (OWNER בלבד)")
async def unlock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("🔓 הערוץ נפתח.")

@bot.tree.command(name="slowmode", description="הגדרת מצב איטי לערוץ (OWNER בלבד)")
async def slow(interaction: discord.Interaction, seconds: int):
    if await check_is_owner(interaction):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"⏳ סלואו-מוד: {seconds} שניות.")

# --- פקודות כלליות (לכולם) ---

@bot.tree.command(name="report", description="דיווח על משתמש שעבר על החוקים")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c)
        embed.add_field(name="מדווח:", value=interaction.user.mention)
        embed.add_field(name="נדווח:", value=member.mention)
        embed.add_field(name="סיבה:", value=reason)
        await ch.send(embed=embed)
        await interaction.response.send_message("הדיווח נשלח לצוות.", ephemeral=True)

@bot.tree.command(name="suggest", description="שליחת הצעה לשיפור השרת")
async def sg(interaction: discord.Interaction, text: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 הצעה חדשה", description=text, color=0xf1c40f)
        embed.set_author(name=interaction.user.name)
        await ch.send(embed=embed)
        await interaction.response.send_message("ההצעה התקבלה!", ephemeral=True)

@bot.tree.command(name="warnings", description="בדיקת כמות האזהרות שלך או של משתמש אחר")
async def wrs(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 ל-{m.mention} יש {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="avatar", description="מציג את תמונת הפרופיל בגדול")
async def av(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="בדיקת הדיליי של הבוט")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms")

# --- אירוע Welcome (תמונת פרופיל גדולה ונקייה) ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        embed = discord.Embed(description="**ברוך הבא לשרת ספאמר הכי טוב בארץ! 🔥**", color=0x00ffff)
        # מציג את תמונת הפרופיל של הבן אדם שנכנס בגדול
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"חבר מספר {member.guild.member_count}")
        await ch.send(content=f"אהלן {member.mention} !", embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(w in message.content for w in BAD_WORDS): await message.delete()
    await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'🛡️ Cyber-Shield Final Grandmaster Online!')

if TOKEN: bot.run(TOKEN)
