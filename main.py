import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import re

# --- הגדרות בוט ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'
LOG_CHANNEL_ID = 1499510962296721568
WELCOME_CHANNEL_ID = 123456789012345678
SUGGESTIONS_CHANNEL_ID = 123456789012345678
STATS_CHANNEL_ID = 123456789012345678 # ערוץ קולי שבו יוצג מספר המשתמשים

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.warnings = {}

    async def setup_hook(self):
        await self.tree.sync()
        self.update_stats.start() # מפעיל את עדכון הסטטיסטיקה
        print(f"✅ Cyber-Shield V-ULTIMATE מוכן לפעולה!")

bot = CyberShield()

# --- פיצ'ר חדש: עדכון סטטיסטיקה אוטומטי ---
@tasks.loop(minutes=10)
async def update_stats():
    channel = bot.get_channel(STATS_CHANNEL_ID)
    if channel:
        guild = channel.guild
        await channel.edit(name=f"👥 משתמשים: {guild.member_count}")

# --- מערכת Welcome & Leave ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=f"👋 ברוך הבא ל-{member.guild.name}!",
            description=f"אהלן {member.mention},\nשמחים שהצטרפת ל**שרת הכי חזק במדינה!** 🔥",
            color=0x00d4ff
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"משתמש מספר {len(member.guild.members)}")
        await channel.send(embed=embed)

# --- הגנה הרמטית (קישורים, הזמנות וקללות) ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # חסימת הזמנות לשרתים אחרים (Anti-Invite)
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            return await message.channel.send(f"🚫 {message.author.mention}, פרסום שרתים אחרים אסור בהחלט!", delete_after=3)

    # חסימת קישורים כלליים
    if re.search(r'http[s]?://', message.content):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            return await message.channel.send(f"🛡️ {message.author.mention}, אין לשלוח קישורים!", delete_after=3)

    await bot.process_commands(message)

# --- פקודות Slash המנצחות ---

@bot.tree.command(name="kick", description="👢 העפת משתמש מהשרת")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צויין"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת. | סיבה: {reason}")

@bot.tree.command(name="ban", description="🔨 חסימת משתמש מהשרת")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צויין"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} נחסם לצמיתות. | סיבה: {reason}")

@bot.tree.command(name="mute", description="🔇 השתקת משתמש")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "לא צויין"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות. 🤐")

@bot.tree.command(name="unmute", description="🔊 ביטול השתקה")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 השתיקה של {member.mention} בוטלה.")

@bot.tree.command(name="clear", description="🧹 ניקוי צ'אט")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 ניקיתי {len(deleted)} הודעות!", ephemeral=True)

@bot.tree.command(name="suggest", description="💡 שלח המלצה")
async def suggest(interaction: discord.Interaction, suggestion: str):
    channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0xffaa00)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await interaction.response.send_message("✅ נשלח!", ephemeral=True)

bot.run(TOKEN)
