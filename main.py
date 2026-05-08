import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import time
from collections import defaultdict

# --- הגדרות ID (תוודא שהן נכונות ב-Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1499510962296721568 
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)
abuse_attempts = defaultdict(int)

# --- פונקציית בדיקת OWNER ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner: return True
    
    # דיווח על ניסיון פריצה
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000)
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention}")
        embed.add_field(name="פקודה:", value=f"/{interaction.command.name}")
        await log_ch.send(embed=embed)
    
    abuse_attempts[interaction.user.id] += 1
    msg = "❌ פקודה ל-OWNER בלבד!" if abuse_attempts[interaction.user.id] == 1 else "⚠️ אזהרה רשמית נרשמה!"
    if abuse_attempts[interaction.user.id] > 1: user_warnings[interaction.user.id] += 1
    await interaction.response.send_message(msg, ephemeral=True)
    return False

# --- הגדרות הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        await self.tree.sync() # מסנכרן את הפקודות כדי שלא יעלמו

bot = CyberShield()

# --- פקודת בדיקת סטטוס ידנית (למקרה שהאוטומטי לא מספיק) ---
@bot.tree.command(name="check_status", description="בודק אם משתמש הוא חשבון חשוד (OWNER בלבד)")
async def check_status(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        age = datetime.now(timezone.utc) - member.created_at
        status = "⚠️ חשוד (חדש)" if age.days < 3 else "✅ תקין"
        await interaction.response.send_message(f"👤 {member.mention}\n📅 נוצר לפני: {age.days} ימים\nסטטוס: {status}")

# --- 20 פקודות הניהול (דוגמה למבנה, תעתיק את השאר מהקוד הקודם עם התיאור המתאים) ---
@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט (OWNER בלבד)")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"נמחקו {amount} הודעות.")

# (כאן תוודא שכל שאר הפקודות - ban, mute, kick וכו' נמצאות עם התיאור OWNER בלבד)

# --- אירוע כניסה: וולקם + סטטוס אבטחה אוטומטי ---
@bot.event
async def on_member_join(member):
    # 1. שליחת סטטוס ללוג האבטחה (מהבוט הזה!)
    log_ch = member.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        age = datetime.now(timezone.utc) - member.created_at
        color = 0xff0000 if age.days < 3 else 0x00ff00
        embed = discord.Embed(title="👤 כניסת משתמש - בדיקת אבטחה", color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="משתמש:", value=member.mention)
        embed.add_field(name="גיל חשבון:", value=f"{age.days} ימים")
        embed.add_field(name="סטטוס:", value="⚠️ חשבון חדש/חשוד" if age.days < 3 else "✅ תקין")
        await log_ch.send(embed=embed)

    # 2. הודעת וולקם עם תמונת פרופיל גדולה
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        w_embed = discord.Embed(description="**ברוך הבא לשרת! 🔥**", color=0x00ffff)
        w_embed.set_image(url=member.display_avatar.url)
        await welcome_ch.send(content=f"אהלן {member.mention} !", embed=w_embed)

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} Is Ready and Guarding!')

if TOKEN: bot.run(TOKEN)
