import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (לפי כל ההיסטוריה והתמונות) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443  # ה-ID שלך (נהוראי)
SECOND_ID = 1493293951959044147

# חדרים ורולים
WELCOME_CH_ID = 1501713652217282591 
FEEDBACK_CH_ID = 1503475379942461522
OWNER_CMD_ROLE_ID = 1502014872655888554
MEMBER_ROLE_ID = 1501983948111352091
MUTE_2DAYS_ROLE_ID = 1501953906736103535
REPORT_ROLE_ID = 1501946934779449505
RECOMMEND_ROLE_ID = 1501947249658429470
SUSPECT_ROLE_ID = 1503464176599695380

user_warnings = defaultdict(int)
spam_tracker = defaultdict(list)

# --- מערכת אימות מעוצבת ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="התחל אימות ✅", style=discord.ButtonStyle.green, custom_id="verify_v1")
    async def v(self, i, b):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role:
            await i.user.add_roles(role)
            await i.response.send_message("אומתת! ברוך הבא לשרת. 🔥", ephemeral=True)

# --- מערכת פידבק אנונימי ---
class FeedbackModal(ui.Modal, title="📤 שלח פידבק"):
    inp = ui.TextInput(label="תוכן", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="כן", required=False)
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        is_anon = self.anon.value.strip().lower() == "כן"
        emb = discord.Embed(title="💬 פידבק חדש", description=self.inp.value, color=0x00ffff)
        if not is_anon: emb.set_author(name=i.user.name, icon_url=i.user.avatar.url)
        else: emb.set_author(name="אנונימי")
        await ch.send(embed=emb)
        await i.response.send_message("נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💥", style=discord.ButtonStyle.blurple, custom_id="fb_v1")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- Bot Core ---
class CyberShield(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

async def is_owner(i):
    if i.user.id == MY_USER_ID or any(role.id == OWNER_CMD_ROLE_ID for role in i.user.roles): return True
    await i.response.send_message("🚫 פקודה לאונר בלבד!", ephemeral=True); return False

# --- הגנה עצמית מבאן (Anti-Ban) ---
@bot.event
async def on_member_remove(m):
    if m.id in [MY_USER_ID, SECOND_ID]:
        async for entry in m.guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == m.id:
                await m.guild.unban(m)
                inv = await m.guild.text_channels[0].create_invite(max_uses=1)
                try: 
                    u = await bot.fetch_user(m.id)
                    await u.send(f"⚠️ ניסו לתת לך באן! המבצע: {entry.user.name}. הנה לינק: {inv}")
                except: pass

# --- וולקם מעוצב ---
@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(description=f"Welcome {m.mention}, אתה מס' {m.guild.member_count}.\nDeveloped by Nehoray Owner 👑", color=0xff4500)
        emb.set_author(name="ברוך הבא לשרת ספאמר 🔥", icon_url=m.guild.icon.url)
        await ch.send(content=m.mention, embed=emb)

# --- פקודות (15 פקודות + חלוקה) ---

@bot.tree.command(name="sync", description="אונר | סנכרון פקודות")
async def sync(i):
    if await is_owner(i): await bot.tree.sync(); await i.response.send_message("סונכרן!", ephemeral=True)

@bot.tree.command(name="setup_verify", description="אונר | סטאפ אימות")
async def sv(i):
    if await is_owner(i): await i.channel.send(embed=discord.Embed(title="אימות משתמשים 🛡️", description="לחץ למטה לאימות\nDeveloped by Nehoray 👑", color=0x2ecc71), view=VerifyView())

@bot.tree.command(name="setup_feedback", description="אונר | סטאפ פידבק")
async def sf(i):
    if await is_owner(i): await i.channel.send(embed=discord.Embed(title="תיבת פידבקים 💥", description="שלחו הצעה או תלונה אנונימית", color=0x00ffff), view=FeedbackView())

@bot.tree.command(name="warn", description="אונר | אזהרה (3=מיוט, 5=קיק)")
async def wr(i, m: discord.Member, reason: str):
    if await is_owner(i):
        user_warnings[m.id] += 1
        c = user_warnings[m.id]
        if c == 3: await m.add_roles(i.guild.get_role(MUTE_2DAYS_ROLE_ID)); msg = f"⚠️ {m.mention} אזהרה 3 - מיוט!"
        elif c >= 5: await m.kick(); user_warnings[m.id] = 0; msg = f"👢 {m.mention} הועף!"
        else: msg = f"⚠️ {m.mention} אזהרה {c}/5. סיבה: {reason}"
        await i.response.send_message(msg)

@bot.tree.command(name="clear", description="אונר | מחיקת הודעות")
async def cl(i, amount: int):
    if await is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="nuke", description="אונר | שחזור חדר")
async def nk(i):
    if await is_owner(i): await i.channel.clone(); await i.channel.delete()

@bot.tree.command(name="mute_2d", description="אונר | מיוט יומיים")
async def m2(i, m: discord.Member):
    if await is_owner(i): await m.add_roles(i.guild.get_role(MUTE_2DAYS_ROLE_ID)); await i.response.send_message(f"🔇 {m.mention}")

@bot.tree.command(name="unmute", description="אונר | ביטול מיוט")
async def unm(i, m: discord.Member):
    if await is_owner(i): await m.remove_roles(i.guild.get_role(MUTE_2DAYS_ROLE_ID)); await i.response.send_message(f"🔊 {m.mention}")

@bot.tree.command(name="lock", description="אונר | נעילת חדר")
async def lc(i):
    if await is_owner(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="kick", description="אונר | העפה")
async def kc(i, m: discord.Member):
    if await is_owner(i): await m.kick(); await i.response.send_message("👢")

@bot.tree.command(name="ban", description="אונר | חסימה")
async def bn(i, m: discord.Member):
    if await is_owner(i): await m.ban(); await i.response.send_message("🔨")

@bot.tree.command(name="say", description="אונר | הודעה מעוצבת")
async def sy(i, text: str):
    if await is_owner(i): await i.channel.send(embed=discord.Embed(description=text, color=0x00ffff)); await i.response.send_message("👍", ephemeral=True)

@bot.tree.command(name="recommend", description="כולם | המלצה")
async def rc(i, text: str):
    r_ch = i.guild.get_role(RECOMMEND_ROLE_ID)
    emb = discord.Embed(title="⭐ המלצה", description=text, color=0xffff00)
    await i.channel.send(content=r_ch.mention if r_ch else "", embed=emb); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="report", description="כולם | דיווח")
async def rp(i, text: str):
    r_ch = i.guild.get_role(REPORT_ROLE_ID)
    emb = discord.Embed(title="🚨 דיווח", description=text, color=0xff0000)
    await i.channel.send(content=r_ch.mention if r_ch else "", embed=emb); await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="profile", description="כולם | פרופיל")
async def pr(i, m: discord.Member):
    e = discord.Embed(title=m.name, color=m.color); e.set_thumbnail(url=m.avatar.url if m.avatar else None)
    await i.response.send_message(embed=e)

# --- ספאם ---
@bot.event
async def on_message(msg):
    if msg.author.bot or any(r.id == OWNER_CMD_ROLE_ID for r in msg.author.roles if hasattr(msg.author, 'roles')): return
    now = asyncio.get_event_loop().time()
    spam_tracker[msg.author.id].append(now)
    if len([t for t in spam_tracker[msg.author.id] if now - t < 3]) > 5:
        await msg.author.timeout(timedelta(minutes=10))
        await msg.channel.send(f"🔇 {msg.author.mention} הושבת (ספאם).", delete_after=5)

if TOKEN: bot.run(TOKEN)
