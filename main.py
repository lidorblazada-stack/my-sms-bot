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
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה
user_balances = defaultdict(int)
user_warnings = defaultdict(int)

# --- מערכת הגנה: ענישה אוטומטית על ניסיון פקודת אונר ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    # 1. אזהרה מילולית מיידית
    await i.response.send_message(f"❌ {i.user.mention}, אסור לך להשתמש בפקודה הזאת! זו אזהרה מילולית.", ephemeral=True)
    
    # 2. רישום אזהרה רשמית
    user_warnings[i.user.id] += 1
    count = user_warnings[i.user.id]
    
    # לוג לאונרים
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        await log_ch.send(f"⚠️ ניסיון פריצה: {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה מספר {count}")

    # 3. ענישה אוטומטית
    if count == 3:
        try:
            await i.user.send("⚠️ קיבלת מיוט ליומיים כי ניסית להשתמש בפקודות אונר ללא הרשאה 3 פעמים.")
        except: pass
        await i.user.timeout(timedelta(days=2), reason="ניסיונות חוזרים להשתמש בפקודות אונר")
        
    elif count >= 5:
        try:
            await i.user.send("👞 הועפת מהשרת עקב ניסיונות חוזרים לפרוץ למערכת הפקודות.")
        except: pass
        await i.user.kick(reason="5 ניסיונות לשימוש בפקודות אונר")
        user_warnings[i.user.id] = 0 # איפוס לאחר קיק

    return False

# --- Shop View ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.success, custom_id="sh_s")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_v")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh_t")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.secondary, custom_id="sh_b")
    async def b4(self, i, b):
        await i.response.send_message(f"💰 יתרה: `{user_balances[i.user.id]}`", ephemeral=True)

    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ חסר כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

# --- Bot Hook ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5 # 5 מטבעות להודעה
    await bot.process_commands(msg)

# --- פקודות אונר מוגנות ---

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת החנות")
async def ss(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🛒 —— CYBER-STORE MARKET ——", 
                            description="🎗️ Supporter: 2,000\n💎 VIP: 5,000\n🛠️ Staff: 15,000", color=0x2b2d31)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("חנות הוקמה", ephemeral=True)

@bot.tree.command(name="add_money", description="[OWNER] העלאת כסף")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"✅ הוספת {amount} ל-{member.mention}")

@bot.tree.command(name="remove_money", description="[OWNER] הורדת כסף")
async def rm(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] -= amount
        await i.response.send_message(f"✅ הורדת {amount} מ-{member.mention}")

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה")
async def aw(i, member: discord.Member, reason: str):
    if await check_owner_and_punish(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר. (סך הכל: {user_warnings[member.id]})")

@bot.tree.command(name="clear", description="[OWNER] ניקוי צ'אט")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount); await i.response.send_message("בוצע", ephemeral=True)

bot.run(TOKEN)
