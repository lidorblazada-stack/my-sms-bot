import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs (אל תשכח לשים את הטוקן שלך ב-Render) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג ניסיונות פריצה
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה-בייס בזיכרון
user_balances = defaultdict(int)
user_warnings = defaultdict(int)

# --- פונקציית הגנה וענישה על פקודות אונר ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    # 1. אזהרה מילולית מיידית
    await i.response.send_message(f"❌ {i.user.mention}, אסור לך להשתמש בפקודה הזאת! זו אזהרה מילולית.", ephemeral=True)
    
    # 2. רישום אזהרה רשמית
    user_warnings[i.user.id] += 1
    count = user_warnings[i.user.id]
    
    # לוג לאונר
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        await log_ch.send(f"⚠️ **ניסיון פריצה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה מס' {count}")

    # 3. ענישה אוטומטית לפי מה שביקשת
    if count == 3:
        try:
            await i.user.send("⚠️ קיבלת מיוט ליומיים כי ניסית להשתמש בפקודות אונר ללא הרשאה 3 פעמים.")
        except: pass
        await i.user.timeout(timedelta(days=2), reason="3 ניסיונות לשימוש בפקודות אונר")
        
    elif count >= 5:
        try:
            await i.user.send("👞 הועפת מהשרת עקב ניסיונות חוזרים לפרוץ למערכת הפקודות.")
        except: pass
        await i.user.kick(reason="5 ניסיונות לשימוש בפקודות אונר")
        user_warnings[i.user.id] = 0 # איפוס לאחר קיק

    return False

# --- Shop View (חנות מעוצבת) ---
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
        await i.response.send_message(f"💰 היתרה שלך היא: `{user_balances[i.user.id]}` מטבעות.", ephemeral=True)

    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p:
            return await i.response.send_message("❌ אין לך מספיק מטבעות!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש! הרכישה בוצעה.", ephemeral=True)

# --- Bot Setup ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView())
        await self.tree.sync()

bot = CyberShield()

# מערכת אלטים (חשבונות חדשים מ-7 ימים)
@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch:
            await ch.send(f"⚠️ **חשבון חשוד (Alt):** {member.mention} נרשם לפני פחות מ-7 ימים.")

# מערכת כסף (5 מטבעות להודעה)
@bot.event
async def on_message(msg):
    if not msg.author.bot:
        user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

# --- פקודות אונר בלבד (מוגנות) ---

@bot.tree.command(name="setup_shop", description="[OWNER] הקמת החנות המעוצבת")
async def ss(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(
            title="🛒 —— CYBER-STORE MARKET ——",
            description=(
                "🎗️ **Server-Supporter** | 2,000 Coins\n"
                "💎 **VIP Member** | 5,000 Coins\n"
                "🛠️ **Ticket-Staff** | 15,000 Coins"
            ),
            color=0x2b2d31
        )
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("החנות הוקמה בהצלחה!", ephemeral=True)

@bot.tree.command(name="add_money", description="[OWNER] הוספת כסף למשתמש")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"✅ הוספת {amount} מטבעות ל-{member.mention}.")

@bot.tree.command(name="remove_money", description="[OWNER] הורדת כסף למשתמש")
async def rm(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] -= amount
        await i.response.send_message(f"✅ הורדת {amount} מטבעות מ-{member.mention}.")

@bot.tree.command(name="add_warn", description="[OWNER] מתן אזהרה רגילה")
async def aw(i, member: discord.Member, reason: str):
    if await check_owner_and_punish(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} קיבל אזהרה. סיבה: {reason} (סך הכל: {user_warnings[member.id]})")

@bot.tree.command(name="clear", description="[OWNER] ניקוי צ'אט")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"נמחקו {amount} הודעות.", ephemeral=True)

bot.run(TOKEN)
