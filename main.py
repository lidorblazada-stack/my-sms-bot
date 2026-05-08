import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
from collections import defaultdict

# --- הגדרות משתנים (אל תשכח לעדכן ב-Railway!) ---
TOKEN = os.getenv('ALT_BOT_TOKEN') # לפי התמונה שלך ב-Railway
SECURITY_LOG_ID = 1499510962296721568 
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
VERIFY_ROLE_ID = 123456789012345678  # שים כאן את ה-ID של הרול בשרת שלך

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]

user_warnings = defaultdict(int)
message_counts = defaultdict(list)

# --- בדיקת Owner מקיפה + דיווח ללוג ---
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

# --- מערכות אינטראקציה (Modals & Views) ---

class FeedbackModal(ui.Modal, title='💎 פאנל פידבק'):
    feedback = ui.TextInput(label='שתף אותנו בדעתך', style=discord.TextStyle.long, required=True, min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            embed = discord.Embed(title="💎 פידבק חדש", description=self.feedback.value, color=0x3498db)
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await ch.send(embed=embed)
            await interaction.response.send_message("תודה! הפידבק נשלח.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='לחץ כאן לאימות ✅', style=discord.ButtonStyle.green, custom_id='v_btn_fixed')
    async def v(self, interaction: discord.Interaction, btn: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת!", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה: רול לא מוגדר.", ephemeral=True)

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- רשימת הפקודות המלאה (10+) ---

# 1. הקמת אימות
@bot.tree.command(name="setup_verify", description="Owner Only: הקמת פאנל אימות")
async def setup_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="🛡️ אימות כניסה", description="לחץ למטה כדי להיכנס.", color=0x2ecc71)
        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message("בוצע.", ephemeral=True)

# 2. הקמת פידבק (הפאנל שביקשת)
@bot.tree.command(name="setup_feedback", description="Owner Only: הקמת פאנל פידבק")
async def setup_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="💎 פאנל פידבקים", description="אנחנו מעריכים את דעתכם! לחצו כדי לשלוח פידבק.", color=0x3498db)
        view = ui.View(timeout=None)
        btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="f_btn")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal())
        view.add_item(btn)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("פאנל פידבק הוקם.", ephemeral=True)

# 3. ניקוי צ'אט
@bot.tree.command(name="clear", description="Owner Only: מחיקת הודעות")
async def clear(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=min(amount, 100))
        await interaction.followup.send(f"נמחקו {len(deleted)} הודעות.")

# 4. מתן אזהרה
@bot.tree.command(name="warn", description="Owner Only: מתן אזהרה")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר. ({user_warnings[member.id]}/5)")

# 5. בדיקת אזהרות
@bot.tree.command(name="warnings", description="בדיקת כמות אזהרות")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 ל-{m.mention} יש {user_warnings[m.id]} אזהרות.")

# 6. השתקה (Timeout)
@bot.tree.command(name="mute", description="Owner Only: השתקת משתמש")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

# 7. העפה (Kick)
@bot.tree.command(name="kick", description="Owner Only: העפת משתמש")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    if await check_is_owner(interaction):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת.")

# 8. חסימה (Ban)
@bot.tree.command(name="ban", description="Owner Only: חסימת משתמש")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    if await check_is_owner(interaction):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🚫 {member.mention} נחסם לצמיתות.")

# 9. דיווח (Report)
@bot.tree.command(name="report", description="דיווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c)
        embed.add_field(name="נגד", value=member.mention)
        embed.add_field(name="סיבה", value=reason)
        await ch.send(embed=embed)
        await interaction.response.send_message("דיווחך התקבל.", ephemeral=True)

# 10. המלצה (Suggest)
@bot.tree.command(name="suggest", description="שליחת המלצה לשרת")
async def suggest(interaction: discord.Interaction, suggestion: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0xf1c40f)
        await ch.send(embed=embed)
        await interaction.response.send_message("ההמלצה נשלחה!", ephemeral=True)

# --- אירועים והגנות ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    # אנטי-ספאם וסינון מילים
    if any(w in message.content for w in BAD_WORDS):
        await message.delete()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} ONLINE - ALL COMMANDS LOADED!')

if TOKEN: bot.run(TOKEN)
