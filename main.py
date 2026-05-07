import discord
import os
import re
from discord.ext import commands

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
    print(f'🛡️ Cyber-Shield Pro is online and guarding the castle!')

# בדיקה אם המשתמש הוא Owner
def is_owner():
    async def predicate(ctx):
        # מחפש את רול ה-Owner בדיוק כפי שמופיע בשרת
        role = discord.utils.get(ctx.author.roles, name="Owner")
        if role: return True
        await ctx.send("🚫 **עצור!** רק ה-👑 **Owner** רשאי להשתמש בפקודה זו.", delete_after=5)
        return False
    return commands.check(predicate)

# --- הגנה אוטומטית (חסינות ל-Owner) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    owner_role = discord.utils.get(message.author.roles, name="Owner")
    if owner_role:
        await bot.process_commands(message)
        return

    if re.search(r'(https?://[^\s]+)', message.content):
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, פרסום קישורים אסור! 🛑", delete_after=3)
        return

    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"🤐 {message.author.mention}, שמור על השפה! 👊", delete_after=3)
            return
    await bot.process_commands(message)

# --- מערכת כניסה מעוצבת ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(description=f"🎊 **ברוך הבאה לשרת ספאמר הכי טוב בארץ!** 🔥", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Cyber-Shield Protection 🛡️")
        await channel.send(content=f"👋 **אהלן {member.mention}!**", embed=embed)

# --- פקודות ניהול (Owner Only) ---

@bot.command()
@is_owner()
async def mute(ctx, member: discord.Member):
    # כאן השם מעודכן לפי התמונה ששלחת: "Muted 🔇"
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇") 
    owner_role = discord.utils.get(ctx.guild.roles, name="Owner")
    
    if muted_role:
        await member.add_roles(muted_role)
        await ctx.send(f"🔇 המשתמש {member.mention} הושתק על ידי {owner_role.mention if owner_role else 'ה-Owner'} 👑")
    else:
        await ctx.send("❌ **שגיאה:** לא מצאתי רול בשם `Muted 🔇`. תוודא שהשם זהה ב-100%.")

@bot.command()
@is_owner()
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 {member.mention}, ההשתקה הוסרה! ✅")

@bot.command()
@is_owner()
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 הצ'אט נוקה על ידי 👑 **Owner**.", delete_after=5)

TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)
