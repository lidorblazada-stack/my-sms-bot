import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (מעודכן לפי הקוד שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SUSPECT_ROLE_ID = 1501953906736103535 
ATTEMPT_LOG_CH_ID = 1503496964732354620 
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 

# משתני מערכת
suspected_list = {} 
user_warnings = defaultdict(int)
spam_tracker = defaultdict(list)

# --- מערכות כפתורים ואימות ---
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
            await self.member.kick(); await i.response.send_message("הועף.", ephemeral=True)
        else: await i.response.send_message("אין גישה.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- Bot Core ---
class NLShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = NLShield()

# בדיקת אונר
async def is_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
    await i.response.send_message("🚫 פקודה לאונר בלבד!", ephemeral=True); return False

# --- כל 15 הפקודות בבת אחת ---

@bot.tree.command(name="sync", description="סנכרון פקודות (תריץ את זה אם חסר משהו)")
async def sync_cmds(i: discord.Interaction):
    if await is_owner(i):
        await bot.tree.sync()
        await i.response.send_message("✅ כל 15 הפקודות סונכרנו בהצלחה!", ephemeral=True)

@bot.tree.command(name="nuke", description="מחיקת חדר ושחזורו")
async def nuke(i: discord.Interaction):
    if await is_owner(i):
        new = await i.channel.clone(); await i.channel.delete()

@bot.tree.command(name="clear", description="ניקוי הודעות")
async def clear(i: discord.Interaction, amount: int):
    if await is_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="mute", description="השתקת משתמש")
async def mute(i: discord.Interaction, member: discord.Member):
    if await is_owner(i):
        await member.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="unmute", description="ביטול השתקה")
async def unmute(i: discord.Interaction, member: discord.Member):
    if await is_owner(i):
        await member.remove_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"🔊 {member.mention} יכול לדבר שוב.")

@bot.tree.command(name="warn", description="מתן אזהרה")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    if await is_owner(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר. אזהרה מספר: {user_warnings[member.id]}\nסיבה: {reason}")

@bot.tree.command(name="kick", description="העפת משתמש")
async def kick(i: discord.Interaction, member: discord.Member):
    if await is_owner(i):
        await member.kick(); await i.response.send_message(f"👢 {member.name} הועף.")

@bot.tree.command(name="ban", description="חסימת משתמש")
async def ban(i: discord.Interaction, member: discord.Member):
    if await is_owner(i):
        await member.ban(); await i.response.send_message(f"🔨 {member.name} נחסם!")

@bot.tree.command(name="setup_verify", description="הצבת כפתור אימות")
async def sv(i: discord.Interaction):
    if await is_owner(i):
        emb = discord.Embed(title="🛡️ מערכת אימות - NL", description="לחץ על הכפתור למטה כדי לקבל גישה לשרת", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView())
        await i.response.send_message("מערכת הוקמה.", ephemeral=True)

@bot.tree.command(name="lock", description="נעילת חדר")
async def lock(i: discord.Interaction):
    if await is_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒 החדר ננעל.")

@bot.tree.command(name="unlock", description="פתיחת חדר")
async def unlock(i: discord.Interaction):
    if await is_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True)
        await i.response.send_message("🔓 החדר נפתח.")

@bot.tree.command(name="slowmode", description="מצב איטי")
async def slow(i: discord.Interaction, seconds: int):
    if await is_owner(i):
        await i.channel.edit(slowmode_delay=seconds)
        await i.response.send_message(f"⏳ מצב איטי הוגדר ל-{seconds} שניות.")

@bot.tree.command(name="say", description="הודעת אונר מעוצבת")
async def say(i: discord.Interaction, text: str):
    if await is_owner(i):
        emb = discord.Embed(description=text, color=0x00ffff)
        emb.set_author(name="הודעת הנהלה", icon_url=i.user.avatar.url)
        await i.channel.send(embed=emb); await i.response.send_message("נשלח.", ephemeral=True)

@bot.tree.command(name="profile", description="בדיקת פרופיל משתמש")
async def profile(i: discord.Interaction, member: discord.Member):
    emb = discord.Embed(title=f"פרופיל: {member.name}", color=member.color)
    emb.add_field(name="הצטרף ב:", value=member.joined_at.strftime("%d/%m/%Y"))
    emb.set_thumbnail(url=member.avatar.url)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="stats", description="מצב השרת")
async def stats(i: discord.Interaction):
    emb = discord.Embed(title=f"סטטיסטיקה: {i.guild.name}", color=0xff8800)
    emb.add_field(name="אנשים בשרת:", value=i.guild.member_count)
    await i.response.send_message(embed=emb)

# --- אבטחה אוטומטית (Anti-Spam) ---
@bot.event
async def on_message(message):
    if message.author.bot or any(role.id == OWNER_ROLE_ID for role in message.author.roles if hasattr(message.author, 'roles')): return
    
    now = asyncio.get_event_loop().time()
    spam_tracker[message.author.id].append(now)
    if len([t for t in spam_tracker[message.author.id] if now - t < 3]) > 5:
        await message.author.timeout(timedelta(minutes=10), reason="Spamming")
        await message.channel.send(f"🔇 {message.author.mention} הושבת ל-10 דקות (ספאם).", delete_after=10)

if TOKEN: bot.run(TOKEN)
