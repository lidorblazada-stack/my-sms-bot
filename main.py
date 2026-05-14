import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- IDs והגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  
LOG_CH_ID = 1503496964732354620       
ALT_LOG_ID = 1503464176599695380      
SUSPECT_ROLE_ID = 1503464176599695380 
REPORT_LOG_CH_ID = 1501946934779449505
FEEDBACK_CH_ID = 1503475379942461522
MEMBER_ROLE_ID = 1501983948111352091

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה
user_balances = defaultdict(int)
user_warnings = defaultdict(int) # אזהרות למשתמשים (מודרציה)
attack_warnings = defaultdict(int) # אזהרות על ניסיון פריצה

# --- לוגיקה של הגנה על אונר ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    await i.response.send_message(f"❌ {i.user.mention}, אזהרה מילולית! פקודה לאונרים בלבד.", ephemeral=True)
    attack_warnings[i.user.id] += 1
    count = attack_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch: await log_ch.send(f"⚠️ **ניסיון פריצה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. אזהרה: {count}/5")

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="3 ניסיונות שימוש בפקודות אונר")
        try: await i.user.send("⚠️ הושתקת ליומיים עקב ניסיונות פריצה.")
        except: pass
    elif count >= 5:
        await i.user.kick(reason="5 ניסיונות שימוש בפקודות אונר")
        attack_warnings[i.user.id] = 0
    return False

# --- Views (חנות, אימות, אלטים) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh:sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh:vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh:stf", row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="sh:bal", row=1)
    async def b4(self, i, b):
        await i.response.send_message(f"💰 יתרה: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ חסר כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

class AltActionView(ui.View):
    def __init__(self, mid): super().__init__(timeout=None); self.mid = mid
    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger)
    async def k(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.mid)
        if m: await m.kick(); await i.response.send_message("הועף", ephemeral=True); await i.message.delete()
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def s(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        await i.response.send_message("אושר", ephemeral=True); await i.message.delete()
    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def h(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.mid); r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.response.send_message("ניתן רול חשוד", ephemeral=True); await i.message.delete()

# --- Bot Setup ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(f"⚠️ זיהוי אלט: {member.mention}", view=AltActionView(member.id))

# --- פקודות (15 פקודות) ---

# 1. הקמת חנות
@bot.tree.command(name="setup_shop")
async def setup_shop(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.description = "👋 **ברוכים הבאים לחנות!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        emb.add_field(name="🎗️ | Server-Supporter", value="**Price:** 2,000 Coins", inline=False)
        emb.add_field(name="💎 | VIP Member", value="**Price:** 5,000 Coins", inline=False)
        emb.add_field(name="🛠️ | TICKET-STAFF", value="**Price:** 15,000 Coins", inline=False)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("הוקם", ephemeral=True)

# 2. הקמת אימות
@bot.tree.command(name="setup_verify")
async def setup_verify(i):
    if await check_owner_and_punish(i):
        await i.channel.send("🛡️ לחץ לאימות", view=VerifyView()); await i.response.send_message("הוקם", ephemeral=True)

# 3. הוספת כסף
@bot.tree.command(name="add_money")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount; await i.response.send_message(f"נוספו {amount} ל-{member.mention}")

# 4. הורדת כסף
@bot.tree.command(name="remove_money")
async def rm(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] -= amount; await i.response.send_message(f"הורדו {amount} מ-{member.mention}")

# 5. ניקוי צ'אט
@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"נמחקו {amount}", ephemeral=True)

# 6. קיק
@bot.tree.command(name="kick")
async def ki(i, member: discord.Member, reason: str = "לא צוין"):
    if await check_owner_and_punish(i):
        await member.kick(reason=reason); await i.response.send_message(f"{member.name} הועף")

# 7. באן
@bot.tree.command(name="ban")
async def ba(i, member: discord.Member, reason: str = "לא צוין"):
    if await check_owner_and_punish(i):
        await member.ban(reason=reason); await i.response.send_message(f"{member.name} הורחק")

# 8. מיוט (Timeout)
@bot.tree.command(name="mute")
async def mu(i, member: discord.Member, minutes: int):
    if await check_owner_and_punish(i):
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"{member.name} הושתק ל-{minutes} דקות")

# 9. אזהרה למשתמש
@bot.tree.command(name="warn")
async def wr(i, member: discord.Member, reason: str):
    if await check_owner_and_punish(i):
        user_warnings[member.id] += 1
        await i.response.send_message(f"⚠️ {member.mention} הוזהר! ({user_warnings[member.id]})")

# 10. איפוס אזהרות
@bot.tree.command(name="clear_warns")
async def cw(i, member: discord.Member):
    if await check_owner_and_punish(i):
        user_warnings[member.id] = 0; await i.response.send_message(f"אזהרות של {member.name} אופסו")

# 11. דיווח (User)
@bot.tree.command(name="report")
async def rep(i, member: discord.Member, reason: str):
    log = i.guild.get_channel(REPORT_LOG_CH_ID)
    if log: await log.send(f"🚨 דיווח מ{i.user.mention} על {member.mention}: {reason}")
    await i.response.send_message("דווח בהצלחה", ephemeral=True)

# 12. המלצה (User)
@bot.tree.command(name="recommend")
async def rec(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"⭐ המלצה מ{i.user.mention}: {text}")
    await i.response.send_message("תודה!", ephemeral=True)

# 13. פינג
@bot.tree.command(name="ping")
async def pi(i): await i.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

# 14. סטטיסטיקה אישית
@bot.tree.command(name="stats")
async def st(i):
    await i.response.send_message(f"📊 סטטיסטיקה עבור {i.user.name}:\n💰 כסף: {user_balances[i.user.id]}\n⚠️ אזהרות: {user_warnings[i.user.id]}", ephemeral=True)

# 15. אנונימי (Feedback)
@bot.tree.command(name="anonymous_feedback")
async def af(i, text: str):
    ch = i.guild.get_channel(FEEDBACK_CH_ID)
    if ch: await ch.send(f"🔒 פידבק אנונימי: {text}")
    await i.response.send_message("נשלח אנונימית", ephemeral=True)

bot.run(TOKEN)
