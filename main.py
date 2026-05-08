import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
from collections import defaultdict

# --- הגדרות IDs (מעודכן ומדויק לפי ההיסטוריה שלנו) ---
TOKEN = os.getenv('DISCORD_TOKEN')
SECURITY_LOG_ID = 1499510962296721568  # דיווח על ניסיונות גישה ופריצה
FEEDBACK_CH_ID = 1502028905253699735   # ערוץ פידבקים (💎)
SUGGESTIONS_CH_ID = 1501947249658429470 # ערוץ המלצות (💡)
REPORTS_CH_ID = 1501946934779449505    # ערוץ דיווחים (🚨)
VERIFY_ROLE_ID = 123456789012345678    # כאן שים את ה-ID של הרול "Verified"

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]

# מאגרי נתונים בזיכרון (מהיר, יציב, לא דורש קבצים חיצוניים)
user_warnings = defaultdict(int)
message_counts = defaultdict(list)
nuke_monitoring = defaultdict(list)

# --- פונקציית אבטחה מרכזית: Owner Only + Reporting ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    # בודק אם למשתמש יש רול בשם "Owner" או שהוא בעל השרת
    is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
    if is_owner_role or interaction.user.id == interaction.guild.owner_id:
        return True
    
    # אם מישהו אחר מנסה - שולח דיווח מיידי ללוג האבטחה
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה לפקודת ניהול", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention} ({interaction.user.id})")
        embed.add_field(name="הפקודה שניסה להריץ:", value=f"/{interaction.command.name}")
        embed.set_footer(text="Cyber-Shield Security")
        await log_ch.send(embed=embed)
    
    await interaction.response.send_message("❌ פקודה זו מוגבלת לצוות בלבד.", ephemeral=True)
    return False

# --- מערכות אינטראקציה (Modals & Views) ---

class FeedbackModal(ui.Modal, title='שליחת פידבק לשיפור השרת'):
    msg = ui.TextInput(label='מה תרצה לומר לנו?', style=discord.TextStyle.long, required=True, min_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            embed = discord.Embed(title="💎 פידבק חדש", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await ch.send(embed=embed)
            await interaction.response.send_message("תודה! הפידבק שלך נשלח.", ephemeral=True)

class SuggestionModal(ui.Modal, title='המלצה חדשה לשרת'):
    msg = ui.TextInput(label='תאר את ההמלצה שלך', style=discord.TextStyle.long, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
        if ch:
            embed = discord.Embed(title="💡 המלצה חדשה", description=self.msg.value, color=0xf1c40f, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await ch.send(embed=embed)
            await interaction.response.send_message("ההמלצה נשלחה בהצלחה!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='לחץ כאן לאימות כניסה ✅', style=discord.ButtonStyle.green, custom_id='persistent:v_btn')
    async def v_btn(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("ברוך הבא! עברת את האימות.", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה: רול לא מוגדר.", ephemeral=True)

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(VerifyView()) # מבטיח שהכפתור יעבוד תמיד
        await self.tree.sync()

bot = CyberShield()

# --- פקודות סלאש (Owner Only) ---

@bot.tree.command(name="setup_verify", description="הצבת הודעת אימות (Owner Only)")
async def setup_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="🛡️ מערכת אימות", description="לחץ על הכפתור כדי לקבל גישה לשרת.", color=0x2ecc71)
        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message("המערכת הוקמה.", ephemeral=True)

@bot.tree.command(name="clear", description="ניקוי הודעות (Owner Only)")
async def clear(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=min(amount, 100))
        await interaction.followup.send(f"נמחקו {len(deleted)} הודעות.")

@bot.tree.command(name="warn", description="מתן אזהרה (Owner Only)")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        count = user_warnings[member.id]
        if count >= 5:
            await member.kick(reason="צבר 5 אזהרות")
            user_warnings[member.id] = 0
            await interaction.response.send_message(f"👢 {member.mention} הועף (5 אזהרות).")
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({count}/5).")

# --- פקודות משתמש (פתוח לכולם) ---

@bot.tree.command(name="feedback", description="שליחת פידבק")
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal())

@bot.tree.command(name="suggest", description="שליחת המלצה")
async def suggest(interaction: discord.Interaction):
    await interaction.response.send_modal(SuggestionModal())

@bot.tree.command(name="report", description="דיווח על משתמש")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="מדווח:", value=interaction.user.mention)
        embed.add_field(name="נדווח:", value=member.mention)
        embed.add_field(name="סיבה:", value=reason)
        await ch.send(embed=embed)
        await interaction.response.send_message("הדיווח התקבל.", ephemeral=True)

# --- הגנות אוטומטיות (Anti-Nuke, Anti-Spam) ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    if not is_staff:
        # אנטי-ספאם וסינון מילים
        if any(w in message.content for w in BAD_WORDS):
            await message.delete()
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now-t).total_seconds() < 3]
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10))
    await bot.process_commands(message)

@bot.event
async def on_guild_channel_delete(channel):
    # הגנת Anti-Nuke
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.user.id == channel.guild.owner_id: return
        user_id = entry.user.id
        now = datetime.now()
        nuke_monitoring[user_id].append(now)
        if len(nuke_monitoring[user_id]) >= 2:
            member = await channel.guild.fetch_member(user_id)
            for role in member.roles:
                try: await member.remove_roles(role)
                except: continue
            log = bot.get_channel(SECURITY_LOG_ID)
            if log: await log.send(f"🚨 **מצב חירום:** {member.mention} ניסה למחוק ערוצים והושבת!")

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield סופי ומוכן! הכל מאובטח.')

if TOKEN: bot.run(TOKEN)
