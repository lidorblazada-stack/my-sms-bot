import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
import asyncio
from collections import defaultdict

# --- IDs והגדרות ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443
SECOND_ID = 1493293951959044147

# ערוצים
WELCOME_CH_ID = 1501713652217282591 
FEEDBACK_CH_ID = 1503475379942461522
RECOMMEND_CH_ID = 1501947249658429470     
REPORT_LOG_CH_ID = 1501946934779449505    
OWNER_LOG_CH_ID = 1503496964732354620     
ALTS_LOG_CH_ID = 1502014872655888554      
ALT_DETECTION_LOG = 1503464176599695380   

# רולים
MEMBER_ROLE_ID = 1501983948111352091
SUSPICIOUS_ROLE_ID = 1503464176599695380 
MUTE_2DAYS_ROLE_ID = 1501953906736103535 
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה-בייס בזיכרון
user_warnings = defaultdict(int)     # אזהרות כלליות (שומר השרת)
spam_punish_count = defaultdict(int) # אזהרות ספאם ספציפיות
user_balances = defaultdict(int)
user_xp = defaultdict(int)
user_levels = defaultdict(int)
spam_tracker = defaultdict(list)
last_xp_time = {}

def xp_for_level(level):
    return 100 * (level ** 2) + 500

# --- פונקציות עזר ---
async def log_to_owner(guild, message):
    ch = guild.get_channel(OWNER_LOG_CH_ID)
    if ch: await ch.send(f"⚠️ **לוג ניהול:** {message}")

async def apply_general_punishment(interaction, member, count, reason):
    # מערכת הענישה המקורית של שומר השרת
    if count == 1: return f"⚠️ {member.mention}, אזהרה מילולית ראשונה. סיבה: {reason}"
    elif count == 2: return f"🚨 {member.mention}, אזהרה רשמית. פעם הבאה מיוט! סיבה: {reason}"
    elif count == 3:
        role = interaction.guild.get_role(MUTE_2DAYS_ROLE_ID)
        if role:
            await member.add_roles(role)
            try: await member.send(f"🔇 הושתקת ליומיים בשרת {interaction.guild.name}. המיוט יוסר אוטומטית.")
            except: pass
            async def auto_unmute():
                await asyncio.sleep(172800)
                if role in member.roles: await member.remove_roles(role)
            asyncio.create_task(auto_unmute())
        return f"🔇 {member.mention} הושתק ליומיים (3 אזהרות)."
    elif count >= 5:
        await member.kick(reason="5 אזהרות")
        return f"👢 {member.mention} הועף מהשרת!"
    return f"⚠️ {member.mention} הוזהר ({count}/5)."

# --- Views ---

class FeedbackReplyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.green, custom_id="fb_reply_btn")
    async def fast_fb(self, i, b): await i.response.send_modal(FeedbackModal())

class FeedbackModal(ui.Modal, title="📤 שלח פידבק"):
    inp = ui.TextInput(label="תוכן", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="כן")
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip().lower() == "כן"
        emb = discord.Embed(title="💬 פידבק חדש", description=self.inp.value, color=0x00ffff)
        if not is_anon: emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        else: emb.set_author(name="משתמש אנונימי")
        await ch.send(embed=emb, view=FeedbackReplyView()) # כפתור מתחת לכל פידבק
        await i.response.send_message("נשלח!", ephemeral=True)

class AltControlView(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.green)
    async def keep(self, i, b):
        role = i.guild.get_role(SUSPICIOUS_ROLE_ID)
        if role: await self.member.remove_roles(role)
        await i.response.send_message(f"אושר.", ephemeral=True)
    @ui.button(label="להעיף 👢", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        await self.member.kick(reason="אלט")
        await i.response.send_message(f"הועף.", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="v_1")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role); await i.response.send_message("אומתת!", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLE_SUPPORTER)
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLE_VIP)
    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLE_TICKET_STAFF)
    @ui.button(label="יתרה 💳", style=discord.ButtonStyle.success, row=1)
    async def b4(self, i, b): await i.response.send_message(f"💰 יתרה: `{user_balances[i.user.id]}`", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances[i.user.id] < p: return await i.response.send_message("❌ חסר כסף", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

# --- Main Bot ---
class CyberUltimateBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackReplyView()); self.add_view(ShopView())
        await self.tree.sync()

bot = CyberUltimateBot()

@bot.event
async def on_member_join(m):
    age = (datetime.utcnow() - m.created_at).days
    if age < 30:
        role = m.guild.get_role(SUSPICIOUS_ROLE_ID)
        if role: await m.add_roles(role)
        ch = m.guild.get_channel(ALT_DETECTION_LOG)
        if ch: await ch.send(embed=discord.Embed(title="🛡️ אלט זוהה", description=f"{m.mention} ({age} ימים)"), view=AltControlView(m))
    ch_w = m.guild.get_channel(WELCOME_CH_ID)
    if ch_w: await ch_w.send(f"Welcome {m.mention}! Developed by NL 👑")

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    u_id = msg.author.id
    now_time = asyncio.get_event_loop().time()
    
    # --- מערכת אנטי-ספאם עם ענישה מדורגת ---
    spam_tracker[u_id].append(now_time)
    spam_tracker[u_id] = [t for t in spam_tracker[u_id] if now_time - t < 5]
    
    if len(spam_tracker[u_id]) > 5:
        spam_punish_count[u_id] += 1
        count = spam_punish_count[u_id]
        
        if count == 1:
            try:
                await msg.author.timeout(timedelta(minutes=1), reason="ספאם - אזהרה מילולית")
                await msg.channel.send(f"⚠️ {msg.author.mention}, **אזהרה מילולית!** אל תספים. קיבלת דקה טיימאוט.")
            except: pass
            return # אין כסף ואין XP בספאם
        elif count == 2:
            await msg.channel.send(f"🚨 {msg.author.mention}, **אזהרה רשמית!** הפסק להספים מיד.")
            return
        elif count >= 3:
            # מעבר למערכת הענישה הכבדה
            user_warnings[u_id] += 1
            res = await apply_general_punishment(msg, msg.author, user_warnings[u_id], "ספאם חוזר")
            await msg.channel.send(res)
            return

    # --- חנות ורמות (רק אם לא ספאם) ---
    user_balances[u_id] += 10
    
    now_dt = datetime.utcnow()
    if u_id not in last_xp_time or now_dt > last_xp_time[u_id] + timedelta(seconds=30):
        last_xp_time[u_id] = now_dt
        user_xp[u_id] += 20
        lvl = user_levels[u_id]
        if user_xp[u_id] >= xp_for_level(lvl + 1):
            user_levels[u_id] += 1
            await msg.channel.send(f"🎊 {msg.author.mention} עלית לרמה **{lvl + 1}**! 🔥")

    await bot.process_commands(msg)

# --- פקודות אונר ---
@bot.tree.command(name="setup_verify")
async def sv(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback")
async def sf(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="💬 פידבק"), view=FeedbackReplyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_shop")
async def ss(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="🛒 חנות"), view=ShopView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="add_warn")
async def aw(i, member: discord.Member, reason: str):
    if i.user.id == MY_USER_ID:
        user_warnings[member.id] += 1
        res = await apply_general_punishment(i, member, user_warnings[member.id], reason)
        await i.response.send_message(res)

# --- פקודות משתמש ---
@bot.tree.command(name="rank", description="בדוק רמה")
async def rank(i, member: discord.Member = None):
    t = member or i.user
    lvl = user_levels[t.id]
    xp = user_xp[t.id]
    needed = xp_for_level(lvl + 1)
    emb = discord.Embed(title=f"📊 {t.name}", description=f"רמה: **{lvl}**\nXP: `{xp}/{needed}`", color=0x3498db)
    await i.response.send_message(embed=emb)

bot.run(TOKEN)
