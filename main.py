import discord
from discord import app_commands
from discord.ext import commands
import os
import re

# הגדרות בסיסיות
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # סנכרון פקודות הסלאש
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

# IDs של הערוצים שלך
WELCOME_CH = 1501713652217282591
REPORT_CH = 1501946934779449505
REC_CH = 1501947249658429470

BAD_WORDS = ["זונה", "שרמוטה", "מניאק", "קוקסינל", "בן זונה", "בת זונה", "נאצי", "הומו", "זין"]

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Cyber-Shield Ultra 🛡️"))
    print(f'Bot is live: {bot.user}')

# --- מערכת הגנה אוטומטית (Owner חסין) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    owner_role = discord.utils.get(message.author.roles, name="Owner")
    if owner_role: return

    if re.search(r'(https?://[^\s]+)', message.content) or any(word in message.content.lower() for word in BAD_WORDS):
        await message.delete()
        return

# --- פקודות סלאש לאדמינים בלבד (Owner) ---

@bot.tree.command(name="mute", description="השתקת משתמש (אדמין בלבד)")
@app_commands.checks.has_role("Owner")
async def mute(interaction: discord.Interaction, member: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.add_roles(muted_role)
        await interaction.response.send_message(f"🔇 {member.mention} הושתק על ידי ה-Owner!")
    else:
        await interaction.response.send_message("לא מצאתי רול בשם 'Muted 🔇'", ephemeral=True)

@bot.tree.command(name="unmute", description="ביטול השתקה (אדמין בלבד)")
@app_commands.checks.has_role("Owner")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted 🔇")
    if muted_role:
        await member.remove_roles(muted_role)
        await interaction.response.send_message(f"🔊 ההשתקה של {member.mention} הוסרה.")

@bot.tree.command(name="clear", description="ניקוי הודעות (אדמין בלבד)")
@app_commands.checks.has_role("Owner")
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.checks.has_role("Owner")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    # פקודת אזהרה כמו בתמונה שלך
    await interaction.response.send_message(f"⚠️ אזהרה נשלחה ל-{member.mention}: {reason}")

# --- פקודות סלאש לכולם ---

@bot.tree.command(name="report", description="דווח על משתמש לצוות")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    channel = bot.get_channel(REPORT_CH)
    embed = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red())
    embed.add_field(name="חשוד:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    await channel.send(embed=embed)
    await interaction.response.send_message("הדיווח הועבר לטיפול, תודה!", ephemeral=True)

@bot.tree.command(name="suggest", description="שלח המלצה לשרת")
async def suggest(interaction: discord.Interaction, text: str):
    channel = bot.get_channel(REC_CH)
    embed = discord.Embed(title="💎 המלצה", description=text, color=discord.Color.gold())
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
    await channel.send(embed=embed)
    await interaction.response.send_message("ההמלצה פורסמה!", ephemeral=True)

bot.run(os.getenv('BOT_TOKEN'))
