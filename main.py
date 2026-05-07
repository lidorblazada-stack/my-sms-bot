import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import os

# --- הגדרות IDs סופיות ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_NAME = "Owner"
VERIFY_ROLE_ID = 1501983185909579937
WELCOME_CHANNEL_ID = 1501713652217282591
REPORT_CHANNEL_ID = 1499510962296721568
SUGGESTIONS_CHANNEL_ID = 1501946934779449505

# --- רשימת מילים אסורות (תוסיף מה שבא לך) ---
BAD_WORDS = ["בן זונה", "שרמוטה", "מניאק", "קוקסינל", "נאצי", "זונה"]

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="לחץ כאן לאימות ✅", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role is None:
            return await interaction.response.send_message("❌ שגיאה: רול האימות לא נמצא!", ephemeral=True)
            
        try:
            if role in interaction.user.roles:
                await interaction.response.send_message("אתה כבר מאומת אחי! 🛡️", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("אומתת בהצלחה! ברוך הבא למבצר של Cyber-Shield! 🔥", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ אין לי סמכות! תעלה את הרול 'Cyber-Shield-App' לראש הרשימה בשרת!", ephemeral=True)

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.warnings = {}

    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()
        print("🛡️ Cyber-Shield ULTIMATE FINAL is Online!")

bot = CyberShield()

# בדיקת אונר
def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(role.name == OWNER_ROLE_NAME for role in interaction.user.roles):
            return True
        await interaction.response.send_message("👑 פקודה זו נעולה לאונר בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- ניהול אזהרות אוטומטי ---
async def add_warning(member, reason, channel):
    uid = str(member.id)
    bot.warnings[uid] = bot.warnings.get(uid, 0) + 1
    count = bot.warnings[uid]
    
    embed = discord.Embed(title="⚠️ אזהרה אוטומטית", color=0xff0000)
    embed.add_field(name="משתמש", value=member.mention)
    embed.add_field(name="סיבה", value=reason)
    embed.add_field(name="מצב אזהרות", value=f"{count}/5")
    await channel.send(embed=embed)

    if count == 3:
        await member.timeout(datetime.timedelta(minutes=30), reason="צבירת 3 אזהרות")
        await channel.send(f"🔇 {member.mention} הושתק ל-30 דקות (3 אזהרות).")
    elif count >= 5:
        await member.kick(reason="צבירת 5 אזהרות")
        await channel.send(f"👞 {member.mention} הועף מהשרת (5 אזהרות)!")

# --- הגנה אקטיבית (קללות ולינקים) ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # 1. בדיקת קללות
    if any(word in message.content.lower() for word in BAD_WORDS):
        await message.delete()
        await message.channel.send(f"🚫 {message.author.mention}, שמור על השפה שלך!", delete_after=3)
        await add_warning(message.author, "שימוש בשפה אסורה", message.channel)
        return

    # 2. בדיקת לינקים
    if re.search(r'http[s]?://|discord.gg/', message.content.lower()):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(f"🛡️ {message.author.mention}, בלי לינקים בשרת!", delete_after=3)
            await add_warning(message.author, "שליחת לינקים ללא רשות", message.channel)
            return

    await bot.process_commands(message)

# --- פקודות מערכת ---
@bot.tree.command(name="setup_verify", description="🛠️ הקמת אימות (אונר)")
@is_owner()
async def setup_verify(interaction: discord.Interaction):
    embed = discord.Embed(title="🔐 אימות כניסה - Cyber-Shield", description="לחץ על הכפתור למטה כדי להיכנס למבצר.", color=0x2f3136)
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("הוקם!", ephemeral=True)

@bot.tree.command(name="report", description="🚨 דווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    log_ch = bot.get_channel(REPORT_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000)
        embed.add_field(name="חשוד", value=member.mention)
        embed.add_field(name="סיבה", value=reason)
        await log_ch.send(embed=embed)
        await interaction.response.send_message("הדיווח הועבר לטיפול! 🚓", ephemeral=True)

@bot.tree.command(name="suggest", description="💡 שלח המלצה")
async def suggest(interaction: discord.Interaction, idea: str):
    sug_ch = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if sug_ch:
        embed = discord.Embed(title="💡 המלצה חדשה", description=idea, color=0xffff00)
        msg = await sug_ch.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await interaction.response.send_message("תודה על ההמלצה!", ephemeral=True)

@bot.tree.command(name="clear", description="🧹 ניקוי הודעות")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"ניקיתי {amount} הודעות. ✨", ephemeral=True)

bot.run(TOKEN)
