import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 # ה-ID שביקשת לדיווחים
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int) 
feedback_cooldowns = {}

# --- פונקציית אבטחה לאונר ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה:", value=f"/{interaction.command.name}", inline=False)
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    if abuse_attempts[interaction.user.id] == 1:
        await interaction.response.send_message("❌ **אזהרה ראשונה!** פקודה ל-OWNER בלבד. ניסיון נוסף = אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[interaction.user.id] += 1
        await interaction.response.send_message(f"⚠️ **קיבלת אזהרה!** אל תיגע בפקודות OWNER. ({user_warnings[interaction.user.id]}/5)", ephemeral=True)
    return False

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        # כאן הוספתי את האימות והפקודות
        await self.tree.sync()

bot = CyberShield()

# (כאן מגיעות כל 20 הפקודות ששמנו מקודם - clear, mute, ban, וכו')

# --- מערכת זיהוי חשבונות חשודים וסטטוס כניסה ---
@bot.event
async def on_member_join(member):
    # 1. דיווח אבטחה לאיי-די שלך
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        account_age = datetime.now(timezone.utc) - member.created_at
        is_suspicious = account_age.days < 3 # חשבון בן פחות מ-3 ימים נחשב חשוד
        
        status_color = 0xff0000 if is_suspicious else 0x00ff00
        status_text = "⚠️ חשבון חשוד (חדש מאוד!)" if is_suspicious else "✅ חשבון תקין"
        
        embed = discord.Embed(title="👤 כניסת משתמש חדש - סטטוס", color=status_color, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="משתמש:", value=f"{member.mention} ({member.name})", inline=False)
        embed.add_field(name="ID:", value=f"`{member.id}`", inline=False)
        embed.add_field(name="נוצר לפני:", value=f"{account_age.days} ימים", inline=True)
        embed.add_field(name="סטטוס:", value=status_text, inline=True)
        await log_ch.send(embed=embed)

    # 2. הודעת וולקם בערוץ הרגיל
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        welcome_embed = discord.Embed(description="**ברוך הבא לשרת ספאמר הכי טוב בארץ! 🔥**", color=0x00ffff)
        welcome_embed.set_image(url=member.display_avatar.url)
        welcome_embed.set_footer(text=f"חבר מספר {member.guild.member_count}")
        await welcome_ch.send(content=f"אהלן {member.mention} !", embed=welcome_embed)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield Secure & Guard Online!')

if TOKEN: bot.run(TOKEN)
