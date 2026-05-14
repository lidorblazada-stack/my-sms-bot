import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs (אל תיגע בזה אם ה-IDs נכונים) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג ניסיונות פריצה
ALT_LOG_ID = 1503464176599695380      # לוג אלטים חשודים
FEEDBACK_CH_ID = 1503475379942461522  # לוג פידבקים והמלצות צוות
REPORT_LOG_CH_ID = 1501946934779449505 # לוג דיווחים על אנשים
MEMBER_ROLE_ID = 1501983948111352091   # רול אימות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה (זמני בזיכרון)
user_balances = defaultdict(int)
user_warnings = defaultdict(int)

# --- מערכת הגנה קשוחה (Anti-Owner Bypass) ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    await i.response.send_message(f"❌ {i.user.mention}, אין לך גישה לפקודות אונר! הניסיון דווח.", ephemeral=True)
    
    user_warnings[i.user.id] += 1
    count = user_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch:
        emb = discord.Embed(title="🚨 ניסיון פריצה למערכת", color=0xff0000)
        emb.add_field(name="משתמש:", value=f"{i.user.mention} ({i.user.id})")
        emb.add_field(name="פקודה:", value=f"`/{i.command.name}`")
        emb.add_field(name="מספר אזהרה:", value=f"{count}/5")
        await log_ch.send(embed=emb)

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="ניסיון שימוש בפקודות אונר")
    elif count >= 5:
        await i.user.kick(reason="ניסיונות פריצה חוזרים למערכת")
        user_warnings[i.user.id] = 0
    return False

# --- מודאלים (חלונות קופצים) ---

class StaffApplyModal(ui.Modal, title="📝 הגשת מועמדות לצוות"):
    age = ui.TextInput(label="בן כמה אתה?", placeholder="גיל...", min_length=1, max_length=2)
    pos = ui.TextInput(label="תפקיד מבוקש", placeholder="ספורטר / מודרייטור / הלפר...")
    exp = ui.TextInput(label="ניסיון קודם", style=discord.TextStyle.paragraph, placeholder="איפה היית צוות בעבר?")
    why = ui.TextInput(label="למה כדאי לנו לבחור בך?", style=discord.TextStyle.paragraph)

    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        emb = discord.Embed(title="✨ —— מועמדות חדשה לצוות —— ✨", color=0x7289da, timestamp=datetime.utcnow())
        emb.set_author(name=f"מועמד: {i.user.name}", icon_url=i.user.display_avatar.url)
        emb.add_field(name="🎂 גיל:", value=f"`{self.age.value}`", inline=True)
        emb.add_field(name="🛠️ תפקיד:", value=f"`{self.pos.value}`", inline=True)
        emb.add_field(name="📚 ניסיון:", value=f"```\n{self.exp.value}\n```", inline=False)
        emb.add_field(name="💡 למה הוא:", value=f"```\n{self.why.value}\n```", inline=False)
        emb.set_footer(text=f"User ID: {i.user.id}")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ המועמדות נשלחה בהצלחה!", ephemeral=True)

class FeedbackModal(ui.Modal, title="💬 שלח פידבק / הצעה"):
    inp = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, placeholder="כתוב כאן...")
    anon = ui.TextInput(label="אנונימי? (כן / לא)", default="לא", min_length=2, max_length=2)

    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip() == "כן"
        emb = discord.Embed(title="💬 פידבק חדש התקבל", description=f"```\n{self.inp.value}\n```", color=0x00ffff, timestamp=datetime.utcnow())
        if is_anon:
            emb.set_author(name="משתמש אנונימי 👻")
        else:
            emb.set_author(name=f"נשלח ע'י: {i.user.name}", icon_url=i.user.display_avatar.url)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("✅ הפידבק נשלח!", ephemeral=True)

# --- Views (כפתורים) ---

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.success, custom_id="sh_1")
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="sh_2")
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="sh_3")
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.secondary, custom_id="sh_bal")
    async def b4(self, i, b): await i.response.send_message(f"💰 היתרה שלך: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ אין לך מספיק כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message(f"✅ תתחדש! קיבלת את הרול.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_btn")
    async def v(self, i, b):
        await i.user.add_roles(i.guild.get_role(MEMBER_ROLE_ID))
        await i.response.send_message("✅ עברת אימות!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.primary, custom_id="fb_v")
    async def fb(self, i, b): await i.response.send_modal(FeedbackModal())
    @ui.button(label="הגשת מועמדות 📝", style=discord.ButtonStyle.secondary, custom_id="st_app")
    async def st(self, i, b): await i.response.send_modal(StaffApplyModal())

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
        if ch: 
            emb = discord.Embed(title="⚠️ חשד למשתמש אלט", color=0xffa500)
            emb.add_field(name="משתמש:", value=f"{member.mention} ({member.id})")
            emb.add_field(name="נוצר לפני:", value=f"{(datetime.utcnow() - member.created_at).days} ימים")
            await ch.send(embed=emb)

@bot.event
async def on_message(msg):
    if not msg.author.bot: user_balances[msg.author.id] += 5
    await bot.process_commands(msg)

# --- פקודות אונר בלבד (Slash Commands) ---

@bot.tree.command(name="setup_shop", description="הקמת חנות")
async def ss(i: discord.Interaction):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🛒 —— CYBER-STORE MARKET ——", description="🎗️ **Supporter Role**: 2,000$\n💎 **VIP Role**: 5,000$\n🛠️ **Staff Role**: 15,000$", color=0x2b2d31)
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("החנות הוקמה!", ephemeral=True)

@bot.tree.command(name="setup_verify", description="הקמת אימות")
async def sv(i: discord.Interaction):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="🛡️ —— מערכת אימות —— 🛡️", description="לחץ על הכפתור למטה כדי לקבל גישה לשרת", color=0x2b2d31)
        await i.channel.send(embed=emb, view=VerifyView())
        await i.response.send_message("מערכת אימות הוקמה!", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פידבק ומועמדות")
async def sf(i: discord.Interaction):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="💬 —— צור קשר עם הצוות —— 💬", description="כאן ניתן לשלוח הצעות לשיפור או להגיש מועמדות לצוות השרת", color=0x2b2d31)
        await i.channel.send(embed=emb, view=FeedbackView())
        await i.response.send_message("מערכת פידבק הוקמה!", ephemeral=True)

@bot.tree.command(name="mute", description="השתקת משתמש")
async def mt(i, member: discord.Member, minutes: int, reason: str = "לא צוינה"):
    if await check_owner_and_punish(i):
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await i.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות. סיבה: {reason}")

@bot.tree.command(name="clear", description="ניקוי הודעות")
async def cl(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"✅ נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="add_money", description="הוספת כסף למשתמש")
async def am(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"✅ נוספו `{amount}` ליתרה של {member.mention}")

# --- פקודות משתמשים (לכולם) ---

@bot.tree.command(name="report", description="דיווח על משתמש שעובר על החוקים")
async def rep(i, member: discord.Member, reason: str):
    ch = i.guild.get_channel(REPORT_LOG_CH_ID)
    emb = discord.Embed(title="🚨 —— דיווח משתמש חדש —— 🚨", color=0xff0000, timestamp=datetime.utcnow())
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.add_field(name="👤 המדווח:", value=f"{i.user.mention} (ID: {i.user.id})", inline=True)
    emb.add_field(name="🚫 הנאשם:", value=f"{member.mention} (ID: {member.id})", inline=True)
    emb.add_field(name="📝 סיבה:", value=f"```\n{reason}\n```", inline=False)
    emb.set_footer(text="CyberShield Security System")
    if ch: await ch.send(embed=emb)
    await i.response.send_message("✅ הדיווח נשלח לצוות הניהול.", ephemeral=True)

bot.run(TOKEN)
