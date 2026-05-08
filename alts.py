import discord
from discord.ext import commands
from datetime import datetime, timezone
import os

# --- הגדרות מעודכנות ---
TOKEN = os.getenv('TOKEN')
LOG_CHANNEL_ID = 1502014872655888554  # ה-ID החדש שלך
MIN_AGE_DAYS = 7 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'🕵️ Cyber-Alt-Detector is scanning for threats!')
    # הגדרת סטטוס מגניב לבוט
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for Alt Accounts"))

@bot.event
async def on_member_join(member):
    now = datetime.now(timezone.utc)
    diff = now - member.created_at
    
    reasons = []
    is_suspicious = False
    
    # בדיקה 1: גיל החשבון
    if diff.days < MIN_AGE_DAYS:
        is_suspicious = True
        reasons.append(f"• חשבון חדש (נוצר לפני {diff.days} ימים)")
    
    # בדיקה 2: תמונת פרופיל דיפולטיבית
    if member.avatar is None:
        is_suspicious = True
        reasons.append("• אין תמונת פרופיל (Default Avatar)")

    # שליחת לוג רק אם המשתמש חשוד
    if is_suspicious:
        log_ch = bot.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            embed = discord.Embed(
                title="🚨 התראת חשד למשתמש אלט",
                description=f"המשתמש {member.mention} הצטרף לשרת ונראה חשוד.",
                color=0xff4b2b, # צבע אדום חזק
                timestamp=now
            )
            
            embed.add_field(name="👤 שם משתמש", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="🆔 מזהה (ID)", value=member.id, inline=True)
            embed.add_field(name="📅 תאריך יצירה", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=False)
            embed.add_field(name="🚩 סיבות לחשד", value="\n".join(reasons), inline=False)
            
            # הוספת תמונת המשתמש בפינה
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Cyber-Alt-Detector System", icon_url=bot.user.display_avatar.url)
            
            await log_ch.send(embed=embed)

@bot.tree.command(name="check", description="🔍 בדיקת גיל חשבון של משתמש באופן ידני")
async def check(interaction: discord.Interaction, member: discord.Member):
    diff = datetime.now(timezone.utc) - member.created_at
    
    embed = discord.Embed(title=f"בדיקת משתמש: {member.name}", color=0x3498db)
    embed.add_field(name="גיל חשבון", value=f"{diff.days} ימים", inline=True)
    embed.add_field(name="תאריך הצטרפות לדיסקורד", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    
    status = "🔴 חשוד מאוד" if diff.days < MIN_AGE_DAYS else "🟢 נראה בטוח"
    embed.add_field(name="סטטוס", value=status, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
