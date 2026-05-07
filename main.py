import discord
import os
import re
from discord.ext import commands

# הגדרות
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs של הערוצים
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין"]

@bot.event
async def on_ready():
    print(f'Cyber-Shield is Online. Restricted to Owner role!')

# פונקציית עזר לבדיקת רול Owner
def is_owner():
    async def predicate(ctx):
        # בודק אם יש למשתמש רול שקוראים לו בדיוק Owner
        role = discord.utils.get(ctx.author.roles, name="Owner")
        if role:
            return True
        await ctx.send("❌ פקודה זו מיועדת רק למשתמשים עם רול **Owner**!", delete_after=5)
        return False
    return commands.check(predicate)

# --- הגנה מפני קישורים וקללות ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # אם המשתמש הוא Owner, הוא חסין מהכל
    is_user_owner = discord.utils.get(message.author.roles, name="Owner")
    if is_user_owner:
        await bot.process_commands(message)
        return

    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, אסור לשלוח קישורים! ❌", delete_after=5)
        return

    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, שמור על השפה! 🤐", delete_after=5)
            return

    await bot.process_commands(message)

# --- מערכת כניסה ועזיבה ---
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

# --- פקודות ניהול מוגבלות לרול Owner בלבד ---

@bot.command()
@is_owner() # הגבלה לרול Owner
async def ban(ctx, member: discord.Member, *, reason="ללא סיבה"):
    await member.ban(reason=reason)
    await ctx.send(f"המשתמש **{member.name}** קיבל באן מה-Owner! 🔨")

@bot.command()
@is_owner()
async def unban(ctx, *, member_id: int):
    user = await bot.fetch_user(member_id)
    await ctx.guild.unban(user)
    await ctx.send(f"הבאן של **{user.name}** הוסר על ידי ה-Owner! ✅")

# פקודות אזהרות (מבוסס על התמונה ששלחת)
@bot.command()
@is_owner()
async def warn(ctx, member: discord.Member, *, reason="אזהרה מההנהלה"):
    # כאן אפשר להוסיף לוגיקה של Firebase לשמירת אזהרות
    await ctx.send(f"⚠️ {member.mention}, קיבלת אזהרה מה-Owner!\nסיבה: {reason}")

@bot.command()
async def report(ctx, member: discord.Member, *, reason="ללא סיבה"):
    channel = bot.get_channel(REPORT_CH)
    if channel:
        embed = discord.Embed(title="דיווח חדש! ⚠️", color=discord.Color.red())
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

TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)
