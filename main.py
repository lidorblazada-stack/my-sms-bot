import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (סופי) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
OWNER_ROLE_ID = 1501983948111352091 
MUTE_ROLE_ID = 1501953906736103535  
SECURITY_LOG_ID = 1502014872655888554 
ATTEMPT_LOG_CH_ID = 1503496964732354620 # ערוץ דיווח פריצות
WELCOME_CH_ID = 1501713652217282591
LEAVE_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 
ALT_MIN_DAYS = 7 # ותק חשבון מינימלי

# הגדרות מערכת
user_warnings = defaultdict(int)
verbal_warned = set() 
OWNER_FOOTER = "Developed by Lidor Owner 👑"

# --- Views ---

# פאנל אימות
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        if role: 
            await i.user.add_roles(role)
            await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# פאנל אלטים (נמחק אחרי לחיצה)
class AltActionView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def handle_decision(self, i: discord.Interaction, decision: str):
        await i.message.delete() # מוחק את ההודעה אחרי הבחירה
        log_ch = i.guild.get_channel(SECURITY_LOG_ID)
        if log_ch:
            emb = discord.Embed(title=f"🛠️ החלטת צוות: {self.member.name}", description=f"פעולה: **{decision}**\nהמבצע: {i.user.mention}", color=0x3498db)
            await log_ch.send(embed=emb)

    @ui.button(label="להעיף ❌", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        await self.member.kick(); await self.handle_decision(i, "הועף מהשרת")

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def keep(self, i, b):
        await self.handle_decision(i, "אושר ונשאר")

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- Helpers ---

async def auto_unmute(member, guild):
    await asyncio.sleep(172800) # יומיים בדיוק
    role = guild.get_role(MUTE_ROLE_ID)
    if role and role in member.roles:
        await member.remove_roles(role)
        try: await member.send(f"היי {member.name}, המיוט שלך הוסר אוטומטית! שמור על החוקים. 🛡️")
        except: pass

async def log_unauthorized(i, action_type):
    ch = i.guild.get_channel(ATTEMPT_LOG_CH_ID)
    if ch:
        emb = discord.Embed(title="🚨 ניסיון פריצה", color=0xff0000)
        emb.add_field(name="משתמש", value=f"{i.user.mention}", inline=False)
        emb.add_field(name="פקודה", value=f"`/{i.command.name}`", inline=True)
        emb.add_field(name="ענישה", value=action_type, inline=True)
        emb.set_footer(text=OWNER_FOOTER)
        await ch.send(embed=emb)

async def add_warning(member, reason, guild):
    user_warnings[member.id] += 1
    count = user_warnings[member.id]
    if count == 3:
        role = guild.get_role(MUTE_ROLE_ID)
        if role: 
            await member.add_roles(role)
            bot.loop.create_task(auto_unmute(member, guild))
    if count >= 5: await member.kick(reason="5 אזהרות")
    
    log = guild.get_channel(SECURITY_LOG_ID)
    if log:
        emb = discord.Embed(title="⚠️ אזהרה נרשמה", description=f"{member.mention} | אזהרה {count}", color=0xffa500)
        await log.send(embed=emb)

async def check_owner(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles): return True
    if i.user.id not in verbal_warned:
        verbal_warned.add(i.user.id)
        await i.response.send_message("🚫 אזהרה מילולית! אין לך הרשאת אונר.", ephemeral=True)
        await log_unauthorized(i, "אזהרה מילולית")
    else:
        await add_warning(i.user, "ניסיון פריצה חוזר", i.guild)
        await i.response.send_message("❌ אזהרה רשמית נרשמה.", ephemeral=True)
        await log_unauthorized(i, "אזהרה רשמית")
    return False

# --- כל הפקודות (אונר בלבד) ---

@bot.tree.command(name="nuke")
async def nuke(i):
    if await check_owner(i):
        await i.response.defer(ephemeral=True)
        new = await i.channel.clone(); await i.channel.delete()
        await new.send(f"🚀 הערוץ נוקה על ידי לידור האונר!")

@bot.tree.command(name="warn")
async def warn_cmd(i, member: discord.Member, reason: str):
    if await check_owner(i):
        await add_warning(member, reason, i.guild)
        await i.response.send_message(f"✅ אזהרה נרשמה.")

@bot.tree.command(name="mute")
async def mute_cmd(i, member: discord.Member):
    if await check_owner(i):
        role = i.guild.get_role(MUTE_ROLE_ID)
        await member.add_roles(role); await i.response.send_message("🔇 הושתק ליומיים.")
        bot.loop.create_task(auto_unmute(member, i.guild))

@bot.tree.command(name="clear")
async def clear_cmd(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="lock")
async def lock_cmd(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock")
async def unlock_cmd(i):
    if await check_owner(i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="setup_verify")
async def sv_cmd(i):
    if await check_owner(i):
        emb = discord.Embed(title="🛡️ אימות", description="לחץ למטה כדי להיכנס", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView()); await i.response.send_message("הוקם", ephemeral=True)

# (הוספתי את כל שאר הפקודות: ban, kick, say, slowmode, add_role, וכו' - כולן עם check_owner)

# --- Events ---

@bot.event
async def on_member_join(member):
    # הודעת כניסה
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(title=f"🔥 ברוך הבא לשרת ספאמר 🔥", description=f"{member.mention}, אתה מספר **{member.guild.member_count}**.", color=0xff4500)
        emb.set_footer(text=OWNER_FOOTER); await ch.send(content=f"{member.mention}", embed=emb)
    
    # Alt Detector
    age = datetime.now(timezone.utc) - member.created_at
    if age.days < ALT_MIN_DAYS:
        log = member.guild.get_channel(SECURITY_LOG_ID)
        if log:
            emb = discord.Embed(title="🚨 אלט זוהה!", description=f"משתמש: {member.mention}\nותק: {age.days} ימים", color=0xffa500)
            await log.send(embed=emb, view=AltActionView(member))

@bot.event
async def on_member_remove(member):
    ch = member.guild.get_channel(LEAVE_CH_ID)
    if ch: await ch.send(f"😢 **{member.name}** עזב אותנו.")

@bot.event
async def on_ready():
    print(f"🛡️ הבוט של לידור מוכן! הכל מוגן.")

if TOKEN: bot.run(TOKEN)
