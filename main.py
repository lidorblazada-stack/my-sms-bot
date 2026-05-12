import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # הרול החדש של האונר
LOG_CH_ID = 1503496964732354620       # ערוץ לוג ניסיונות שימוש באונר
ALT_LOG_ID = 1503464176599695380      # לוג אלטים

# ערוצי קהילה
REPORT_LOG_CH_ID = 1501946934779449505
RECOMMEND_CH_ID = 1501947249658429470

# רולים
MEMBER_ROLE_ID = 1501983948111352091
MUTE_2DAYS_ROLE_ID = 1501953906736103535
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה
user_warnings = defaultdict(int)
user_balances = defaultdict(int)
user_xp = defaultdict(int)
user_levels = defaultdict(int)

# --- בדיקת הרשאת אונר + דיווח ללוג ---
async def check_owner(i: discord.Interaction):
    role = i.guild.get_role(OWNER_ROLE_ID)
    if role in i.user.roles:
        return True
    
    # דיווח על ניסיון שימוש ללא רול אונר
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        emb = discord.Embed(title="🚫 ניסיון גישה נחסם", color=0xff0000, timestamp=datetime.utcnow())
        emb.add_field(name="משתמש", value=f"{i.user.mention} ({i.user.id})")
        emb.add_field(name="פקודה שנוסתה", value=f"`/{i.command.name}`")
        await log_ch.send(embed=emb)
    
    await i.response.send_message("❌ אין לך הרשאת Owner לביצוע הפעולה!", ephemeral=True)
    return False

# --- Views ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.success, custom_id="shop_sup")
    async def b1(self, i, b): await self.process_buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop_vip")
    async def b2(self, i, b): await self.process_buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop_staff")
    async def b3(self, i, b): await self.process_buy(i, 15000, ROLE_TICKET_STAFF)

    async def process_buy(self, i, price, role_id):
        if user_balances[i.user.id] < price:
            return await i.response.send_message("❌ אין לך מספיק מטבעות!", ephemeral=True)
        user_balances[i.user.id] -= price
        await i.user.add_roles(i.guild.get_role(role_id))
        await i.response.send_message("✅ תתחדש! הרול נוסף.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot Hook ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch:
            emb = discord.Embed(title="⚠️ חשבון חשוד (Alt)", description=f"{member.mention} נרשם לאחרונה.", color=0x2b2d31)
            await ch.send(embed=emb)

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        user_balances[msg.author.id] += 10
        user_xp[msg.author.id] += 15
    await bot.process_commands(msg)

# --- פקודות אונר (נעולות לרול) ---
@bot.tree.command(name="setup_shop", description="[OWNER] הקמת החנות")
async def ss(i):
    if await check_owner(i):
        emb = discord.Embed(title="🛒 —— CYBER-STORE MARKET ——", description="👋 ברוכים הבאים!\n🎗️ Supporter: 2,000\n💎 VIP: 5,000\n🛠️ Staff: 15,000", color=0x2b2d31)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("הוקם!", ephemeral=True)

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה")
async def aw(i, member: discord.Member, reason: str):
    if await check_owner(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5)")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def cl(i, amount: int):
    if await check_owner(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="mute", description="[OWNER] השתקת משתמש")
async def mu(i, member: discord.Member, minutes: int):
    if await check_owner(i):
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message("הושתק.")

@bot.tree.command(name="kick", description="[OWNER] העפת משתמש")
async def ki(i, member: discord.Member):
    if await check_owner(i):
        await member.kick(); await i.response.send_message("הועף.")

@bot.tree.command(name="ban", description="[OWNER] הרחקת משתמש")
async def ba(i, member: discord.Member):
    if await check_owner(i):
        await member.ban(); await i.response.send_message("הורחק.")

@bot.tree.command(name="add_money", description="[OWNER] הוספת כסף")
async def am(i, member: discord.Member, amount: int):
    if await check_owner(i):
        user_balances[member.id] += amount; await i.response.send_message(f"הוספו {amount} מטבעות.")

# --- פקודות משתמש ---
@bot.tree.command(name="rank", description="[USER] בדיקת רמה")
async def ra(i): await i.response.send_message(f"📊 רמה: {user_levels[i.user.id]} | XP: {user_xp[i.user.id]}", ephemeral=True)

@bot.tree.command(name="bal", description="[USER] בדיקת יתרה")
async def bl(i): await i.response.send_message(f"💰 יתרה: {user_balances[i.user.id]}", ephemeral=True)

@bot.tree.command(name="report", description="[USER] דיווח")
async def rep(i, member: discord.Member, reason: str):
    await i.guild.get_channel(REPORT_LOG_CH_ID).send(f"🚨 דיווח על {member.mention}: {reason}"); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="recommend", description="[USER] המלצה")
async def rec(i, text: str):
    await i.guild.get_channel(RECOMMEND_CH_ID).send(f"⭐ המלצה: {text}"); await i.response.send_message("תודה", ephemeral=True)

@bot.tree.command(name="ping", description="[USER] מהירות")
async def pi(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms", ephemeral=True)

bot.run(TOKEN)
