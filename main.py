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
spam_tracker = defaultdict(list)
delete_tracker = defaultdict(list)

# --- מערכת כפתורים ---
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
            await self.member.kick(); await i.message.delete()
            await i.response.send_message(f"✅ {self.member.name} הועף.", ephemeral=True)

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep_alt(self, i, b):
        if await self.check_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role and role in self.member.roles: await self.member.remove_roles(role)
            if self.member.id in suspected_list: del suspected_list[self.member.id]
            await i.message.delete()
            await i.response.send_message(f"✅ אושר.", ephemeral=True)

    @ui.button(label="להמשיך לשים עין 🕵️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if await self.check_owner(i):
            role = i.guild.get_role(SUSPECT_ROLE_ID)
            if role: await self.member.add_roles(role)
            suspected_list[self.member.id] = datetime.now(timezone.utc)
            await i.message.delete()
            await i.response.send_message(f"🕵️ המעקב חודש.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
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
                    await ch.send(embed=discord.Embed(title="⚠️ חשוד לא פעיל", description=f"{member.mention} לא דיבר 24 שעות.", color=0xff0000), view=AltActionView(member))
                    suspected_list[uid] = now 

bot = NLShield()

# --- לוגיקה של הגנה אקטיבית (Anti-Nuke/Spam) ---
@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
        if any(role.id == OWNER_ROLE_ID for role in entry.user.roles): return
        now = asyncio.get_event_loop().time()
        delete_tracker[entry.user.id].append(now)
        if len([t for t in delete_tracker[entry.user.id] if now - t < 60]) >= 3:
            member = channel.guild.get_member(entry.user.id)
            if member: await member.edit(roles=[], reason="Anti-Nuke Active")

# --- פקודות ---
async def validate(i):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
    await i.response.send_message("🚫 אונר בלבד!", ephemeral=True); return False

@bot.tree.command(name="nuke")
async def nuke(i):
    if await validate(i):
        new = await i.channel.clone(); await i.channel.delete()

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if await validate(i):
        await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="mute")
async def mute(i, member: discord.Member):
    if await validate(i):
        await member.add_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"🔇 {member.name} הושתק.")

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    if await validate(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! פעם {user_warnings[member.id]}. סיבה: {reason}")

@bot.tree.command(name="setup_verify")
async def sv(i):
    if await validate(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView())
        await i.response.send_message("הוקם.")

# --- Events ---
@bot.event
async def on_message(message):
    if message.author.bot or any(role.id == OWNER_ROLE_ID for role in message.author.roles if hasattr(message.author, 'roles')): return
    # Anti-Spam
    now = asyncio.get_event_loop().time()
    spam_tracker[message.author.id].append(now)
    if len([t for t in spam_tracker[message.author.id] if now - t < 3]) > 5:
        await message.author.timeout(timedelta(minutes=10), reason="Spam")
        await message.channel.send(f"🔇 {message.author.mention} הושתק על ספאם.", delete_after=5)
    
    if message.author.id in suspected_list: suspected_list[message.author.id] = datetime.now(timezone.utc)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if (datetime.now(timezone.utc) - member.created_at).days < ALT_MIN_DAYS:
        ch = member.guild.get_channel(ATTEMPT_LOG_CH_ID)
        if ch: await ch.send(embed=discord.Embed(title="🚨 אלט!", description=f"{member.mention} חדש!"), view=AltActionView(member))

if TOKEN: bot.run(TOKEN)
