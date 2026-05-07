import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import os

# --- הגדרות מערכת ---
# הבוט מושך את הטוקן מה-Secrets של GitHub (DISCORD_TOKEN)
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_NAME = "Owner"
LOG_CHANNEL_ID = 1499510962296721568  # ה-ID שביקשת לדיווחים
WELCOME_CHANNEL_ID = 123456789012345678 # שנה ל-ID של ערוץ הוולקם שלך
SUGGESTIONS_CHANNEL_ID = 123456789012345678 # שנה ל-ID של ערוץ ההמלצות
VERIFY_ROLE_ID = 123456789012345678 # שנה ל-ID של הרול שניתן באימות

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="לחץ כאן לאימות ✅", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role in interaction.user.roles:
            await interaction.response.send_message("אתה כבר מאומת אחי! 🛡️", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה! ברוך הבא לשרת הכי חזק במדינה! 🔥", ephemeral=True)

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.warnings = {} # מעקב אזהרות

    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()
        print(f"🛡️ Cyber-Shield V-FINAL באוויר ומוכן להגנה!")

bot = CyberShield()

# --- בדיקת רול אונר (רק מי שעם רול Owner) ---
def is_owner_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(role.name == OWNER_ROLE_NAME for role in interaction.user.roles):
            return True
        await interaction.response.send_message(f"👑 פקודה זו נעולה! רק למשתמשים עם רול **{OWNER_ROLE_NAME}** יש גישה.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- אירועים: Welcome & Auto-Mod ---
@bot.event
async def on_member_join(member):
    ch = bot.get_channel(WELCOME_CHANNEL_ID)
    if ch:
        embed = discord.Embed(
            title=f"👋 ברוך הבא ל-{member.guild.name}!", 
            description=f"אהלן {member.mention}, הגעת ל**שרת הכי חזק במדינה!** 🔥", 
            color=0x00d4ff
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Cyber-Shield Security")
        await ch.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    msg_content = message.content.lower()
    
    # 1. חסימת לינקים והזמנות לשרתים אחרים
    if re.search(r'http[s]?://|discord.gg/', msg_content):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            return await message.channel.send(f"🛡️ {message.author.mention}, אין לשלוח קישורים בשרת!", delete_after=3)

    # 2. תשובות אוטומטיות (Auto-Responder)
    if "איך קונים" in msg_content or "לקנות" in msg_content:
        await message.reply("אהלן אחי! כדי לקנות קרידיטים פשוט תפתח טיקט בערוץ המתאים. 💳")
    
    await bot.process_commands(message)

# --- פקודות אדמין (רק לרול Owner) ---
@bot.tree.command(name="setup_verify", description="🛠️ הקמת מערכת אימות בשרת")
@is_owner_role()
async def setup_verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔐 מערכת אימות - Verification",
        description="כדי לקבל גישה לשאר הערוצים בשרת, עליך ללחוץ על הכפתור למטה.",
        color=0x00ff00
    )
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("מערכת האימות הוקמה בהצלחה!", ephemeral=True)

@bot.tree.command(name="shutdown", description="🔌 כיבוי הבוט מרחוק")
@is_owner_role()
async def shutdown(interaction: discord.Interaction):
    await interaction.response.send_message("הבוט נכבה בפקודת האונר. להתראות! 👋", ephemeral=True)
    await bot.close()

# --- פקודות ניהול (Moderation) ---
@bot.tree.command(name="warn", description="⚠️ מתן אזהרה למשתמש")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צויין"):
    uid = str(member.id)
    bot.warnings[uid] = bot.warnings.get(uid, 0) + 1
    count = bot.warnings[uid]
    
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    await interaction.response.send_message(f"⚠️ {member.mention} הוזהר! ({count}/5). סיבה: {reason}")
    
    if log_ch:
        await log_ch.send(f"🚨 **דיווח אזהרה:** {member.name} הוזהר על ידי {interaction.user.name}. סיבה: {reason}")

    if count == 3:
        await member.timeout(datetime.timedelta(minutes=10), reason="צבר 3 אזהרות")
        await interaction.channel.send(f"🔇 {member.mention} הושתק ל-10 דקות בגלל צבירת 3 אזהרות.")
    elif count >= 5:
        await member.kick(reason="צבר 5 אזהרות")
        await interaction.channel.send(f"👞 {member.mention} הועף מהשרת בגלל צבירת 5 אזהרות.")

@bot.tree.command(name="clear", description="🧹 מחיקת הודעות בצ'אט")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"ניקיתי {len(deleted)} הודעות. ✨", ephemeral=True)

# --- פקודות קהילה ---
@bot.tree.command(name="suggest", description="💡 שלח הצעה לשיפור השרת")
async def suggest(interaction: discord.Interaction, suggestion: str):
    ch = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if ch:
        embed = discord.Embed(title="💡 הצעה חדשה", description=suggestion, color=0xffaa00)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        msg = await ch.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await interaction.response.send_message("ההצעה שלך נשלחה לבדיקה! תודה אחי. 🙏", ephemeral=True)

@bot.tree.command(name="report", description="🚨 דווח על משתמש בעייתי")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(title="🚨 דיווח משתמש", color=0xff0000)
        embed.add_field(name="המשתמש המדווח", value=member.mention)
        embed.add_field(name="דיווח על ידי", value=interaction.user.mention)
        embed.add_field(name="סיבה", value=reason)
        await log_ch.send(embed=embed)
        await interaction.response.send_message("הדיווח התקבל ויועבר לטיפול האדמינים. 🚓", ephemeral=True)

@bot.tree.command(name="help", description="📜 מציג את כל הפקודות של הבוט")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ תפריט העזרה של Cyber-Shield", color=0x00d4ff)
    embed.add_field(name="👑 אדמין (Owner Only)", value="`/setup_verify`, `/shutdown`", inline=False)
    embed.add_field(name="🛠️ ניהול שרת", value="`/warn`, `/clear`, `/mute`", inline=False)
    embed.add_field(name="👥 קהילה", value="`/suggest`, `/report`", inline=False)
    embed.set_footer(text="השרת הכי חזק במדינה 🔥")
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
