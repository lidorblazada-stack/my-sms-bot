import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import os
import re
from collections import defaultdict

# --- הגדרות (וודא שהן תואמות ל-Railway) ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1499510962296721568 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"] 

# --- משתני מערכת בזיכרון (יציב ללא פיירבייס) ---
user_warnings = defaultdict(int)
message_counts = defaultdict(list)
nuke_monitoring = defaultdict(list)
join_monitoring = []

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        # סנכרון פקודות הסלאש (/)
        await self.tree.sync()

bot = CyberShield()

# --- בדיקת הרשאות Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if is_owner_role or interaction.user.id == interaction.guild.owner_id:
            return True
        await interaction.response.send_message("❌ פקודה זו מיועדת לצוות הניהול הגבוה בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- פקודות ניהול ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    
    if count >= 5:
        await member.kick(reason="צבר 5 אזהרות")
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת לאחר שצבר 5 אזהרות.")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר! ({count}/5). סיבה: {reason}")

@bot.tree.command(name="warnings", description="בדיקת כמות אזהרות")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    count = user_warnings[target.id]
    await interaction.response.send_message(f"📋 למשתמש {target.mention} יש **{count}/5** אזהרות.")

@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט")
@is_owner()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=min(amount, 100))
    await interaction.followup.send(f"🧹 ניקיתי {len(deleted)} הודעות בהצלחה.")

@bot.tree.command(name="mute", description="השתקת משתמש לזמן מוגבל")
@is_owner()
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    until = timedelta(minutes=minutes)
    await member.timeout(until)
    await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

# --- אירועים והגנות אוטומטיות ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # 1. אנטי-ספאם
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now - t).total_seconds() < 3]
        
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10))
            await message.channel.send(f"🔇 {message.author.mention}, הפסק להספים! הושתקת ל-10 דקות.")
            return

        # 2. סינון קללות וקישורים
        if any(word in message.content for word in BAD_WORDS) or re.search(r'(https?://\S+|discord\.gg/\S+)', message.content):
            await message.delete()
            return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(title="🗑️ הודעה נמחקה", color=0xe74c3c, timestamp=datetime.now())
        embed.add_field(name="כותב:", value=message.author.mention)
        embed.add_field(name="תוכן:", value=message.content or "קובץ/תמונה")
        embed.set_footer(text=f"ערוץ: {message.channel.name}")
        await log_ch.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    # הגנת Anti-Nuke: מזהה מחיקת ערוצים מהירה
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.user.id == channel.guild.owner_id: return
        
        user_id = entry.user.id
        now = datetime.now()
        nuke_monitoring[user_id].append(now)
        nuke_monitoring[user_id] = [t for t in nuke_monitoring[user_id] if (now-t).total_seconds() < 60]
        
        if len(nuke_monitoring[user_id]) >= 2:
            member = await channel.guild.fetch_member(user_id)
            for role in member.roles:
                try: await member.remove_roles(role)
                except: continue
            log = bot.get_channel(LOG_CHANNEL_ID)
            if log: await log.send(f"🚨 **מצב חירום:** הוסרו הרולים ל-{member.mention} כי הוא ניסה למחוק ערוצים!")

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield הופעל בהצלחה: {bot.user}')

if TOKEN: bot.run(TOKEN)
