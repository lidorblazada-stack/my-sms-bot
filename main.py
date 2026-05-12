import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SUSPECT_ROLE_ID = 1501953906736103535 
SECURITY_LOG_ID = 1502014872655888554 
ATTEMPT_LOG_CH_ID = 1503496964732354620 
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 

# משתני מערכת
suspected_list = {} 
user_warnings = defaultdict(int)

# --- View עם 3 כפתורים (להעיף/להשאיר/לשים עין) ---
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def check_nl_owner(self, i: discord.Interaction):
        if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
        await i.response.send_message("❌ אין לך הרשאת אונר!", ephemeral=True)
        return False

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if await self.check_nl_owner(i):
            try:
                await self.member.kick(reason="החלטת אונר")
                await i.message.delete()
                await i.response.send_message(f"✅ {self.member.name} הועף.", ephemeral=True)
            except:
                await i.response.send_message("❌ תקלה בהעפת המשתמש.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep_alt(self, i, b):
        if await self.check_nl_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role and role in self.member.roles: await self.member.remove_roles(role)
            if self.member.id in suspected_list: del suspected_list[self.member.id]
            await i.message.delete()
            await i.response.send_message(f"✅ המשתמש אושר.", ephemeral=True)

    @ui.button(label="להמשיך לשים עין 🕵️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if await self.check_nl_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role: await self.member.add_roles(role)
            suspected_list[self.member.id] = datetime.now(timezone.utc)
            await i.message.delete()
            await i.response.send_message(f"🕵️ המעקב חודש ל-24 שעות נוספות.", ephemeral=True)

# --- פאנל אימות ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: 
            await i.user.add_roles(role)
            await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- Bot Core ---
class NLShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        self.check_suspects.start()
        await self.tree.sync()

    @tasks.loop(hours=1)
    async def check_suspects(self):
        now = datetime.now(timezone.utc)
        ch = self.get_channel(ATTEMPT_LOG_CH_ID)
        if not ch: return
        to_report = [uid for uid, last_msg in suspected_list.items() if now - last_msg > timedelta(hours=24)]
        for uid in to_report:
            member = ch.guild.get_member(uid)
            if member:
                emb = discord.Embed(title="⚠️ התראת חוסר פעילות", description=f"החשוד {member.mention} לא שלח הודעה ב-24 שעות האחרונות.", color=0xff0000)
                await ch.send(embed=emb, view=AltActionView(member))
                suspected_list[uid] = now 

bot = NLShield()

# --- לוגים ואבטחה ---
async def log_it(i, status):
    ch = i.guild.get_channel(SECURITY_LOG_ID)
    if ch:
        color = 0x3498db if status == "בוצע" else 0xff0000
        emb = discord.Embed(title=f"🛡️ פקודה: {i.command.name}", description=f"סטטוס: {status}\nמבצע: {i.user.mention}", color=color)
        await ch.send(embed=emb)

async def validate_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        await log_it(i, "בוצע"); return True
    await log_it(i, "🚨 ניסיון פריצה!"); await i.response.send_message("🚫 פקודה לאונר בלבד!", ephemeral=True)
    return False

# --- פקודות ---

@bot.tree.command(name="nuke", description="ניקוי ושחזור הערוץ")
async def nuke(i):
    if await validate_owner(i):
        new = await i.channel.clone(); await i.channel.delete()
        await new.send("🚀 הערוץ נוקה ושוחזר.")

@bot.tree.command(name="warn", description="מתן אזהרה")
async def warn(i, member: discord.Member, reason: str):
    if await validate_owner(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! ({user_warnings[member.id]})\nסיבה: {reason}")

@bot.tree.command(name="clear", description="מחיקת הודעות")
async def clear(i, amount: int):
    if await validate_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="setup_verify", description="פאנל אימות")
async def sv(i):
    if await validate_owner(i):
        emb = discord.Embed(title="🛡️ אימות", description="לחץ למטה לאימות", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView()); await i.response.send_message("בוצע.", ephemeral=True)

# --- Events ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch: await ch.send(f"🔥 ברוך הבא, {member.mention}!")
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        alert_ch = member.guild.get_channel(ATTEMPT_LOG_CH_ID)
        if alert_ch:
            emb = discord.Embed(title="🚨 אלט זוהה!", description=f"משתמש: {member.mention}\nותק: {age.days} ימים", color=0xffa500)
            await alert_ch.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_message(msg):
    if msg.author.id in suspected_list:
        suspected_list[msg.author.id] = datetime.now(timezone.utc)
    await bot.process_commands(msg)

if TOKEN: bot.run(TOKEN)
