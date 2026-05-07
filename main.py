import discord
import os
import re
import asyncio
from discord.ext import commands

# הגדרות בוט בסיסיות
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs של הערוצים בשרת שלך
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

# רשימת מילים אסורות (Blacklist)
BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין", "כוסאמא"]

@bot.event
async def on_ready():
    # משנה את הסטטוס של הבוט שייראה מקצועי
    await bot.change_presence(activity=discord.Game(name="Guarding Spam-Server 🔥"))
    print(f'--- Cyber-Shield Ultra is Online ---')

# פונקציית הגנה: בודק אם המשתמש הוא Owner
def is_owner():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name="Owner")
        if role: return True
        await ctx.send("❌ פקודה זו זמינה ל-**Owner** בלבד!", delete_after=5)
        return False
    return commands.check(predicate)

# --- מערכת הגנה אוטומטית (Anti-Spam & Filter) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # חסינות ל-Owner: אתה יכול לשלוח מה שבא לך
    owner_role = discord.utils.get(message.author.roles, name="Owner")
    if owner_role:
        await bot.process_commands(message)
        return

    # חסימת קישורים אוטומטית
    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, אסור לשלוח קישורים בשרת! 🛑", delete_after=4)
        return

    # סינון קללות
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, שמור על שפה נקייה! 🤐", delete_after=4)
            return

    await bot.process_commands(message)

# --- מערכת כניסה מעוצבת (Welcome) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(
            description=f"ברוך הבאה לשרת ספאמר הכי טוב בארץ! 🔥",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"משתמש מספר {len(member.guild.members)}")
        await channel.send(content=f"אהלן {member.mention}!", embed=embed)

# --- פקודות ניהול (Owner Only) ---

@bot.command()
@is_owner()
async def mute(ctx, member: discord.Member):
    """משתיק משתמש באמצעות הרול המוגדר"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇")
    owner_role = discord.utils.get(ctx.guild.roles, name="Owner")
    if muted_role:
        await member.add_roles(muted_role)
        await ctx.send(f"המשתמש {member.mention} הושתק על ידי {owner_role.mention if owner_role else 'Owner'}")
    else:
        await ctx.send("שגיאה: לא נמצא רול בשם `Muted 🔇`")

@bot.command()
@is_owner()
async def unmute(ctx, member: discord.Member):
    """מסיר השתקה"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.remove_roles(muted_role)
        await ctx.send(f"ההשתקה של {member.mention} הוסרה.")

@bot.command()
@is_owner()
async def clear(ctx, amount: int = 10):
    """מנקה כמות הודעות מהצ'אט"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"ניקיתי {amount} הודעות לבקשת ה-Owner. ✨", delete_after=3)

@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason="הפרת חוקי השרת"):
    """חוסם משתמש לצמיתות"""
    await member.ban(reason=reason)
    await ctx.send(f"המשתמש {member.name} נחסם מהשרת! 🔨")

# --- מערכת דיווחים והמלצות ---

@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    """שולח דיווח לערוץ הסטאף"""
    channel = bot.get_channel(REPORT_CH)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red())
        embed.add_field(name="חשוד:", value=member.mention)
        embed.add_field(name="סיבה:", value=reason)
        embed.set_footer(text=f"דווח על ידי {ctx.author.name}")
        await channel.send(embed=embed)
        await ctx.message.delete()
        await ctx.send(f"{ctx.author.mention}, הדיווח שלך נשלח לבדיקה.", delete_after=5)

@bot.command()
async def recommend(ctx, *, text):
    """שולח המלצה לערוץ ההמלצות"""
    channel = bot.get_channel(REC_CH)
    if channel:
        embed = discord.Embed(title="💎 המלצה חדשה", description=text, color=discord.Color.gold())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.message.delete()

# הרצה דרך GitHub Secrets
TOKEN = os.getenv('BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
