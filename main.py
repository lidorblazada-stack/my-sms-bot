import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import asyncio
from collections import defaultdict

# --- IDs והגדרות סופיות (בול לפי מה ששלחת אחי) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443
SECOND_ID = 1493293951959044147

# ערוצים ולוגים
WELCOME_CH_ID = 1501713652217282591 
FEEDBACK_CH_ID = 1503475379942461522
RECOMMEND_CH_ID = 1501947249658429470     # ערוץ המלצות
REPORT_LOG_CH_ID = 1501946934779449505    # לוג דיווחים
OWNER_LOG_CH_ID = 1503496964732354620     # לוג שימוש בפקודות אונר
ALTS_LOG_CH_ID = 1502014872655888554      # לוג הלטים (Anti-Ban)
ALT_DETECTION_LOG = 1503464176599695380   # לוג זיהוי אלטים עם כפתורים

# רולים
MEMBER_ROLE_ID = 1501983948111352091
SUSPICIOUS_ROLE_ID = 1503464176599695380 # רול חשוד (אלט)
MUTE_2DAYS_ROLE_ID = 1501953906736103535 # רול מיוט יומיים
OWNER_CMD_ROLE_ID = 1502014872655888554

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה-בייס בזיכרון
user_warnings = defaultdict(int)
user_balances = defaultdict(int)
spam_tracker = defaultdict(list)

# --- פונקציות עזר ולוגים ---

async def log_to_owner(guild, message):
    ch = guild.get_channel(OWNER_LOG_CH_ID)
    if ch: await ch.send(f"⚠️ **לוג ניהול:** {message}")

async def apply_punishment(interaction, member, count, reason):
    if count == 1:
        return f"⚠️ {member.mention}, זוהי **אזהרה מילולית** ראשונה. סיבה: {reason}"
    elif count == 2:
        return f"🚨 {member.mention}, זוהי **אזהרה רשמית**. פעם הבאה תושתק! סיבה: {reason}"
    elif count == 3:
        role = interaction.guild.get_role(MUTE_2DAYS_ROLE_ID)
        if role:
            await member.add_roles(role)
            try: await member.send(f"🔇 הושתקת ליומיים בשרת {interaction.guild.name}. המיוט יוסר אוטומטית בעוד 48 שעות.")
            except: pass
            # תזמון הסרה אוטומטית (48 שעות)
            async def auto_unmute():
                await asyncio.sleep(172800)
                if role in member.roles: await member.remove_roles(role)
            asyncio.create_task(auto_unmute())
        return f"🔇 {member.mention} הגיע ל-3 אזהרות והושתק ליומיים!"
    elif count >= 5:
        try: await member.send(f"👢 הועפת מהשרת (5 אזהרות).")
        except: pass
        await member.kick(reason="5 אזהרות")
        user_warnings[member.id] = 0
        return f"👢 {member.mention} הועף מהשרת!"
    return f"⚠️ {member.mention} הוזהר ({count}/5). סיבה: {reason}"

# --- Views (אלטים, חנות, פידבק, אימות) ---

class AltControlView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.green)
    async def keep(self, i: discord.Interaction, b: ui.Button):
        role = i.guild.get_role(SUSPICIOUS_ROLE_ID)
        if role: await self.member.remove_roles(role)
        await i.response.send_message(f"החשוד {self.member.mention} אושר בשרת.", ephemeral=True)
        self.stop()

    @ui.button(label="להעיף 👢", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i: discord.Interaction, b: ui.Button):
        await self.member.kick(reason="זוהה כאלט חשוד")
        await i.response.send_message(f"האלט {self.member.name} הועף מהשרת.", ephemeral=True)
        self.stop()

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_v1")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת! 🔥", ephemeral=True)

class FeedbackModal(ui.Modal, title="📤 שלח פידבק"):
    inp = ui.TextInput(label="תוכן", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="כן", required=False)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip().lower() == "כן"
        emb = discord.Embed(title="💬 פידבק", description=self.inp.value, color=0x00ffff)
        if not is_anon: emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        else: emb.set_author(name="משתמש אנונימי")
        await ch.send(embed=emb); await i.response.send_message("נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💥", style=discord.ButtonStyle.green, custom_id="fb_v1")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supp", row=0)
    async def b1(self, i, b): await self.handle_buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def b2(self, i, b): await self.handle_buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def b3(self, i, b): await self.handle_buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop:bal", row=1)
    async def b4(self, i, b):
        bal = user_balances.get(i.user.id, 0)
        await i.response.send_message(f"💰 יתרה: `{bal}`", ephemeral=True)

    async def handle_buy(self, i, price, role_id):
        bal = user_balances.get(i.user.id, 0)
        if bal < price: return await i.response.send_message("❌ אין מספיק כסף!", ephemeral=True)
        role = i.guild.get_role(role_id)
        if role in i.user.roles: return await i.response.send_message("❌ כבר יש לך!", ephemeral=True)
        user_balances[i.user.id] -= price
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש על {role.name}!", ephemeral=True)

# --- Bot Core ---
class CyberBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView()); self.add_view(ShopView())
        await self.tree.sync()

bot = CyberBot()

# --- איוונטים (Anti-Ban, Welcome, Anti-Alt, Spam) ---

@bot.event
async def on_member_remove(m):
    if m.id in [MY_USER_ID, SECOND_ID]:
        async for entry in m.guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == m.id:
                await m.guild.unban(m)
                ch = m.guild.get_channel(ALTS_LOG_CH_ID)
                if ch: await ch.send(f"🚨 **Anti-Ban:** הבאן ל-{m.name} בוטל!")

@bot.event
async def on_member_join(m):
    # 1. Anti-Alt
    account_age = (datetime.utcnow() - m.created_at).days
    if account_age < 30:
        role = m.guild.get_role(SUSPICIOUS_ROLE_ID)
        if role: await m.add_roles(role)
        ch_alt = m.guild.get_channel(ALT_DETECTION_LOG)
        if ch_alt:
            emb = discord.Embed(title="🛡️ חשבון חשוד זוהה", color=0xffa500)
            emb.add_field(name="משתמש", value=f"{m.mention}")
            emb.add_field(name="גיל חשבון", value=f"{account_age} ימים")
            await ch_alt.send(embed=emb, view=AltControlView(m))
    
    # 2. Welcome
    ch_w = m.guild.get_channel(WELCOME_CH_ID)
    if ch_w:
        emb = discord.Embed(description=f"Welcome {m.mention}, מס' {m.guild.member_count}.\nDeveloped by NL 👑", color=0xff4500)
        await ch_w.send(content=m.mention, embed=emb)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    now = asyncio.get_event_loop().time()
    spam_tracker[msg.author.id].append(now)
    if len([t for t in spam_tracker[msg.author.id] if now - t < 3]) > 5:
        await msg.author.timeout(timedelta(minutes=10))
        return await msg.channel.send(f"🔇 {msg.author.mention} הושתק (ספאם).", delete_after=5)
    user_balances[msg.author.id] += 10
    await bot.process_commands(msg)

# --- פקודות הקמה ---
@bot.tree.command(name="setup_verify", description="הקמת אימות")
async def sv(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פידבק")
async def sf(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="💬 פידבק אנונימי", color=0x00ffff), view=FeedbackView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_shop", description="הקמת חנות")
async def ss(i):
    if i.user.id == MY_USER_ID:
        emb = discord.Embed(title="═══ 💠 CYBER-STORE 💠 ═══", color=0x2b2d31)
        emb.add_field(name="🎗️ Supporter", value="`2,000`", inline=True); emb.add_field(name="💎 VIP", value="`5,000`", inline=True)
        emb.add_field(name="🛠️ Ticket Staff", value="`15,000`", inline=False)
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("בוצע", ephemeral=True)

# --- פקודות משתמשים ---
@bot.tree.command(name="recommend", description="שלח המלצה")
async def rc(i, text: str):
    ch = i.guild.get_channel(RECOMMEND_CH_ID)
    emb = discord.Embed(title="⭐ המלצה", description=text, color=0xffff00)
    emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="report", description="שלח דיווח")
async def rp(i, text: str):
    ch = i.guild.get_channel(REPORT_LOG_CH_ID)
    emb = discord.Embed(title="🚨 דיווח", description=text, color=0xff0000)
    emb.set_author(name=i.user.name)
    if ch: await ch.send(embed=emb)
    await i.response.send_message("נשלח", ephemeral=True)

# --- פקודות אונר ---
@bot.tree.command(name="add_warn", description="הוסף אזהרה")
async def aw(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warnings[member.id] += 1
    res = await apply_punishment(i, member, user_warnings[member.id], reason)
    await i.response.send_message(res)
    await log_to_owner(i.guild, f"{i.user.name} הזהיר את {member.name}. סיבה: {reason}")

@bot.tree.command(name="add_money", description="הוסף כסף")
async def am(i, member: discord.Member, amount: int):
    if i.user.id == MY_USER_ID:
        user_balances[member.id] += amount
        await i.response.send_message(f"נוספו {amount} ל-{member.mention}")
        await log_to_owner(i.guild, f"{i.user.name} הוסיף כסף ל-{member.name}")

@bot.tree.command(name="clear", description="נקה הודעות")
async def cl(i, amount: int):
    if i.user.id == MY_USER_ID: await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

bot.run(TOKEN)
