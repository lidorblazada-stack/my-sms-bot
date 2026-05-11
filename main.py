import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות IDs (תחליף במידת הצורך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
OWNER_ROLE_ID = 1501983948111352091 # רול אונר
MUTE_ROLE_ID = 1501953906736103535  # רול מיוט
SECURITY_LOG_ID = 1502014872655888554 # לוגים כלליים
ATTEMPT_LOG_CH_ID = 1503496964732354620 # ערוץ דיווח ניסיונות של לא-אונרים
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

# הגדרות מערכת
user_warnings = defaultdict(int)
verbal_warned = set() 
OWNER_FOOTER = "Developed by Lidor Owner 👑"

# --- Views ---

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: 
            await i.user.add_roles(role)
            await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        await i.message.delete()
        await self.member.kick(); await i.response.send_message("הועף", ephemeral=True)
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep(self, i, b):
        await i.message.delete()
        await i.response.send_message("אושר", ephemeral=True)

# --- Bot Core ---

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- Helpers ---

async def log_attempt(i, action_type):
    ch = i.guild.get_channel(ATTEMPT_LOG_CH_ID)
    if ch:
        emb = discord.Embed(title="🚨 ניסיון פריצה למערכת", color=0xff0000)
        emb.add_field(name="משתמש", value=f"{i.user.mention} ({i.user.id})", inline=False)
        emb.add_field(name="ניסה להשתמש ב:", value=f"`/{i.command.name}`", inline=True)
        emb.add_field(name="ענישה", value=action_type, inline=True)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    if i.user.id not in verbal_warned:
        verbal_warned.add(i.user.id)
        await i.response.send_message(f"🚫 {i.user.mention}, זו אזהרה מילולית! אין לך הרשאת אונר.", ephemeral=True)
        await log_attempt(i, "אזהרה מילולית")
    else:
        user_warnings[i.user.id] += 1
        await i.response.send_message("❌ אזהרה רשמית נרשמה עקב ניסיון נוסף.", ephemeral=True)
        await log_attempt(i, f"אזהרה רשמית (סה''כ: {user_warnings[i.user.id]})")
    return False

# --- 20 הפקודות הכי חשובות ---

@bot.tree.command(name="nuke", description="מחיקה ובנייה מחדש של הערוץ")
async def nuke(i):
    if await check_owner(i):
        await i.response.defer(ephemeral=True)
        new_ch = await i.channel.clone()
        await i.channel.delete()
        await new_ch.send(f"🚀 הערוץ נוקה על ידי האונר!")

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות")
async def s_v(i):
    if await check_owner(i):
        emb = discord.Embed(title="🛡️ אימות כניסה", description="לחץ על הכפתור למטה כדי להיכנס לשרת", color=0x2ecc71)
        emb.set_footer(text=OWNER_FOOTER)
        await i.channel.send(embed=emb, view=VerifyView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה")
async def warn(i, member: discord.Member, reason: str):
    if await check_owner(i):
        user_warnings[member.id] += 1
        count = user_warnings[member.id]
        if count == 3:
            r = i.guild.get_role(MUTE_ROLE_ID)
            if r: await member.add_roles(r)
        if count >= 5:
            await member.kick(reason="5 אזהרות")
        await i.response.send_message(f"✅ אזהרה נרשמה ל-{member.name} ({count})")

@bot.tree.command(name="clear_warns", description="איפוס אזהרות")
async def c_warns(i, member: discord.Member):
    if await check_owner(i):
        user_warnings[member.id] = 0
        await i.response.send_message("✅ אופס")

@bot.tree.command(name="mute", description="השתקת משתמש")
async def mute(i, member: discord.Member):
    if await check_owner(i):
        r = i.guild.get_role(MUTE_ROLE_ID)
        await member.add_roles(r); await i.response.send_message("🔇 הושתק")

@bot.tree.command(name="unmute", description="ביטול השתקה")
async def unmute(i, member: discord.Member):
    if await check_owner(i):
        r = i.guild.get_role(MUTE_ROLE_ID)
        await member.remove_roles(r); await i.response.send_message("🔊 שוחרר")

@bot.tree.command(name="ban", description="באן לצמיתות")
async def ban(i, member: discord.Member, reason: str = "ללא"):
    if await check_owner(i):
        await member.ban(reason=reason); await i.response.send_message("🚫 נחסם")

@bot.tree.command(name="kick", description="העפה מהשרת")
async def kick(i, member: discord.Member):
    if await check_owner(i):
        await member.kick(); await i.response.send_message("👢 הועף")

@bot.tree.command(name="clear", description="מחיקת הודעות")
async def clear(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message("🧹 נוקה", ephemeral=True)

@bot.tree.command(name="lock", description="נעילת ערוץ")
async def lock(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="פתיחת ערוץ")
async def unlock(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="slowmode", description="מצב איטי")
async def slow(i, seconds: int):
    if await check_owner(i):
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="userinfo", description="מידע על משתמש")
async def u_info(i, member: discord.Member):
    emb = discord.Embed(title=member.name, color=0x3498db)
    emb.add_field(name="אזהרות", value=user_warnings[member.id])
    emb.set_footer(text=OWNER_FOOTER)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="avatar", description="תמונת פרופיל")
async def av(i, member: discord.Member = None):
    m = member or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="add_role", description="מתן רול")
async def a_role(i, member: discord.Member, role: discord.Role):
    if await check_owner(i):
        await member.add_roles(role); await i.response.send_message("✅")

@bot.tree.command(name="remove_role", description="הסרת רול")
async def r_role(i, member: discord.Member, role: discord.Role):
    if await check_owner(i):
        await member.remove_roles(role); await i.response.send_message("❌")

@bot.tree.command(name="nickname", description="שינוי כינוי")
async def nick(i, member: discord.Member, name: str):
    if await check_owner(i):
        await member.edit(nick=name); await i.response.send_message("✅")

@bot.tree.command(name="say", description="הבוט מדבר")
async def say(i, text: str):
    if await check_owner(i):
        await i.channel.send(text); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="serverinfo", description="מידע על השרת")
async def si(i):
    emb = discord.Embed(title=i.guild.name, description=f"חברים: {i.guild.member_count}", color=0x3498db)
    emb.set_footer(text=OWNER_FOOTER)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="ping", description="בדיקת לאגים")
async def ping(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# --- Events ---

@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(title="🔥 ברוך הבא לשרת ספאמר הכי טוב בארץ 🔥", description=f"שלום {member.mention}, אתה מספר **{member.guild.member_count}**.\n\nעם אתה מתקשה פתח טיקט לעזרה ונדבר", color=0xff4500)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(content=f"{member.mention}", embed=emb)
    
    if (datetime.now(timezone.utc) - member.created_at).days < 7:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log:
            emb = discord.Embed(title="🚨 אלט זוהה", description=f"משתמש חשוד: {member.mention}", color=0xffa500)
            await log.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_ready():
    print(f"🛡️ CyberShield Final Version | Developed by Lidor Owner")

if TOKEN:
    bot.run(TOKEN)
