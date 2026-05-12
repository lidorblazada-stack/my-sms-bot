import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
import json

# --- הגדרות IDs (תעדכן לפי השרת שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SUSPECT_ROLE_ID = 1501953906736103535 
SECURITY_LOG_ID = 1502014872655888554 
ATTEMPT_LOG_CH_ID = 1503496964732354620 
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 

# משתני מערכת (טעינה מקבצים כדי שלא ימחק בריסטרט)
suspected_list = {} # {id: timestamp}
user_warnings = {} # {id: count}

# --- לוגיקה של כפתורי אלט/חשוד ---
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def check_owner(self, i: discord.Interaction):
        if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
        await i.response.send_message("❌ אין לך גישת אונר!", ephemeral=True)
        return False

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if await self.check_owner(i):
            await self.member.kick(reason="החלטת אונר"); await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} הועף.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep_alt(self, i, b):
        if await self.check_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role and role in self.member.roles: await self.member.remove_roles(role)
            if self.member.id in suspected_list: del suspected_list[self.member.id]
            await i.message.delete()
            await i.response.send_message(f"✅ המשתמש אושר.", ephemeral=True)

    @ui.button(label="להמשיך לשים עין 🕵️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if await self.check_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role: await self.member.add_roles(role)
            suspected_list[self.member.id] = datetime.now(timezone.utc)
            await i.message.delete()
            await i.response.send_message(f"🕵️ מעקב חודש ל-24 שעות נוספות.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת!", ephemeral=True)

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
        for uid, last_msg in list(suspected_list.items()):
            if now - last_msg > timedelta(hours=24):
                member = ch.guild.get_member(uid)
                if member:
                    emb = discord.Embed(title="⚠️ חשוד לא פעיל", description=f"{member.mention} לא שלח הודעה 24 שעות.", color=0xff0000)
                    await ch.send(embed=emb, view=AltActionView(member))
                    suspected_list[uid] = now 

bot = NLShield()

# --- אבטחה ולוגים ---
async def validate(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        log_ch = i.guild.get_channel(SECURITY_LOG_ID)
        if log_ch:
            emb = discord.Embed(title=f"🛡️ פקודה: {i.command.name}", description=f"בוצעה על ידי: {i.user.mention}", color=0x3498db)
            await log_ch.send(embed=emb)
        return True
    await i.response.send_message("🚫 ל-Owner בלבד!", ephemeral=True)
    return False

# --- 15 הפקודות הכי חזקות ---

@bot.tree.command(name="nuke", description="1. ניקוי ושחזור הערוץ")
async def nuke(i):
    if await validate(i):
        new = await i.channel.clone(); await i.channel.delete()
        await new.send("🚀 הערוץ נוקה ושוחזר.")

@bot.tree.command(name="clear", description="2. מחיקת כמות הודעות")
async def clear(i, amount: int):
    if await validate(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="lock", description="3. נעילת ערוץ")
async def lock(i):
    if await validate(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="4. פתיחת ערוץ")
async def unlock(i):
    if await validate(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="mute", description="5. השתקת משתמש")
async def mute(i, member: discord.Member):
    if await validate(i):
        await member.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"🔇 {member.name} הושתק.")

@bot.tree.command(name="ban", description="6. חסימת משתמש")
async def ban(i, member: discord.Member):
    if await validate(i):
        await member.ban(); await i.response.send_message(f"🚫 {member.name} נחסם.")

@bot.tree.command(name="kick", description="7. העפת משתמש")
async def kick(i, member: discord.Member):
    if await validate(i):
        await member.kick(); await i.response.send_message(f"👢 {member.name} הועף.")

@bot.tree.command(name="warn", description="8. מתן אזהרה")
async def warn(i, member: discord.Member, reason: str):
    if await validate(i):
        user_warnings[member.id] = user_warnings.get(member.id, 0) + 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! פעם {user_warnings[member.id]}. סיבה: {reason}")

@bot.tree.command(name="setup_verify", description="9. פאנל אימות")
async def sv(i):
    if await validate(i):
        emb = discord.Embed(title="🛡️ אימות", description="לחץ לאימות", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView()); await i.response.send_message("בוצע.")

@bot.tree.command(name="slowmode", description="10. מצב איטי")
async def slow(i, seconds: int):
    if await validate(i):
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="say", description="11. הבוט מדבר")
async def say(i, text: str):
    if await validate(i):
        await i.channel.send(text); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="mark_suspect", description="12. סימון חשוד ידני")
async def ms(i, member: discord.Member):
    if await validate(i):
        suspected_list[member.id] = datetime.now(timezone.utc)
        role = i.guild.get_role(SUSPECT_ROLE_ID)
        if role: await member.add_roles(role)
        await i.response.send_message(f"🕵️ {member.name} בשימור עין.")

@bot.tree.command(name="serverinfo", description="13. מידע על השרת")
async def si(i):
    emb = discord.Embed(title=i.guild.name, description=f"חברים: {i.guild.member_count}", color=0x3498db)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="avatar", description="14. הצגת תמונה")
async def av(i, member: discord.Member = None):
    m = member or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="15. מהירות הבוט")
async def p(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# --- Events ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch: await ch.send(f"🔥 ברוך הבא {member.mention}!")
    if (datetime.now(timezone.utc) - member.created_at).days < ALT_MIN_DAYS:
        alert = member.guild.get_channel(ATTEMPT_LOG_CH_ID)
        if alert:
            emb = discord.Embed(title="🚨 אלט זוהה!", description=f"{member.mention} חדש!", color=0xffa500)
            await alert.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_message(msg):
    if msg.author.id in suspected_list: suspected_list[msg.author.id] = datetime.now(timezone.utc)
    await bot.process_commands(msg)

if TOKEN: bot.run(TOKEN)
