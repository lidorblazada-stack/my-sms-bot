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
    print(f'🛡️ Cyber-Shield Pro is ready for action!')

# בדיקת רול Owner
def is_owner():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name="Owner")
        if role: return True
        await ctx.send("🚫 **גישה חסומה!** רק משתמש עם רול 👑 **Owner** יכול לבצע זאת.", delete_after=5)
        return False
    return commands.check(predicate)

# --- הגנה אוטומטית ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    owner_role = discord.utils.get(message.author.roles, name="Owner")
    if owner_role:
        await bot.process_commands(message)
        return

    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, פרסום קישורים אסור! 🛑", delete_after=4)
        return

    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"🤐 {message.author.mention}, שמור על השפה! 👊", delete_after=4)
            return

    await bot.process_commands(message)

# --- מערכת כניסה מעוצבת עם תמונה ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(
            description=f"🎊 **ברוך הבאה לשרת ספאמר הכי טוב בארץ!** 🔥",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Cyber-Shield Protection 🛡️")
        await channel.send(content=f"👋 **שלום {member.mention}, תהנה מהשרת!**", embed=embed)

# --- פקודות ניהול (Owner Only) ---

@bot.command()
@is_owner()
async def mute(ctx, member: discord.Member):
    """משתיק משתמש עם הרול הכולל אימוג'י"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇")
    owner_role = discord.utils.get(ctx.guild.roles, name="Owner")
    
    if muted_role:
        await member.add_roles(muted_role)
        await ctx.send(f"🔇 המשתמש {member.mention} הושתק על ידי {owner_role.mention if owner_role else 'ה-Owner'} 👑")
    else:
        await ctx.send("❌ **שגיאה:** לא מצאתי רול בשם `Muted 🔇`. תוודא שיצרת אותו בדיוק ככה!")

@bot.command()
@is_owner()
async def unmute(ctx, member: discord.Member):
    """מסיר השתקה"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 ההשתקה של {member.mention} הוסרה! אפשר לחזור לדבר. ✅")

@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason="ללא סיבה"):
    owner_role = discord.utils.get(ctx.guild.roles, name="Owner")
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **באן בוצע!** על ידי {owner_role.mention if owner_role else 'ה-Owner'} 👑")

@bot.command()
@is_owner()
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 הצ'אט נוקה על ידי 👑 **ה-Owner**.", delete_after=5)

# --- פקודות קהילה ---

@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    channel = bot.get_channel(REPORT_CH)
    embed = discord.Embed(title="🚨 דיווח חדש!", color=discord.Color.red())
    embed.add_field(name="חשוד:", value=member.mention)
    embed.add_field(name="סיבה:", value=f"**{reason}**")
    await channel.send(embed=embed)
    await ctx.message.delete()

@bot.command()
async def recommend(ctx, *, text):
    channel = bot.get_channel(REC_CH)
    embed = discord.Embed(title="💎 המלצה זהב", description=f"**{text}**", color=discord.Color.gold())
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    await channel.send(embed=embed)
    await ctx.message.delete()

TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)
