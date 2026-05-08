import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import os
import re
from collections import defaultdict

# --- הגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1499510962296721568 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"] 

# מאגרי נתונים בזיכרון (יציב ומהיר)
user_warnings = defaultdict(int)
message_counts = defaultdict(list)
nuke_monitoring = defaultdict(list)

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ כל פקודות הסלאש סונכרנו!")

bot = CyberShield()

# בדיקת צוות ניהול (Owner)
def is_owner():
    async def predicate(interaction: discord.Interaction):
        is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if is_owner_role or interaction.user.id == interaction.guild.owner_id:
            return True
        await interaction.response.send_message("❌ אין לך הרשאות 'Owner' לביצוע פקודה זו!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- פקודות סלאש (Slash Commands) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש (5 אזהרות = קיק)")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    
    if count >= 5:
        await member.kick(reason="צבר 5 אזהרות")
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת (צבר 5 אזהרות).")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר! ({count}/5). סיבה: {reason}")

@bot.tree.command(name="warnings", description="בדיקת מצב האזהרות של משתמש")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    count = user_warnings[target.id]
    await interaction.response.send_message(f"📋 למשתמש {target.mention} יש **{count}/5** אזהרות.")

@bot.tree.command(name="clear", description="מחיקת הודעות מהצ'אט (עד 100)")
@is_owner()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=min(amount, 100))
    await interaction.followup.send(f"🧹 נמחקו {len(deleted)} הודעות.")

@bot.tree.command(name="mute", description="השתקת משתמש לזמן מוגבל (דקות)")
@is_owner()
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    until = timedelta(minutes=minutes)
    await member.timeout(until)
    await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

# --- הגנות אוטומטיות ולוגים ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # בדיקה אם המשתמש הוא צוות (Owner) - להם מותר הכל
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # 1. אנטי-ספאם (יותר מ-5 הודעות ב-3 שניות)
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now - t).total_seconds() < 3]
        
        if len(message_counts[message.author.id]) > 5:
            try:
                await message.author.timeout(timedelta(minutes=10))
                await message.channel.send(f"🔇 {message.author.mention} הושתקת ל-10 דקות עקב ספאם!")
            except: pass
            return

        # 2. סינון מילים אסורות וקישורים
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
        embed.add_field(name="משתמש:", value=message.author.mention)
        embed.add_field(name="תוכן:", value=message.content or "תמונה/קובץ")
        embed.set_footer(text=f"בערוץ: {message.channel.name}")
        await log_ch.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    # הגנת Anti-Nuke (מחיקת ערוצים)
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
            if log: await log.send(f"🚨 **ניסיון פריצה:** {member.mention} ניסה למחוק ערוצים וכל הרולים שלו הוסרו!")

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield באוויר! מחובר בתור: {bot.user}')

if TOKEN:
    bot.run(TOKEN)
