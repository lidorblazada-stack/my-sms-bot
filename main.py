import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- IDs והגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג פריצות
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
SUSPECT_ROLE_ID = 1503464176599695380 # רול חשוד (לפי האיידי שנתת)

# רולים ודאטה
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041
user_balances = defaultdict(int)
attack_warnings = defaultdict(int)

# --- כפתורי ניהול אלטים (העדכון החדש) ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    # כפתור 1: להעיף
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def kick_alt(self, i: discord.Interaction, b: ui.Button):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles):
            return await i.response.send_message("❌ רק אונר יכול להחליט!", ephemeral=True)
        
        member = i.guild.get_member(self.member_id)
        if member:
            await member.kick(reason="אלט חשוד - הועף על ידי אונר")
            await i.response.send_message(f"✅ {member.name} הועף מהשרת.", ephemeral=True)
            await i.message.delete()

    # כפתור 2: להשאיר (רגיל)
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success, custom_id="alt_stay")
    async def stay_alt(self, i: discord.Interaction, b: ui.Button):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles):
            return await i.response.send_message("❌ רק אונר יכול להחליט!", ephemeral=True)
        
        await i.response.send_message("✅ המשתמש אושר בשרת.", ephemeral=True)
        await i.message.delete()

    # כפתור 3: רול חשוד
    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary, custom_id="alt_suspect")
    async def suspect_alt(self, i: discord.Interaction, b: ui.Button):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles):
            return await i.response.send_message("❌ רק אונר יכול להחליט!", ephemeral=True)
        
        member = i.guild.get_member(self.member_id)
        role = i.guild.get_role(SUSPECT_ROLE_ID)
        if member and role:
            await member.add_roles(role)
            await i.response.send_message(f"⚠️ {member.name} הושאר בשרת עם רול חשוד.", ephemeral=True)
            await i.message.delete()

# --- בדיקת אונר + ענישה ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    await i.response.send_message(f"❌ {i.user.mention}, זו אזהרה מילולית! אין גישה לפקודות אונר.", ephemeral=True)
    attack_warnings[i.user.id] += 1
    count = attack_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        await log_ch.send(f"⚠️ **ניסיון פריצה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה: {count}/5")

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="3 ניסיונות שימוש בפקודות אונר")
    elif count >= 5:
        await i.user.kick(reason="5 ניסיונות שימוש בפקודות אונר")
        attack_warnings[i.user.id] = 0
    return False

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch:
            emb = discord.Embed(title="⚠️ זיהוי אלט (חשבון חדש)", 
                                description=f"המשתמש {member.mention} נרשם לאחרונה.\nמה תרצה לעשות?", color=0xffa500)
            await ch.send(embed=emb, view=AltActionView(member.id))

# --- פקודות אונר ---
@bot.tree.command(name="setup_shop", description="[OWNER] הקמת חנות")
async def ss(i):
    if await check_owner_and_punish(i):
        # כאן תבוא פקודת החנות שכתבנו קודם...
        await i.response.send_message("החנות הוקמה!", ephemeral=True)

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

bot.run(TOKEN)
