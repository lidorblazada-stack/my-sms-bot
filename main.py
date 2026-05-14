import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג ניסיונות פריצה
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
FEEDBACK_CH_ID = 1503475379942461522  # ערוץ פידבקים/המלצות
REPORT_LOG_CH_ID = 1501946934779449505 # לוג דיווחים

# רולים
MEMBER_ROLE_ID = 1501983948111352091
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה (במציאות כדאי להשתמש ב-Database, אבל כאן זה בזיכרון)
user_balances = defaultdict(int)
user_warnings = defaultdict(int)
attack_warnings = defaultdict(int) # אזהרות למי שמנסה לפרוץ פקודות אונר

# --- פונקציית הגנה: בדיקת אונר + ענישה אוטומטית ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    # אזהרה מילולית מיידית
    await i.response.send_message(f"❌ {i.user.mention}, זו אזהרה מילולית! אין לך גישה לפקודות אונר.", ephemeral=True)
    
    attack_warnings[i.user.id] += 1
    count = attack_warnings[i.user.id]
    
    # לוג לאונר
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        await log_ch.send(f"⚠️ **ניסיון גישה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה: {count}/5")

    if count == 3:
        try: await i.user.send("⚠️ הושתקת ליומיים עקב ניסיונות חוזרים להשתמש בפקודות אונר.")
        except: pass
        await i.user.timeout(timedelta(days=2), reason="3 ניסיונות שימוש בפקודות אונר")
        
    elif count >= 5:
        try: await i.user.send("👞 הועפת מהשרת עקב ניסיונות פריצה למערכת.")
        except: pass
        await i.user.kick(reason="5 ניסיונות שימוש בפקודות אונר")
        attack_warnings[i.user.id] = 0

    return False

# --- ממשקי כפתורים (Views) ---

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.success, custom_id="shop_1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop_2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop_3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.secondary, custom_id="shop_4")
    async def b4(self, i, b):
        await i.response.send_message(f"💰 היתרה שלך: `{user_balances[i.user.id]}` מטבעות.", ephemeral=True)

    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p:
            return await i.response.send_message("❌ אין לך מספיק מטבעות!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש! הרול נוסף.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_v1")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView())
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        user_balances[msg.author.id] += 5 # 5 מטבעות לכל הודעה
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ חשבון חשוד (Alt): {member.mention} נרשם לפני פחות משבוע.")

# --- פקודות אונר (ניהול והקמה) ---

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת החנות")
async def ss(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🛒 —— CYBER-STORE MARKET ——", 
                            description="🎗️ **Supporter**: 2,000\n💎 **VIP**: 5,000\n🛠️ **Staff**: 15,000", 
                            color=0x2b2d31)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("חנות הוקמה", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[OWNER] הקמת אימות")
async def sv(i):
    if await check_owner_and_punish(i):
        await i.channel.send("🛡️ לחץ על הכפתור כדי להתאמת לשרת", view=VerifyView())
        await i.response.send_message("אימות הוקם", ephemeral=True)

@bot.tree.command(name="add_money", description="[OWNER] הוספת כסף")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"✅ נוספו {amount} ל-{member.mention}")

@bot.tree.command(name="remove_money", description="[OWNER] הורדת כסף")
async def rm(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] -= amount
        await i.response.send_message(f"✅ הורדו {amount} מ-{member.mention}")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"נמחקו {amount} הודעות", ephemeral=True)

@bot.tree.command(name="kick", description="[OWNER] העפת משתמש")
async def ki(i, member: discord.Member):
    if await check_owner_and_punish(i):
        await member.kick(); await i.response.send_message(f"{member.name} הועף")

@bot.tree.command(name="ban", description="[OWNER] הרחקת משתמש")
async def ba(i, member: discord.Member):
    if await check_owner_and_punish(i):
        await member.ban(); await i.response.send_message(f"{member.name} הורחק")

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה")
async def aw(i, member: discord.Member, reason: str):
    if await check_owner_and_punish(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! ({user_warnings[member.id]}/5)")

# --- פקודות משתמש ---

@bot.tree.command(name="report", description="[USER] דיווח על משתמש")
async def rep(i, member: discord.Member, reason: str):
    log = i.guild.get_channel(REPORT_LOG_CH_ID)
    if log: await log.send(f"🚨 דיווח מ{i.user.mention} על {member.mention}: {reason}")
    await i.response.send_message("הדיווח נשלח", ephemeral=True)

@bot.tree.command(name="recommend", description="[USER] המלצה לשרת")
async def rec(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"⭐ המלצה חדשה מ{i.user.mention}: {text}")
    await i.response.send_message("תודה על ההמלצה!", ephemeral=True)

@bot.tree.command(name="ping", description="[USER] מהירות הבוט")
async def pi(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms", ephemeral=True)

bot.run(TOKEN)
