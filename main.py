import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs (הכל מעודכן לפי מה שנתת לי) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג פריצות
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
FEEDBACK_CH_ID = 1503475379942461522  # לוג פידבקים/מועמדות
REPORT_LOG_CH_ID = 1501946934779449505 # לוג דיווחים
MEMBER_ROLE_ID = 1501983948111352091   # רול אימות

# רולים של החנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה
user_balances = defaultdict(int)
user_warnings = defaultdict(int)

# --- מערכת הגנה קשוחה (ענישה אוטומטית) ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    await i.response.send_message(f"❌ {i.user.mention}, אין לך גישה! הניסיון דווח והתקבלת אזהרה.", ephemeral=True)
    
    user_warnings[i.user.id] += 1
    count = user_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        emb = discord.Embed(title="🚨 ניסיון פריצה למערכת", color=0xff0000)
        emb.add_field(name="משתמש:", value=f"{i.user.mention} ({i.user.id})")
        emb.add_field(name="פקודה:", value=f"`/{i.command.name}`")
        emb.add_field(name="אזהרה:", value=f"{count}/5")
        await log_ch.send(embed=emb)

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="ניסיון שימוש בפקודות אונר")
    elif count >= 5:
        await i.user.kick(reason="ניסיונות פריצה חוזרים")
        user_warnings[i.user.id] = 0
    return False

# --- מערכת חנות (עיצוב כהה) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh_1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER, "Supporter")

    @ui.button(label="VIP 💎", style=discord.ButtonStyle.secondary, custom_id="sh_2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP, "VIP")

    @ui.button(label="Ticket-Staff 🛠️", style=discord.ButtonStyle.secondary, custom_id="sh_3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF, "Ticket-Staff")

    @ui.button(label="בדיקת יתרה 💰", style=discord.ButtonStyle.success, custom_id="sh_bal")
    async def b4(self, i, b):
        await i.response.send_message(f"💰 יתרה נוכחית: `{user_balances[i.user.id]}`", ephemeral=True)

    async def buy(self, i, p, r_id, r_name):
        if user_balances[i.user.id] < p:
            return await i.response.send_message(f"❌ חסר לך כסף! מחיר: `{p}`", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message(f"✅ תתחדש על רול {r_name}!", ephemeral=True)

# --- מערכת אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="לחץ לאימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("אומתת בהצלחה!", ephemeral=True)

# --- מועמדות ופידבק (אנונימי ומעוצב) ---
class StaffApplyModal(ui.Modal, title="📝 הגשת מועמדות לצוות"):
    age = ui.TextInput(label="גיל", min_length=1, max_length=2)
    pos = ui.TextInput(label="תפקיד מבוקש")
    exp = ui.TextInput(label="ניסיון קודם", style=discord.TextStyle.paragraph)
    why = ui.TextInput(label="למה כדאי לבחור בך?", style=discord.TextStyle.paragraph)

    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        emb = discord.Embed(title="✨ מועמדות חדשה לצוות", color=0x2b2d31, timestamp=datetime.utcnow())
        emb.set_author(name=f"{i.user}", icon_url=i.user.display_avatar.url)
        emb.add_field(name="גיל:", value=f"`{self.age.value}`")
        emb.add_field(name="תפקיד:", value=f"`{self.pos.value}`")
        emb.add_field(name="ניסיון:", value=f"```\n{self.exp.value}\n```", inline=False)
        emb.add_field(name="למה הוא:", value=f"```\n{self.why.value}\n```", inline=False)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ המועמדות נשלחה!", ephemeral=True)

class FeedbackModal(ui.Modal, title="💬 שלח פידבק"):
    inp = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", min_length=2, max_length=2)

    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip() == "כן"
        emb = discord.Embed(title="💬 פידבק חדש", description=f"```\n{self.inp.value}\n```", color=0x00ffff, timestamp=datetime.utcnow())
        if is_anon: emb.set_author(name="משתמש אנונימי 👻")
        else: emb.set_author(name=f"מאת: {i.user.name}", icon_url=i.user.display_avatar.url)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.primary, custom_id="fb_v")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())
    @ui.button(label="הגשת מועמדות 📝", style=discord.ButtonStyle.secondary, custom_id="st_app")
    async def st(self, i, b): await i.response.send_modal(StaffApplyModal())

# --- ליבת הבוט ---
class ServerGuardian(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(VerifyView()); self.add_view(FeedbackView())
        await self.tree.sync()

bot = ServerGuardian()

# --- פקודות ניהול (אונר בלבד) ---
@bot.tree.command(name="setup_shop")
async def ss(i):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🖤 —— MARKETPLACE —— 🖤", description="🎗️ Supporter: 2k | 💎 VIP: 5k | 🛠️ Staff: 15k", color=0x2b2d31)
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_verify")
async def sv(i):
    if await check_owner_and_punish(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", description="לחץ למטה", color=0x2b2d31), view=VerifyView())
        await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback")
async def sf(i):
    if await check_owner_and_punish(i):
        await i.channel.send(embed=discord.Embed(title="💬 צור קשר", description="פידבקים ומועמדות לצוות", color=0x2b2d31), view=FeedbackView())
        await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="mute")
async def mt(i, member: discord.Member, minutes: int, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.timeout(timedelta(minutes=minutes), reason=reason); await i.response.send_message(f"🔇 הושתק {member.mention}")

@bot.tree.command(name="kick")
async def kk(i, member: discord.Member, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.kick(reason=reason); await i.response.send_message(f"👞 הועף {member.mention}")

@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 נמחקו {amount}", ephemeral=True)

@bot.tree.command(name="add_money")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount; await i.response.send_message(f"💰 נוספו {amount} ל-{member.mention}")

# --- פקודות משתמש ואירועים ---
@bot.tree.command(name="report")
async def rep(i, member: discord.Member, reason: str):
    ch = i.guild.get_channel(REPORT_LOG_CH_ID)
    emb = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.utcnow())
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.add_field(name="מדווח:", value=i.user.mention); emb.add_field(name="נאשם:", value=member.mention)
    emb.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ נשלח", ephemeral=True)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch: await ch.send(embed=discord.Embed(title="⚠️ חשד לאלט", description=f"{member.mention} נוצר לפני פחות מ-7 ימים", color=0xffa500))

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

bot.run(TOKEN)
