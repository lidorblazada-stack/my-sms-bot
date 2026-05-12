import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta
import os
import asyncio
from collections import defaultdict

# --- IDs סופיים ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443
SECOND_ID = 1493293951959044147

WELCOME_CH_ID = 1501713652217282591 
FEEDBACK_CH_ID = 1503475379942461522
OWNER_CMD_ROLE_ID = 1502014872655888554
MEMBER_ROLE_ID = 1501983948111352091
MUTE_2DAYS_ROLE_ID = 1501953906736103535
REPORT_ROLE_ID = 1501946934779449505
RECOMMEND_ROLE_ID = 1501947249658429470

# דאטה-בייס פשוט בזיכרון
user_warnings = defaultdict(int)
owner_attempt_tracker = set() # למעקב אחרי אזהרה מילולית ראשונה
spam_tracker = defaultdict(list)

# --- פונקציית ענישה מרכזית ---
async def apply_punishment(interaction, member, count, reason):
    if count == 3:
        role = interaction.guild.get_role(MUTE_2DAYS_ROLE_ID)
        if role: await member.add_roles(role)
        try: await member.send(f"🔇 הושתקת ליומיים בשרת {interaction.guild.name}. המיוט ירד בעוד יומיים.")
        except: pass
        return f"⚠️ {member.mention} הגיע ל-3 אזהרות והושתק ליומיים!"
    elif count >= 5:
        try: await member.send(f"👢 הועפת מהשרת {interaction.guild.name} בגלל שהגעת ל-5 אזהרות.")
        except: pass
        await member.kick(reason="5 אזהרות")
        user_warnings[member.id] = 0
        return f"👢 {member.mention} הועף מהשרת (5 אזהרות)!"
    return f"⚠️ {member.mention} הוזהר ({count}/5). סיבה: {reason}"

# --- Views ---
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
        if not is_anon: emb.set_author(name=i.user.name)
        await ch.send(embed=emb); await i.response.send_message("נשלח!", ephemeral=True)

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

# --- בדיקת אונר עם ענישה ---
async def is_owner(i: discord.Interaction):
    if i.user.id == MY_USER_ID or any(role.id == OWNER_CMD_ROLE_ID for role in i.user.roles):
        return True
    
    if i.user.id not in owner_attempt_tracker:
        owner_attempt_tracker.add(i.user.id)
        await i.response.send_message("🚫 פקודת אונר בלבד! ניסיון נוסף יגרור אזהרה רשמית.", ephemeral=True)
    else:
        user_warnings[i.user.id] += 1
        res = await apply_punishment(i, i.user, user_warnings[i.user.id], "ניסיון שימוש בפקודות אונר")
        await i.response.send_message(res, ephemeral=True)
    return False

# --- Anti-Ban & Welcome (נשאר ללא שינוי) ---
@bot.event
async def on_member_remove(m):
    if m.id in [MY_USER_ID, SECOND_ID]:
        async for entry in m.guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == m.id:
                await m.guild.unban(m)
                inv = await m.guild.text_channels[0].create_invite(max_uses=1)
                try: await (await bot.fetch_user(m.id)).send(f"⚠️ בוטל באן! לינק: {inv}")
                except: pass

@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(WELCOME_CH_ID)
    if ch:
        emb = discord.Embed(description=f"Welcome {m.mention}, מס' {m.guild.member_count}.\nDeveloped by Nehoray 👑", color=0xff4500)
        await ch.send(content=m.mention, embed=emb)

# --- פקודות ניהול אזהרות ---

@bot.tree.command(name="check_warns", description="בדוק כמה אזהרות יש למשתמש")
async def check_w(i, member: discord.Member):
    count = user_warnings[member.id]
    await i.response.send_message(f"למשתמש {member.mention} יש `{count}` אזהרות במערכת.", ephemeral=True)

@bot.tree.command(name="add_warn", description="אונר | הוסף אזהרה ידנית")
async def add_w(i, member: discord.Member, reason: str):
    if await is_owner(i):
        user_warnings[member.id] += 1
        res = await apply_punishment(i, member, user_warnings[member.id], reason)
        await i.response.send_message(res)

@bot.tree.command(name="remove_warn", description="אונר | הסר אזהרה ידנית")
async def rem_w(i, member: discord.Member):
    if await is_owner(i):
        if user_warnings[member.id] > 0:
            user_warnings[member.id] -= 1
            await i.response.send_message(f"הוסרה אזהרה ל-{member.mention}. מצב נוכחי: `{user_warnings[member.id]}`")
        else:
            await i.response.send_message("למשתמש אין אזהרות להסיר.", ephemeral=True)

# --- פקודות אונר רגילות ---

@bot.tree.command(name="sync")
async def sync(i):
    if await is_owner(i): await bot.tree.sync(); await i.response.send_message("סונכרן!", ephemeral=True)

@bot.tree.command(name="setup_all")
async def sa(i):
    if await is_owner(i):
        await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView())
        await i.channel.send(embed=discord.Embed(title="💬 פידבק אנונימי", color=0x00ffff), view=FeedbackView())
        await i.response.send_message("מערכות הוקמו.", ephemeral=True)

@bot.tree.command(name="clear")
async def cl(i, amount: int):
    if await is_owner(i): await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="nuke")
async def nk(i):
    if await is_owner(i): await i.channel.clone(); await i.channel.delete()

# --- פקודות לכולם ---
@bot.tree.command(name="recommend")
async def rc(i, text: str):
    await i.channel.send(embed=discord.Embed(title="⭐ המלצה", description=text, color=0xffff00))
    await i.response.send_message("נשלח", ephemeral=True)

@bot.tree.command(name="report")
async def rp(i, text: str):
    await i.channel.send(embed=discord.Embed(title="🚨 דיווח", description=text, color=0xff0000))
    await i.response.send_message("נשלח", ephemeral=True)

# --- ספאם ---
@bot.event
async def on_message(msg):
    if msg.author.bot or any(r.id == OWNER_CMD_ROLE_ID for r in msg.author.roles if hasattr(msg.author, 'roles')): return
    now = asyncio.get_event_loop().time()
    spam_tracker[msg.author.id].append(now)
    if len([t for t in spam_tracker[msg.author.id] if now - t < 3]) > 5:
        await msg.author.timeout(timedelta(minutes=10))
        await msg.channel.send(f"🔇 {msg.author.mention} הושתק (ספאם).", delete_after=5)

if TOKEN: bot.run(TOKEN)
