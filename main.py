import discord
import os
import re
from discord.ext import commands

# הגדרות
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs של הערוצים שנתת
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

# רשימת קללות בסיסית
BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין"]

@bot.event
async def on_ready():
    print(f'Cyber-Shield is Online and Ready!')

# --- הגנה מפני קישורים וקללות ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # מנהלים חסינים מהגנות
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    # חסימת קישורים
    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, אסור לשלוח קישורים! ❌", delete_after=5)
        return

    # חסימת קללות
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, שמור על השפה! 🤐", delete_after=5)
            return

    await bot.process_commands(message)

# --- מערכת כניסה (מעוצבת לפי בקשתך) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(
            description=f"ברוך הבאה לשרת ספאמר הכי טוב בארץ! 🔥",
            color=discord.Color.blue()
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await channel.send(content=f"ברוך הבא {member.mention}!", embed=embed)

# --- מערכת עזיבה ---
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(
            title="👋 להתראות",
            description=f"המשתמש **{member.name}** עזב את השרת.",
            color=discord.Color.red()
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await channel.send(content=f"להתראות {member.name}, חבל שעזבת...", embed=embed)

# --- פקודות ניהול (Ban & Unban) ---
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="ללא סיבה"):
    await member.ban(reason=reason)
    await ctx.send(f"המשתמש **{member.name}** קיבל באן! 🔨")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_id: int):
    user = await bot.fetch_user(member_id)
    await ctx.guild.unban(user)
    await ctx.send(f"הבאן של **{user.name}** הוסר! ✅")

# --- פקודות דיווח והמלצות ---
@bot.command()
async def report(ctx, member: discord.Member, *, reason="ללא סיבה"):
    channel = bot.get_channel(REPORT_CH)
    if channel:
        embed = discord.Embed(title="דיווח חדש! ⚠️", color=discord.Color.red())
        embed.add_field(name="דווח על ידי:", value=ctx.author.mention, inline=True)
        embed.add_field(name="המשתמש המדווח:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=reason, inline=False)
        await channel.send(embed=embed)
        await ctx.message.delete()

@bot.command()
async def recommend(ctx, *, text):
    channel = bot.get_channel(REC_CH)
    if channel:
        embed = discord.Embed(title="המלצה חדשה! ⭐", description=text, color=discord.Color.gold())
        embed.set_footer(text=f"נשלח על ידי: {ctx.author.name}")
        await channel.send(embed=embed)
        await ctx.message.delete()

# הרצה (הטוקן נמשך מה-Secrets ב-GitHub)
TOKEN = os.getenv('BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
