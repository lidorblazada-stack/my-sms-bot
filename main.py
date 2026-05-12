import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (לידור/נהוראי NL Owner) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SUSPECT_ROLE_ID = 1501953906736103535 # ה-ID של רול החשוד
SECURITY_LOG_ID = 1502014872655888554 # ערוץ לוגים של פקודות
ATTEMPT_LOG_CH_ID = 1503496964732354620 # ערוץ דיווח פריצות ואלטים
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 

# מערכות מעקב
suspected_list = {} # {user_id: last_msg_time}
OWNER_FOOTER = "Developed by NL Owner 👑"

# --- תפריט אלטים (3 כפתורים) ---
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def check_perm(self, i: discord.Interaction):
        if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
        await i.response.send_message("❌ רק NL Owner יכול לבצע פעולה זו!", ephemeral=True)
        return False

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if await self.check_perm(i):
            await self.member.kick(reason="אלט הועף על ידי אונר"); await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} הועף.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep_alt(self, i, b):
        if await self.check_perm(i):
            await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} אושר.", ephemeral=True)

    @ui.button(label="סמן כחשוד 🕵️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if await self.check_perm(i):
            # מתן רול חשוד
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role: await self.member.add_roles(role)
            # כניסה למערכת מעקב
            suspected_list[self.member.id] = datetime.now(timezone.utc)
            await i.message.delete()
            await i.response.send_message(f"🕵️ {self.member.name} קיבל רול ונכנס למעקב 24 שעות!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: 
            await i.user.add_roles(role)
            await i.response.send_message("אומתת בהצלחה בשרת של NL!", ephemeral=True)

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.check_inactive.start()
        await self.tree.sync()

    @tasks.loop(hours=1)
    async def check_inactive(self):
        now = datetime.now(timezone.utc)
        ch = self.get_channel(ATTEMPT_LOG_CH_ID)
        to_remove = []
        for uid, last_msg in suspected_list.items():
            if now - last_msg > timedelta(hours=24):
                if ch: await ch.send(f"⚠️ **התראת NL:** החשוד <@{uid}> לא שלח הודעה כבר 24 שעות!")
                to_remove.append(uid)
        for uid in to_remove: del suspected_list[uid]

bot = CyberShield()

# --- מערכת אבטחה ולוגים ---
async def log_command(i, status):
    ch = i.guild.get_channel(SECURITY_LOG_ID)
    if ch:
        color = 0x3498db if status == "בוצע" else 0xff0000
        emb = discord.Embed(title=f"🛡️ פקודת NL: {i.command.name}", description=f"סטטוס: {status}\nמבצע: {i.user.mention}", color=color)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb)

async def check_nl_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        await log_command(i, "בוצע"); return True
    await log_command(i, "🚨 ניסיון פריצה!"); await i.response.send_message("🚫 הרשאת NL Owner בלבד!", ephemeral=True)
    return False

# --- 20 פקודות NL Owner ---

@bot.tree.command(name="nuke", description="מחיקה ושחזור הערוץ מחדש")
async def nuke(i):
    if await check_nl_owner(i):
        new = await i.channel.clone(); await i.channel.delete()
        await new.send(f"🚀 הערוץ נוקה על ידי **NL Owner**")

@bot.tree.command(name="lock", description="נעילת הערוץ לכתיבה")
async def lock(i):
    if await check_nl_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 ננעל.")

@bot.tree.command(name="unlock", description="פתיחת הערוץ לכתיבה")
async def unlock(i):
    if await check_nl_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 נפתח.")

@bot.tree.command(name="mute", description="השתקת משתמש (מיוט)")
async def mute(i, member: discord.Member):
    if await check_nl_owner(i):
        await member.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"🔇 {member.name} הושתק.")

@bot.tree.command(name="ban", description="חסימת משתמש מהשרת")
async def ban(i, member: discord.Member):
    if await check_nl_owner(i):
        await member.ban(); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="clear", description="מחיקת הודעות")
async def clear(i, amount: int):
    if await check_nl_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות כניסה")
async def sv(i):
    if await check_nl_owner(i):
        emb = discord.Embed(title="🛡️ אימות NL", description="לחץ למטה כדי להיכנס", color=0x2ecc71)
        emb.set_footer(text=OWNER_FOOTER)
        await i.channel.send(embed=emb, view=VerifyView()); await i.response.send_message("בוצע.")

@bot.tree.command(name="kick", description="העפת משתמש מהשרת")
async def kick(i, member: discord.Member):
    if await check_nl_owner(i):
        await member.kick(); await i.response.send_message("👢 הועף.")

@bot.tree.command(name="say", description="שליחת הודעה דרך הבוט")
async def say(i, text: str):
    if await check_nl_owner(i):
        await i.channel.send(text); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="slowmode", description="הגדרת מצב איטי לערוץ")
async def slow(i, seconds: int):
    if await check_nl_owner(i):
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="serverinfo", description="קבלת מידע על השרת")
async def si(i):
    emb = discord.Embed(title=i.guild.name, description=f"חברים: {i.guild.member_count}", color=0x3498db)
    emb.set_footer(text=OWNER_FOOTER); await i.response.send_message(embed=emb)

@bot.tree.command(name="avatar", description="הצגת תמונת פרופיל")
async def av(i, member: discord.Member = None):
    m = member or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="בדיקת מהירות הבוט")
async def p(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
async def wr(i, member: discord.Member, reason: str):
    if await check_nl_owner(i): await i.response.send_message(f"⚠️ אזהרה נרשמה ל-{member.mention}: {reason}")

@bot.tree.command(name="add_role", description="הוספת רול למשתמש")
async def ar(i, member: discord.Member, role: discord.Role):
    if await check_nl_owner(i): await member.add_roles(role); await i.response.send_message("✅ ניתן.")

@bot.tree.command(name="remove_role", description="הסרת רול ממשתמש")
async def rr(i, member: discord.Member, role: discord.Role):
    if await check_nl_owner(i): await member.remove_roles(role); await i.response.send_message("❌ הוסר.")

@bot.tree.command(name="userinfo", description="מידע על משתמש")
async def ui_cmd(i, member: discord.Member):
    emb = discord.Embed(title=member.name, color=0x3498db); emb.set_footer(text=OWNER_FOOTER)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="nick", description="שינוי כינוי למשתמש")
async def nick(i, member: discord.Member, name: str):
    if await check_nl_owner(i): await member.edit(nick=name); await i.response.send_message("✅ שונה.")

@bot.tree.command(name="audit", description="בדיקת לוגים אחרונים")
async def audit(i):
    if await check_nl_owner(i): await i.response.send_message("📁 הלוגים נשלחו לערוץ האבטחה.", ephemeral=True)

@bot.tree.command(name="credits", description="קרדיט ליוצר")
async def creds(i): await i.response.send_message(f"🛡️ הבוט פותח על ידי **{OWNER_FOOTER}**")

# --- Events ---
@bot.event
async def on_member_join(member):
    welcome_ch = member.guild.get_channel(WELCOME_CH_ID)
    if welcome_ch: await welcome_ch.send(f"🔥 ברוך הבא לשרת של NL, {member.mention}!")
    
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        alert = member.guild.get_channel(ATTEMPT_LOG_CH_ID)
        if alert:
            emb = discord.Embed(title="🚨 NL Alt Detected!", description=f"משתמש: {member.mention}\nותק: {age.days} ימים", color=0xffa500)
            await alert.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_message(msg):
    if msg.author.id in suspected_list:
        suspected_list[msg.author.id] = datetime.now(timezone.utc)
    await bot.process_commands(msg)

if TOKEN: bot.run(TOKEN)
