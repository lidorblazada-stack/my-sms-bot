import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג פריצות
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
FEEDBACK_CH_ID = 1503475379942461522  # לוג פידבקים

# ערוצים ורולים נוספים
REPORT_LOG_CH_ID = 1501946934779449505
MEMBER_ROLE_ID = 1501983948111352091
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה
user_balances = defaultdict(int)
user_warnings = defaultdict(int)

# --- מערכת הגנה קשוחה ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    # אזהרה מילולית
    await i.response.send_message(f"❌ {i.user.mention}, זו אזהרה מילולית! הניסיון נרשם.", ephemeral=True)
    
    user_warnings[i.user.id] += 1
    count = user_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        await log_ch.send(f"🚨 **ניסיון פריצה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה: {count}/5")

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="ניסיון שימוש בפקודות אונר")
    elif count >= 5:
        await i.user.kick(reason="ניסיון שימוש בפקודות אונר")
        user_warnings[i.user.id] = 0
    return False

# --- Views (חנות, אימות, פידבק) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.success, custom_id="sh_1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh_3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.secondary, custom_id="sh_bal")
    async def b4(self, i, b):
        await i.response.send_message(f"💰 יתרה שלך: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ אין כסף", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("אומתת!", ephemeral=True)

class FeedbackModal(ui.Modal, title="שלח פידבק"):
    inp = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        if ch: await ch.send(embed=discord.Embed(title="💬 פידבק", description=self.inp.value, color=0x00ffff).set_author(name=i.user.name))
        await i.response.send_message("נשלח", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.primary, custom_id="fb_v")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ **אלט חשוד:** {member.mention}")

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

# --- פקודות אונר בלבד ---

@bot.tree.command(name="setup_shop", description="הקמת חנות")
async def ss(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🛒 —— CYBER-STORE MARKET ——", description="🎗️ Supporter: 2k\n💎 VIP: 5k\n🛠️ Staff: 15k", color=0x2b2d31)
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="mute", description="השתקת משתמש")
async def mt(i, member: discord.Member, minutes: int, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await i.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות. סיבה: {reason}")

@bot.tree.command(name="unmute", description="ביטול השתקה")
async def um(i, member: discord.Member):
    if await check_owner_and_punish(i):
        await member.timeout(None)
        await i.response.send_message(f"🔊 השתקה בוטלה ל-{member.mention}")

@bot.tree.command(name="kick", description="העפת משתמש")
async def kk(i, member: discord.Member, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.kick(reason=reason)
        await i.response.send_message(f"👞 {member.mention} הועף. סיבה: {reason}")

@bot.tree.command(name="ban", description="הרחקת משתמש")
async def bn(i, member: discord.Member, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.ban(reason=reason)
        await i.response.send_message(f"🚫 {member.mention} הורחק לצמיתות. סיבה: {reason}")

@bot.tree.command(name="warns_check", description="בדיקת אזהרות של משתמש")
async def wc(i, member: discord.Member):
    if await check_owner_and_punish(i):
        await i.response.send_message(f"⚠️ למשתמש {member.mention} יש `{user_warnings[member.id]}` אזהרות.", ephemeral=True)

@bot.tree.command(name="add_money", description="הוספת כסף")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"✅ נוספו {amount} ל-{member.mention}")

@bot.tree.command(name="clear", description="ניקוי צ'אט")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

# פקודות setup נוספות
@bot.tree.command(name="setup_verify", description="הקמת אימות")
async def sv(i):
    if await check_owner_and_punish(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", description="לחץ למטה", color=0x2b2d31), view=VerifyView())
        await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פידבק")
async def sf(i):
    if await check_owner_and_punish(i):
        await i.channel.send(embed=discord.Embed(title="💬 פידבק", description="לחץ למטה", color=0x2b2d31), view=FeedbackView())
        await i.response.send_message("הוקם", ephemeral=True)

# פקודות משתמש
@bot.tree.command(name="report", description="דיווח")
async def rep(i, member: discord.Member, reason: str):
    await i.guild.get_channel(REPORT_LOG_CH_ID).send(f"🚨 דיווח על {member.mention}: {reason}")
    await i.response.send_message("נשלח", ephemeral=True)

bot.run(TOKEN)
