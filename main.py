import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
import asyncio
from collections import defaultdict

# --- הגדרות IDs ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1502014872655888554  
FEEDBACK_CH_ID = 1502028905253699735   
REPORTS_CH_ID = 1501946934779449505    
SUGGESTIONS_CH_ID = 1501947249658429470 
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
SUSPECT_ROLE_ID = 1503464176599695380  

ALT_MIN_DAYS = 7
BAD_WORDS = ["זונה", "מזיין", "נאצי", "כושלאמא"]
user_warnings = defaultdict(int) # מערכת אזהרות
message_counts = defaultdict(int) # למניעת ספאם

# --- Views (חייבים להופיע לפני הבוט) ---

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="פתח פנייה 🎫", style=discord.ButtonStyle.gray, custom_id="open_t")
    async def open_t(self, i, b):
        overwrites = {
            i.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        await i.response.send_message(f"✅ נפתח ערוץ: {channel.mention}", ephemeral=True)

class FeedbackModal(ui.Modal, title="שליחת פידבק"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db)
            emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
            await ch.send(embed=emb)
            await i.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="fb_main")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())

class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        await self.member.kick(); await i.response.send_message("הועף", ephemeral=True)
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def s(self, i, b):
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        await self.member.add_roles(r); await i.response.send_message("סומן כחשוד", ephemeral=True)

# --- הגדרות הבוט ---

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        # עכשיו ה-Views כבר קיימים בקוד אז לא תהיה שגיאה
        self.add_view(VerifyView())
        self.add_view(TicketView())
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- מערכת אזהרות אוטומטית ---
async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    log_ch = guild.get_channel(SECURITY_LOG_ID)
    
    if log_ch:
        await log_ch.send(f"⚠️ אזהרה {count} למשתמש {member.mention} | סיבה: {reason}")
    
    if count == 3:
        await member.timeout(timedelta(hours=24), reason="3 Warnings reached")
        if log_ch: await log_ch.send(f"🔇 {member.mention} הושתק ל-24 שעות (3 אזהרות).")
    
    if count >= 5:
        await member.kick(reason="5 Warnings reached")
        if log_ch: await log_ch.send(f"❌ {member.mention} הועף מהשרת (5 אזהרות).")

# --- פקודות ניהול ---

@bot.tree.command(name="warn", description="מתן אזהרה ידנית")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    if i.user.guild_permissions.manage_messages:
        await add_warning(member, reason, i.guild)
        await i.response.send_message(f"✅ אזהרה נרשמה ל-{member.name}.", ephemeral=True)

@bot.tree.command(name="nuke", description="ניקוי ערוץ")
async def nuke(i: discord.Interaction):
    if i.user.id == i.guild.owner_id:
        new = await i.channel.clone()
        await i.channel.delete()
        await new.send("🚀 הערוץ נוקה!")

@bot.tree.command(name="setup_all", description="הקמת כל הפאנלים")
async def setup_all(i: discord.Interaction):
    if i.user.guild_permissions.administrator:
        await i.channel.send("🛡️ **פאנל אימות**", view=VerifyView())
        await i.channel.send("🎫 **מערכת טיקטים**", view=TicketView())
        await i.channel.send("🌟 **פידבקים**", view=FeedbackView())
        await i.response.send_message("הכל הוקם!", ephemeral=True)

# --- אירועים ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    # חסימת מילים גסות + אזהרה
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await add_warning(message.author, "שפה לא נאותה", message.guild)
            return
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS or member.avatar is None:
        ch = member.guild.get_channel(SECURITY_LOG_ID)
        if ch: await ch.send(f"🚨 חשוד נכנס: {member.mention}", view=AltActionView(member))
    
    welcome = member.guild.get_channel(WELCOME_CH_ID)
    if welcome: await welcome.send(f"ברוך הבא {member.mention}! 🔥")

@bot.event
async def on_ready():
    print(f"🛡️ CyberShield PRO MAX ONLINE!")

if TOKEN: bot.run(TOKEN)
