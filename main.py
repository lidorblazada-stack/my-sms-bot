import discord
from discord import app_commands
from discord.ext import commands
import os
import re

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # סנכרון פקודות הסלאש מול דיסקורד
        await self.tree.sync()
        print(f"Slash commands synced for {self.user}")

bot = MyBot()

# IDs של הערוצים שלך
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין"]

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Cyber-Shield Ultra 🛡️"))
    print(f'Cyber-Shield is LIVE!')

# פונקציית בדיקה: האם למשתמש יש רול בשם Owner
def is_owner_check():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name="Owner")
        if role:
            return True
        await interaction.response.send_message("🚫 פקודה זו מיועדת ל-**Owner** בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- הגנה אוטומטית (חסינות לבעלי רול Owner) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # אם למשתמש יש רול Owner, הבוט לא בודק אותו
    owner_role = discord.utils.get(message.author.roles, name="Owner")
    if owner_role:
        await bot.process_commands(message)
        return

    # מחיקת קישורים וקללות
    if re.search(r'(https?://[^\s]+)', message.content) or any(word in message.content.lower() for word in BAD_WORDS):
        await message.delete()
        return

    await bot.process_commands(message)

# --- מערכת כניסה עם תמונה ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH)
    if channel:
        embed = discord.Embed(description=f"ברוך הבאה לשרת ספאמר הכי טוב בארץ! 🔥", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=f"אהלן {member.mention}!", embed=embed)

# --- פקודות סלאש לאדמינים בלבד ---

@bot.tree.command(name="mute", description="השתקת משתמש")
@is_owner_check()
async def mute(interaction: discord.Interaction, member: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.add_roles(muted_role)
        await interaction.response.send_message(f"🔇 המשתמש {member.mention} הושתק!")
    else:
        await interaction.response.send_message("שגיאה: לא מצאתי רול בשם `Muted 🔇`", ephemeral=True)

@bot.tree.command(name="unmute", description="ביטול השתקה")
@is_owner_check()
async def unmute(interaction: discord.Interaction, member: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.remove_roles(muted_role)
        await interaction.response.send_message(f"🔊 ההשתקה של {member.mention} הוסרה.")

@bot.tree.command(name="clear", description="ניקוי הודעות")
@is_owner_check()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@is_owner_check()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.send_message(f"⚠️ אזהרה ל-{member.mention}: {reason}")

# --- פקודות לכולם ---

@bot.tree.command(name="report", description="דווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    channel = bot.get_channel(REPORT_CH)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red())
        embed.add_field(name="חשוד:", value=member.mention)
        embed.add_field(name="סיבה:", value=reason)
        await channel.send(embed=embed)
        await interaction.response.send_message("הדיווח הועבר לטיפול.", ephemeral=True)

bot.run(os.getenv('BOT_TOKEN'))
