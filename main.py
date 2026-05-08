import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID מעודכנות ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 # ה-ID החדש שנתת
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
# מעקב אחרי ניסיונות פריצה לפקודות אונר
abuse_attempts = defaultdict(int) 
feedback_cooldowns = {}

# --- פונקציית אבטחה משופרת ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    # בדיקה אם למשתמש יש רול Owner או שהוא בעל השרת
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    
    if is_owner:
        return True
    
    # 🚨 דיווח ללוג אבטחה
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה (OWNER ONLY)", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה שנוסתה:", value=f"/{interaction.command.name}", inline=False)
        embed.set_footer(text="מערכת הגנה Cyber-Shield")
        await log_ch.send(embed=embed)
    
    # ⚠️ מערכת אזהרות למשתמש
    abuse_attempts[interaction.user.id] += 1
    attempt_count = abuse_attempts[interaction.user.id]
    
    if attempt_count == 1:
        await interaction.response.send_message("❌ **ניסיון פריצה זוהה!** אם תנסה שוב פעם אחת תקבל אזהרה רשמית.", ephemeral=True)
    else:
        # פעם שנייה ומעלה - נותן אזהרה רשמית במערכת
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **קיבלת אזהרה!** ניסיונות חוזרים להשתמש בפקודות OWNER אסורים. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    
    return False

# (המשך הקוד עם ה-Modals וה-Views נשאר אותו דבר...)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='אימות כניסה ✅', style=discord.ButtonStyle.green, custom_id='v_fixed_final')
    async def v_callback(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("ברוך הבא!", ephemeral=True)

class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(VerifyView()); await self.tree.sync()

bot = CyberShield()

# --- פקודות עם תיאור מעודכן (OWNER בלבד) ---

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות (OWNER בלבד)")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.send("🛡️ **אזור אימות:**", view=VerifyView())
        await interaction.response.send_message("פאנל הוקם.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק (OWNER בלבד)")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        # (הקוד של הפידבק נשאר כאן...)
        await interaction.response.send_message("פאנל פידבק הוקם.", ephemeral=True)

@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="השתקת משתמש (OWNER בלבד)")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="ban", description="חסימת משתמש (OWNER בלבד)")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

# (כך גם עבור kick, lock, unlock, slowmode, clear_warns - כולם עם OWNER בלבד בתיאור)

# --- אירוע Welcome מתוקן (תמונת פרופיל בלבד) ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        embed = discord.Embed(description="**ברוך הבא לשרת ספאמר הכי טוב בארץ! 🔥**", color=0x00ffff)
        # מציג את תמונת הפרופיל של הבן אדם שנכנס
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"חבר מספר {member.guild.member_count}")
        await ch.send(content=f"אהלן {member.mention} !", embed=embed)

@bot.event
async def on_ready(): print(f'🛡️ Cyber-Shield Secure Online!')

if TOKEN: bot.run(TOKEN)
