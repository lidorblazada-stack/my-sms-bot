import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (לידור, תוודא שה-IDs נכונים) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SUSPECT_ROLE_ID = 1501953906736103535 # הרול שיקבל מי שתסמן כחשוד
SECURITY_LOG_ID = 1502014872655888554 # ערוץ לוגים שוטף (מי עשה מה)
ATTEMPT_LOG_CH_ID = 1503496964732354620 # ערוץ דיווח פריצות ואלטים
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 

# מערכות מעקב
user_warnings = defaultdict(int)
suspected_list = {} # מעקב הודעות 24 שעות
OWNER_FOOTER = "Developed by Lidor Owner 👑"

# --- תפריט אלטים עם 3 אפשרויות ---

class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def check_perm(self, i: discord.Interaction):
        if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
            return True
        await i.response.send_message("❌ רק לידור האונר יכול להחליט!", ephemeral=True)
        return False

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if await self.check_perm(i):
            await self.member.kick(reason="אלט שהועף על ידי אונר")
            await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} הועף.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep_alt(self, i, b):
        if await self.check_perm(i):
            await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} אושר ונשאר.", ephemeral=True)

    @ui.button(label="סמן כחשוד 🕵️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if await self.check_perm(i):
            # 1. מתן רול חשוד
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role: await self.member.add_roles(role)
            # 2. כניסה למעקב 24 שעות
            suspected_list[self.member.id] = datetime.now(timezone.utc)
            # 3. מחיקת ההודעה
            await i.message.delete()
            await i.response.send_message(f"🕵️ {self.member.name} סומן כחשוד וקיבל רול. המעקב החל!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: 
            await i.user.add_roles(role)
            await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- Bot Core ---

class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.check_inactive_suspects.start()
        await self.tree.sync()

    @tasks.loop(hours=1) # בודק כל שעה מי "שקט" מדי
    async def check_inactive_suspects(self):
        now = datetime.now(timezone.utc)
        ch = self.get_channel(ATTEMPT_LOG_CH_ID)
        to_remove = []
        for uid, last_msg in suspected_list.items():
            if now - last_msg > timedelta(hours=24):
                if ch: await ch.send(f"⚠️ **התראת מעקב:** המשתמש <@{uid}> (חשוד) לא שלח הודעה כבר 24 שעות!")
                to_remove.append(uid)
        for uid in to_remove: del suspected_list[uid]

bot = CyberShield()

# --- מערכת לוגים ואבטחת אונר ---

async def log_cmd(i, status):
    ch = i.guild.get_channel(SECURITY_LOG_ID)
    if ch:
        color = 0x3498db if status == "בוצע" else 0xff0000
        emb = discord.Embed(title=f"🛡️ פקודה: {i.command.name}", description=f"סטטוס: {status}", color=color)
        emb.add_field(name="מבצע", value=f"{i.user.mention} ({i.user.id})")
        emb.set_timestamp()
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        await log_cmd(i, "בוצע") # שולח לוג על כל פקודה של אונר
        return True
    # אם מישהו אחר מנסה
    await log_cmd(i, "🚨 ניסיון פריצה!")
    await i.response.send_message("🚫 מצטער אחי, הפקודה הזו ללידור האונר בלבד!", ephemeral=True)
    return False

# --- הפקודות שלך (הכל מרוכז כאן) ---

@bot.tree.command(name="nuke", description="מחיקה ובנייה מחדש של הערוץ")
async def nuke(i):
    if await check_owner(i):
        new = await i.channel.clone(); await i.channel.delete()
        await new.send(f"🚀 הערוץ נוקה ושוחזר על ידי **לידור האונר**!")

@bot.tree.command(name="mute", description="מיוט ליומיים עם הסרה אוטומטית")
async def mute(i, member: discord.Member):
    if await check_owner(i):
        role = i.guild.get_role(MUTE_ROLE_ID)
        await member.add_roles(role)
        await i.response.send_message(f"🔇 {member.name} הושתק ליומיים.")
        await asyncio.sleep(172800) # יומיים
        if role in member.roles: await member.remove_roles(role)

@bot.tree.command(name="ban", description="באן למשתמש מהשרת")
async def ban(i, member: discord.Member):
    if await check_owner(i):
        await member.ban(); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="clear", description="מחיקת הודעות")
async def clear(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount}.", ephemeral=True)

@bot.tree.command(name="lock", description="נעילת הערוץ")
async def lock(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="פתיחת הערוץ")
async def unlock(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="setup_verify", description="פאנל אימות")
async def sv(i):
    if await check_owner(i):
        emb = discord.Embed(title="🛡️ מערכת אימות", description="לחץ על הכפתור למטה כדי להיכנס", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView()); await i.response.send_message("הוקם.")

@bot.tree.command(name="say", description="דיבור דרך הבוט")
async def say(i, text: str):
    if await check_owner(i):
        await i.channel.send(text); await i.response.send_message("נשלח", ephemeral=True)

# --- Events (ברוך הבא ואלטים) ---

@bot.event
async def on_member_join(member):
    # ברוך הבא
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch: await ch.send(f"🔥 ברוך הבא {member.mention} לשרת של לידור!")
    
    # בדיקת אלט (חשבון חדש מ-7 ימים)
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        alert = member.guild.get_channel(ATTEMPT_LOG_CH_ID)
        if alert:
            emb = discord.Embed(title="🚨 אלט זוהה!", description=f"משתמש: {member.mention}\nותק: {age.days} ימים", color=0xffa500)
            emb.set_footer(text="לידור, מה עושים?")
            await alert.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_message(msg):
    # עדכון זמן הודעה אחרונה לחשודים
    if msg.author.id in suspected_list:
        suspected_list[msg.author.id] = datetime.now(timezone.utc)
    await bot.process_commands(msg)

if TOKEN: bot.run(TOKEN)
