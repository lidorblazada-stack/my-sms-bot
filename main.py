import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import asyncio
from collections import defaultdict

# --- הגדרות ו-IDs (לפי התמונות שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443 

# ערוצים
WELCOME_CH_ID = 1501713652217282591
FEEDBACK_CH_ID = 1503475379942461522
RECOMMEND_CH_ID = 1501947249658429470     
REPORT_LOG_CH_ID = 1501946934779449505    
OWNER_LOG_CH_ID = 1503496964732354620     
ALT_LOG_CH_ID = 1503464176599695380  # ערוץ לוג אלטים חשודים

# רולים
MEMBER_ROLE_ID = 1501983948111352091
SUSPICIOUS_ROLE_ID = 1503464176599695380 
MUTE_2DAYS_ROLE_ID = 1501953906736103535 

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה-בייס בזיכרון
user_warnings = defaultdict(int)
user_balances = defaultdict(int)
user_xp = defaultdict(int)
user_levels = defaultdict(int)
spam_tracker = defaultdict(list)

# --- פונקציות לוג ---
async def send_owner_log(guild, user, command_name, details=""):
    ch = guild.get_channel(OWNER_LOG_CH_ID)
    if ch:
        emb = discord.Embed(title="👑 Owner Action Log", color=0xffd700, timestamp=datetime.utcnow())
        emb.add_field(name="מבצע", value=f"{user.mention}")
        emb.add_field(name="פקודה", value=f"`/{command_name}`")
        if details: emb.add_field(name="פרטים", value=details)
        await ch.send(embed=emb)

# --- Views & Modals ---

class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id
    @ui.button(label="Ban 🔨", style=discord.ButtonStyle.danger)
    async def b(self, i, b):
        m = i.guild.get_member(self.member_id)
        if m: await m.ban(reason="Alt detected"); await i.response.send_message("הורחק!", ephemeral=True)
    @ui.button(label="Trust ✅", style=discord.ButtonStyle.success)
    async def t(self, i, b):
        await i.response.send_message("סומן כבטוח", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh4")
    async def b4(self, i, b): await i.response.send_message(f"💰 יתרה: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ אין כסף", ephemeral=True)
        user_balances[i.user.id] -= p
        role = i.guild.get_role(r_id); await i.user.add_roles(role)
        await i.response.send_message("✅ נרכש בהצלחה!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_main")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID); await i.user.add_roles(role)
        await i.response.send_message("אומתת!", ephemeral=True)

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- מערכת זיהוי אלטים חשודים ---
@bot.event
async def on_member_join(member):
    now = datetime.utcnow()
    diff = now - member.created_at
    # אם החשבון נפתח לפני פחות מ-7 ימים
    if diff.days < 7:
        ch = member.guild.get_channel(ALT_LOG_CH_ID)
        if ch:
            emb = discord.Embed(title="⚠️ זיהוי משתמש חשוד (Alt)", color=0xffa500)
            emb.add_field(name="משתמש", value=f"{member.mention} ({member.name})")
            emb.add_field(name="נוצר לפני", value=f"{diff.days} ימים")
            await ch.send(embed=emb, view=AltActionView(member.id))
            # הוספת רול חשוד
            role = member.guild.get_role(SUSPICIOUS_ROLE_ID)
            if role: await member.add_roles(role)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    user_balances[msg.author.id] += 10
    user_xp[msg.author.id] += 15
    await bot.process_commands(msg)

# --- פקודות אונר ---

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת חנות הרולים")
async def ss(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send("🛒 חנות Cyber Shield", view=ShopView()); await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[OWNER] הקמת מערכת האימות")
async def sv(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send("🛡️ מערכת אימות", view=VerifyView()); await i.response.send_message("הוקם", ephemeral=True)

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה למשתמש")
async def aw(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warnings[member.id] += 1
    await i.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5). סיבה: {reason}")
    if user_warnings[member.id] >= 3:
        r = i.guild.get_role(MUTE_2DAYS_ROLE_ID)
        if r: await member.add_roles(r)

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def cl(i, amount: int):
    if i.user.id != MY_USER_ID: return
    await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="mute", description="[OWNER] השתקת משתמש")
async def mu(i, member: discord.Member, minutes: int):
    if i.user.id != MY_USER_ID: return
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"הושתק ל-{minutes} דקות")

# --- פקודות משתמש ---

@bot.tree.command(name="rank", description="[USER] בדיקת הרמה שלך")
async def ra(i): await i.response.send_message(f"📊 רמה: {user_levels[i.user.id]} | XP: {user_xp[i.user.id]}", ephemeral=True)

@bot.tree.command(name="bal", description="[USER] בדיקת יתרה")
async def bl(i): await i.response.send_message(f"💰 יתרה: {user_balances[i.user.id]}", ephemeral=True)

@bot.tree.command(name="report", description="[USER] דיווח על משתמש")
async def rep(i, member: discord.Member, reason: str):
    ch = i.guild.get_channel(REPORT_LOG_CH_ID)
    await ch.send(f"🚨 דיווח מ{i.user.mention} על {member.mention}: {reason}")
    await i.response.send_message("הדיווח נשלח", ephemeral=True)

@bot.tree.command(name="recommend", description="[USER] שליחת המלצה")
async def rec(i, recommendation: str):
    ch = i.guild.get_channel(RECOMMEND_CH_ID)
    await ch.send(f"⭐ המלצה מ{i.user.mention}: {recommendation}")
    await i.response.send_message("תודה!", ephemeral=True)

bot.run(TOKEN)
