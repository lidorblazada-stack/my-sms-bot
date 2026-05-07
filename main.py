import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re

# --- הגדרות שרת (תעדכן את ה-ID שלך) ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'
OWNER_ROLE_NAME = "Owner"
LOG_CHANNEL_ID = 1499510962296721568
WELCOME_CHANNEL_ID = 123456789012345678
SUGGESTIONS_CHANNEL_ID = 123456789012345678
VERIFY_ROLE_ID = 123456789012345678

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
        self.warnings = {}

    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()
        print(f"🛡️ Cyber-Shield V-FINAL באוויר!")

bot = CyberShield()

# בדיקת רול אונר
def is_owner_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(role.name == OWNER_ROLE_NAME for role in interaction.user.roles):
            return True
        await interaction.response.send_message(f"👑 רק למי שיש רול **{OWNER_ROLE_NAME}** מורשה להשתמש בזה!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- אירועים: Welcome & Auto-Mod ---
@bot.event
async def on_member_join(member):
    ch = bot.get_channel(WELCOME_CHANNEL_ID)
    if ch:
        embed = discord.Embed(title=f"👋 ברוך הבא ל-{member.guild.name}!", description=f"אהלן {member.mention}, הגעת ל**שרת הכי חזק במדינה!** 🔥", color=0x00d4ff)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # חסימת לינקים והזמנות
    if re.search(r'http[s]?://|discord.gg/', message.content.lower()):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            return await message.channel.send(f"🛡️ {message.author.mention}, אין לשלוח קישורים בשרת!", delete_after=3)

    await bot.process_commands(message)

# --- פקודות אדמין (Owner Only) ---
@bot.tree.command(name="setup_verify", description="🛠️ הקמת מערכת אימות")
@is_owner_role()
async def setup_verify(interaction: discord.Interaction):
    embed = discord.Embed(title="🔐 אימות משתמשים", description="לחצו על הכפתור למטה כדי לקבל גישה לשרת.", color=0x00ff00)
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("המערכת הוקמה!", ephemeral=True)

# --- פקודות ניהול (Moderation) ---
@bot.tree.command(name="clear", description="🧹 ניקוי צ'אט")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 ניקיתי {len(deleted)} הודעות.", ephemeral=True)

@bot.tree.command(name="warn", description="⚠️ מתן אזהרה")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צויין"):
    uid = str(member.id)
    bot.warnings[uid] = bot.warnings.get(uid, 0) + 1
    count = bot.warnings[uid]
    await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({count}/5). סיבה: {reason}")
    if count == 3: await member.timeout(datetime.timedelta(minutes=10), reason="3 אזהרות")
    elif count >= 5: await member.kick(reason="5 אזהרות")

@bot.tree.command(name="suggest", description="💡 שלח המלצה")
async def suggest(interaction: discord.Interaction, suggestion: str):
    ch = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if ch:
        embed = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0xffaa00)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        msg = await ch.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await interaction.response.send_message("✅ ההמלצה נשלחה!", ephemeral=True)

@bot.tree.command(name="help", description="📜 תפריט עזרה")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ Cyber-Shield Help", description="`/clear`, `/mute`, `/warn`, `/report`, `/suggest`, `/setup_verify`", color=0x00d4ff)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
