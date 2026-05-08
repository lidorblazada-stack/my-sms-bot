import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות מה-Railway שלך ---
TOKEN = os.getenv('DISCORD_TOKEN') # משתמש בטוקן שראיתי בתמונה ב-Railway
SECURITY_LOG_ID = 1499510962296721568  # לוג ניסיונות פריצה
FEEDBACK_CH_ID = 1502028905253699735   # ערוץ פידבק
SUGGESTIONS_CH_ID = 1501947249658429470 # ערוץ המלצות
REPORTS_CH_ID = 1501946934779449505    # ערוץ דיווחים

# !!! שים לב אחי: תכתוב כאן את ה-ID של הרול שאתה נותן ב-Verify !!!
VERIFY_ROLE_ID = 123456789012345678 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)

# --- בדיקת Owner מקיפה ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
    if is_owner_role or interaction.user.id == interaction.guild.owner_id:
        return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000)
        embed.add_field(name="משתמש", value=interaction.user.mention)
        embed.add_field(name="פקודה", value=f"/{interaction.command.name}")
        await log_ch.send(embed=embed)
    
    await interaction.response.send_message("❌ פקודה זו מוגבלת לצוות בלבד.", ephemeral=True)
    return False

# --- מערכות אינטראקציה (Verify & Feedback) ---

class FeedbackModal(ui.Modal, title='💎 שליחת פידבק'):
    fb = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long, required=True, min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            embed = discord.Embed(title="💎 פידבק חדש", description=self.fb.value, color=0x3498db)
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await ch.send(embed=embed)
            await interaction.response.send_message("תודה! נשלח.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='לחץ כאן לאימות ✅', style=discord.ButtonStyle.green, custom_id='v_btn_ultimate')
    async def v(self, interaction: discord.Interaction, btn: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה!", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה: ה-ID של הרול בקוד לא תקין.", ephemeral=True)

# --- הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- 10+ הפקודות שלנו ---

@bot.tree.command(name="setup_verify", description="Owner: הקמת אימות")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.send("🛡️ לחץ לאימות:", view=VerifyView())
        await interaction.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="Owner: הקמת פאנל פידבק")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        view = ui.View(timeout=None)
        btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="f_btn")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal())
        view.add_item(btn)
        await interaction.channel.send("💎 **פאנל פידבקים:**", view=view)
        await interaction.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="clear", description="Owner: ניקוי צ'אט")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="Owner: השתקה")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="kick", description="Owner: העפה")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick()
        await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="Owner: חסימה")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="warn", description="Owner: מתן אזהרה")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def wrs(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 {m.mention} עם {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="report", description="דיווח על משתמש")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        await ch.send(f"🚨 **דיווח מ-{interaction.user.mention}** נגד {member.mention}: {reason}")
        await interaction.response.send_message("הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="suggest", description="המלצה לשרת")
async def sg(interaction: discord.Interaction, msg: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        await ch.send(f"💡 **המלצה:** {msg}")
        await interaction.response.send_message("תודה!", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(w in message.content for w in BAD_WORDS):
        await message.delete()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} ONLINE!')

if TOKEN: bot.run(TOKEN)
