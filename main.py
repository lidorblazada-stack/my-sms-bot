import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1502014872655888554  
FEEDBACK_CH_ID = 1502028905253699735   
REPORTS_CH_ID = 1501946934779449505    
SUGGESTIONS_CH_ID = 1501947249658429470 
WELCOME_CH_ID = 1501713652217282591
LEAVE_CH_ID = 1501713652217282591 # ערוץ הפרידה (כמו בתמונה)
VERIFY_ROLE_ID = 1501983948111352091 
SUSPECT_ROLE_ID = 1503464176599695380  

ALT_MIN_DAYS = 7
BAD_WORDS = ["זונה", "מזיין", "נאצי", "כושלאמא"]
user_warnings = defaultdict(int)
feedback_cooldowns = {}

# --- Views & Modals (הבסיס הישן שלך) ---

class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="מה תרצה להגיד?", style=discord.TextStyle.paragraph, required=True)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        last = feedback_cooldowns.get(interaction.user.id)
        if last and (now - last).seconds < 300:
            return await interaction.response.send_message("⏳ חכה 5 דקות.", ephemeral=True)

        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anon.value.strip() == "כן"
            name = "Anonymous User 👤" if is_anon else interaction.user.name
            icon = "https://cdn.discordapp.com/embed/avatars/0.png" if is_anon else interaction.user.display_avatar.url
            emb = discord.Embed(title="📝 פידבק חדש", description=self.msg.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            emb.set_author(name=name, icon_url=icon)
            await ch.send(embed=emb, view=QuickFeedbackView())
            feedback_cooldowns[interaction.user.id] = now
            await interaction.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.blurple, custom_id="main_fb")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())

class QuickFeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 🌟", style=discord.ButtonStyle.gray, custom_id="quick_fb")
    async def q_fb(self, i, b): await i.response.send_modal(FeedbackModal())

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="פתח פנייה 🎫", style=discord.ButtonStyle.gray, custom_id="open_t")
    async def open_t(self, i, b):
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(read_messages=False), i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        await i.response.send_message(f"✅ פנייה נפתחה: {channel.mention}", ephemeral=True)

class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        await self.member.kick(); await i.response.send_message("הועף", ephemeral=True)
        await i.message.edit(view=None)
    @ui.button(label="חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def s(self, i, b):
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        await self.member.add_roles(r); await i.response.send_message("סומן כחשוד", ephemeral=True)
        await i.message.edit(view=None)

# --- Bot Setup ---

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.add_view(FeedbackView())
        self.add_view(QuickFeedbackView())
        self.add_view(TicketView())
        await self.tree.sync()

bot = CyberShield()

# --- Helpers ---

async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    log = guild.get_channel(SECURITY_LOG_ID)
    if log:
        emb = discord.Embed(title="⚠️ אזהרה", description=f"{member.mention} קיבל אזהרה שביעית: {count}\nסיבה: {reason}", color=0xffa500)
        await log.send(embed=emb)
    if count == 3: await member.timeout(timedelta(hours=24), reason="3 Warnings")
    elif count >= 5: await member.kick(reason="5 Warnings")

async def check_is_owner(i: discord.Interaction) -> bool:
    if i.user.id == i.guild.owner_id or any(role.name.lower() == "owner" for role in i.user.roles):
        return True
    await i.response.send_message("❌ פקודה זו ל-OWNER בלבד!", ephemeral=True)
    return False

# --- פקודות (מעל 20 פונקציות) ---

@bot.tree.command(name="nuke", description="ניקוי ערוץ אטומי")
async def nuke(i: discord.Interaction):
    if await check_is_owner(i):
        await i.response.defer(ephemeral=True) # פותר את בעיית ה-did not respond
        pos = i.channel.position
        new = await i.channel.clone()
        await i.channel.delete()
        await new.edit(position=pos)
        await new.send("🚀 הערוץ עבר ניקוי אטומי!")

@bot.tree.command(name="setup_all", description="הקמת כל הפאנלים")
async def setup_all(i: discord.Interaction):
    if await check_is_owner(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView())
        await i.channel.send(embed=discord.Embed(title="🎫 טיקטים", color=0x3498db), view=TicketView())
        await i.channel.send(embed=discord.Embed(title="🌟 פידבק", color=0x9b59b6), view=FeedbackView())
        await i.response.send_message("הכל הוקם!", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה")
async def warn(i, member: discord.Member, reason: str):
    if i.user.guild_permissions.manage_messages:
        await add_warning(member, reason, i.guild)
        await i.response.send_message("✅ נרשם", ephemeral=True)

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if await check_is_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="report")
async def report(i, reason: str):
    ch = i.guild.get_channel(REPORTS_CH_ID)
    emb = discord.Embed(title="🚨 דיווח", description=reason, color=0xff0000)
    emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
    await ch.send(embed=emb); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="userinfo")
async def uinfo(i, member: discord.Member):
    emb = discord.Embed(title=member.name, color=member.color)
    emb.add_field(name="ID", value=member.id)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="ping")
async def ping(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# --- Events ---

@bot.event
async def on_member_join(member):
    # הודעת כניסה
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(title=f"⚡ {member.name} הצטרף לשרת", description=f"מספר **{member.guild.member_count}** שהצטרף אלינו.", color=0x2ecc71)
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text=f"CyberIL | {datetime.now().strftime('%H:%M')}")
        await ch.send(content=f"{member.mention}", embed=emb)
    
    # Alt Detector
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS or member.avatar is None:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log: await log.send(f"🚨 חשוד: {member.mention}", view=AltActionView(member))

@bot.event
async def on_member_remove(member):
    # הודעת עזיבה (בידיוק כמו בתמונה ששלחת)
    ch = member.guild.get_channel(LEAVE_CH_ID)
    if ch:
        emb = discord.Embed(description=f"😢 **{member.name}** עזב את השרת.\nנשארנו **{member.guild.member_count}** חברים.", color=0xff4747)
        emb.set_footer(text=f"{datetime.now().strftime('%H:%M')}")
        await ch.send(embed=emb)

@bot.event
async def on_message(message):
    if message.author.bot: return
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            await add_warning(message.author, "מילים אסורות", message.guild)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"🛡️ {bot.user.name} ONLINE - ALL COMMANDS LOADED")

if TOKEN: bot.run(TOKEN)
