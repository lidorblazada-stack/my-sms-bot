import discord
import os
import re
from discord.ext import commands

# הגדרות דיסקורד
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs של הערוצים שלך
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

# רשימת מילים אסורות
BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין"]

@bot.event
async def on_ready():
    print(f'Cyber-Shield IS LIVE! Guarding the server.')

# בדיקה אם המשתמש הוא Owner
def is_owner():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name="Owner")
        if role: return True
        await ctx.send("❌ רק ה-**Owner** יכול להשתמש בזה!", delete_after=5)
        return False
    return commands.check(predicate)

# --- הגנה אוטומטית ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # חריגה ל-Owner
    is_user_owner = discord.utils.get(message.author.roles, name="Owner")
    if is_user_owner:
        await bot.process_commands(message)
        return

    # חסימת קישורים
    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, קישורים אסורים! ❌", delete_after=3)
        return

    # חסימת קללות
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, שמור על שפה נקייה! 🤐", delete_after=3)
            return

    await bot.process_commands(message)

# --- מערכת כניסה עם תמונת משתמש ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(
            description=f"ברוך הבאה לשרת ספאמר הכי טוב בארץ! 🔥",
            color=discord.Color.blue()
        )
        # כאן הקסם: מושך את התמונה של המשתמש שנכנס
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=f"ברוך הבא {member.mention}!", embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(title="👋 להתראות", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=f"המשתמש {member.name} עזב אותנו..", embed=embed)

# --- פקודות ניהול (Owner Only) ---

@bot.command()
@is_owner()
async def clear(ctx, amount: int):
    """מנקה הודעות בצ'אט"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"ניקיתי {amount} הודעות! 🧹", delete_after=5)

@bot.command()
@is_owner()
async def kick(ctx, member: discord.Member, *, reason="ללא סיבה"):
    await member.kick(reason=reason)
    await ctx.send(f"המשתמש {member.name} נזרק מהשרת! 👞")

@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason="ללא סיבה"):
    await member.ban(reason=reason)
    await ctx.send(f"המשתמש {member.name} קיבל באן! 🔨")

@bot.command()
@is_owner()
async def mute(ctx, member: discord.Member):
    """משתיק משתמש (דורש רול בשם Muted)"""
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.add_roles(role)
    await ctx.send(f"{member.mention} הושתק! 🤐")

# --- מערכת דיווחים והמלצות ---

@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    channel = bot.get_channel(REPORT_CH)
    embed = discord.Embed(title="דיווח חדש! ⚠️", color=discord.Color.red())
    embed.add_field(name="מדווח:", value=ctx.author.mention)
    embed.add_field(name="על המשתמש:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    await channel.send(embed=embed)
    await ctx.message.delete()

@bot.command()
async def recommend(ctx, *, text):
    channel = bot.get_channel(REC_CH)
    embed = discord.Embed(title="המלצה חדשה! ⭐", description=text, color=discord.Color.gold())
    embed.set_footer(text=f"נשלח על ידי: {ctx.author.name}")
    await channel.send(embed=embed)
    await ctx.message.delete()

TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)
