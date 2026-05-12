import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta
import os
import asyncio
from collections import defaultdict

# --- כל ה-IDs שנתת לי (מעודכן סופית) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443  # ה-ID שלך
SECOND_ID = 1493293951959044147   # ID הגנה נוסף

OWNER_CMD_ROLE = 1502014872655888554
MEMBER_ROLE_ID = 1501983948111352091
REPORT_ROLE_ID = 1501946934779449505
RECOMMEND_ROLE_ID = 1501947249658429470
FEEDBACK_ROLE_ID = 1503475379942461522
MUTE_2DAYS_ROLE = 1501953906736103535
SUSPECT_ROLE_ID = 1503464176599695380

# מעקב אזהרות וספאם
user_warnings = defaultdict(int)
spam_tracker = defaultdict(list)

# --- מערכות כפתורים ואימות ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="אימות וכניסה ✅", style=discord.ButtonStyle.green, custom_id="v_final")
    async def v(self, i: discord.Interaction, b: ui.Button):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role: await i.user.add_roles(role)
        await i.response.send_message("אומתת! קיבלת רול Member.", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.blurple, custom_id="f_btn")
    async def f(self, i, b): await i.response.send_modal(InputModal("פידבק", FEEDBACK_ROLE_ID))
    @ui.button(label="שלח המלצה ⭐", style=discord.ButtonStyle.success, custom_id="r_btn")
    async def r(self, i, b): await i.response.send_modal(InputModal("המלצה", RECOMMEND_ROLE_ID))

class ReportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="דווח על שחקן 👤", style=discord.ButtonStyle.danger, custom_id="rep_player")
    async def rp(self, i, b): await i.response.send_modal(InputModal("דיווח על שחקן", REPORT_ROLE_ID))
    @ui.button(label="דווח על איש צוות 🛠️", style=discord.ButtonStyle.secondary, custom_id="rep_staff")
    async def rs(self, i, b): await i.response.send_modal(InputModal("דיווח על איש צוות", REPORT_ROLE_ID))

class InputModal(ui.Modal):
    def __init__(self, title, role_id):
        super().__init__(title=title)
        self.role_id = role_id
        self.inp = ui.TextInput(label="פרטים", style=discord.TextStyle.paragraph)
        self.add_item(self.inp)
    async def on_submit(self, i: discord.Interaction):
        role = i.guild.get_role(self.role_id)
        emb = discord.Embed(title=f"קבלת {self.title}", description=self.inp.value, color=0x00ffff)
        emb.set_author(name=i.user.name, icon_url=i.user.avatar.url if i.user.avatar else None)
        await i.channel.send(content=role.mention if role else "", embed=emb)
        await i.response.send_message("נשלח בהצלחה!", ephemeral=True)

class NLShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView()); self.add_view(ReportView())
        await self.tree.sync()

bot = NLShield()

async def is_owner(i: discord.Interaction):
    if i.user.id == MY_USER_ID or any(role.id == OWNER_CMD_ROLE for role in i.user.roles): return True
    await i.response.send_message("🚫 אין גישה!", ephemeral=True); return False

# --- הגנה עצמית (Anti-Ban) ---
@bot.event
async def on_member_remove(member):
    if member.id in [MY_USER_ID, SECOND_ID]:
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == member.id:
                await member.guild.unban(member)
                inv = await member.guild.text_channels[0].create_invite(max_uses=1, unique=True)
                try:
                    u = await bot.fetch_user(member.id)
                    await u.send(f"⚠️ אחי ניסו לתת לך באן! המבצע: {entry.user.name}. ביטלתי ישר. הנה קישור חזרה: {inv}")
                except: pass

# --- פקודות (15 פקודות) ---

@bot.tree.command(name="sync", description="סנכרון פקודות")
async def sync(i):
    if await is_owner(i): await bot.tree.sync(); await i.response.send_message("✅ הכל סונכרן!", ephemeral=True)

@bot.tree.command(name="setup_all", description="הקמת כל המערכות")
async def sa(i):
    if await is_owner(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", description="לחץ לאימות", color=0x2ecc71), view=VerifyView())
        await i.channel.send(embed=discord.Embed(title="💬 פידבקים והמלצות", color=0x00ffff), view=FeedbackView())
        await i.channel.send(embed=discord.Embed(title="🚨 דיווחים (שחקן/צוות)", color=0xff0000), view=ReportView())
        await i.response.send_message("הכל הוקם!", ephemeral=True)

@bot.tree.command(name="warn", description="אזהרה (3=מיוט, 5=קיק)")
async def warn(i, member: discord.Member, reason: str):
    if await is_owner(i):
        user_warnings[member.id] += 1
        count = user_warnings[member.id]
        if count == 3:
            await member.add_roles(i.guild.get_role(MUTE_2DAYS_ROLE))
            await i.response.send_message(f"⚠️ {member.mention} הוזהר פעם 3 והושתק ליומיים!")
        elif count >= 5:
            await member.kick(reason="5 אזהרות")
            user_warnings[member.id] = 0
            await i.response.send_message(f"👢 {member.mention} הועף בגלל 5 אזהרות!")
        else:
            await i.response.send_message(f"⚠️ {member.mention} הוזהר ({count}/5). סיבה: {reason}")

@bot.tree.command(name="clear", description="ניקוי הודעות")
async def cl(i, amount: int):
    if await is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="mute_2d", description="מיוט ידני ליומיים")
async def m2(i, member: discord.Member):
    if await is_owner(i):
        await member.add_roles(i.guild.get_role(MUTE_2DAYS_ROLE))
        await i.response.send_message(f"🔇 {member.mention} הושתק ליומיים.")

@bot.tree.command(name="unmute", description="ביטול השתקה")
async def unm(i, member: discord.Member):
    if await is_owner(i):
        await member.remove_roles(i.guild.get_role(MUTE_2DAYS_ROLE))
        await i.response.send_message(f"🔊 {member.mention} שוחרר ממיוט.")

@bot.tree.command(name="nuke", description="שחזור חדר")
async def nk(i):
    if await is_owner(i): await i.channel.clone(); await i.channel.delete()

@bot.tree.command(name="lock", description="נעילת חדר")
async def lc(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="פתיחת חדר")
async def ulc(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="kick", description="העפה")
async def kck(i, m: discord.Member):
    if await is_owner(i): await m.kick(); await i.response.send_message(f"👢 {m.name} הועף.")

@bot.tree.command(name="ban", description="חסימה")
async def bn(i, m: discord.Member):
    if await is_owner(i): await m.ban(); await i.response.send_message(f"🔨 {m.name} נחסם!")

@bot.tree.command(name="suspect", description="שים כחשוד")
async def susp(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(SUSPECT_ROLE_ID)); await i.response.send_message(f"🕵️ {m.mention} חשוד.")

@bot.tree.command(name="say", description="הודעת אונר")
async def sy(i, text: str):
    if await is_owner(i): await i.channel.send(embed=discord.Embed(description=text, color=0x00ffff)); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="slowmode", description="מצב איטי")
async def sl(i, seconds: int):
    if await is_owner(i): await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="profile", description="פרופיל")
async def pr(i, m: discord.Member):
    e = discord.Embed(title=m.name, color=m.color); e.set_thumbnail(url=m.avatar.url if m.avatar else None)
    await i.response.send_message(embed=e)

# --- אבטחה ספאם ---
@bot.event
async def on_message(msg):
    if msg.author.bot or any(role.id == OWNER_CMD_ROLE for role in msg.author.roles if hasattr(msg.author, 'roles')): return
    now = asyncio.get_event_loop().time()
    spam_tracker[msg.author.id].append(now)
    if len([t for t in spam_tracker[msg.author.id] if now - t < 3]) > 5:
        await msg.author.timeout(timedelta(minutes=10))
        await msg.channel.send(f"🔇 {msg.author.mention} הושתק (ספאם).", delete_after=5)

if TOKEN: bot.run(TOKEN)
