import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- קונפיגורציה (IDs מהמגילה) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443

CHANNELS = {
    "SUGGESTIONS": 1501947249658429470, "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522, "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554, "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591, "LEADERBOARD": 1502014872655888554
}
ROLES = {
    "SUPPORTER": 1503819239310627068, "VIP": 1503817695466881255,
    "TICKET_STAFF": 1501316672345211041, "MUTE": 1501953906736103535,
    "VERIFIED": 1501316672345211041
}

# דאטה-בייס פנימי
user_balances = {}
user_warns = {}
jail_list = {} # {user_id: release_time}
daily_cooldown = {}
feedback_cooldown = {}

# --- מודאלים (חלונות קופצים) ---
class ReportModal(ui.Modal, title="🚨 דיווח על שחקן"):
    player = ui.TextInput(label="שם השחקן המדווח", placeholder="לדוגמה: Lidor#1234")
    reason = ui.TextInput(label="סיבת הדיווח", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        emb = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red(), timestamp=datetime.now())
        emb.add_field(name="מדווח:", value=i.user.mention)
        emb.add_field(name="שחקן נגדו דווח:", value=self.player.value)
        emb.add_field(name="סיבה:", value=self.reason.value)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=emb)
        await i.response.send_message("✅ הדיווח נשלח לצוות.", ephemeral=True)

class FeedbackModal(ui.Modal, title="📩 שלח פידבק"):
    content = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", max_length=2, default="לא")
    async def on_submit(self, i):
        display = "👤 אנונימי" if self.anon.value == "כן" else i.user.name
        emb = discord.Embed(title="✨ פידבק מהשרת", description=self.content.value, color=discord.Color.cyan())
        emb.set_footer(text=f"נשלח ע\"י: {display}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=emb)
        await i.response.send_message("✅ תודה על הפידבק!", ephemeral=True)

# --- פאנלים קבועים ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s:sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLES["SUPPORTER"])
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="s:vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLES["VIP"])
    @ui.button(label="🎁 בונוס יומי (Daily)", style=discord.ButtonStyle.success, custom_id="s:day", row=1)
    async def daily_btn(self, i, b):
        now = datetime.now()
        if i.user.id in daily_cooldown and now < daily_cooldown[i.user.id] + timedelta(days=1):
            return await i.response.send_message("❌ חזור מחר אחי.", ephemeral=True)
        amt = random.randint(500, 1500)
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + amt
        daily_cooldown[i.user.id] = now
        await i.response.send_message(f"💰 קיבלת ₪{amt}!", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances.get(i.user.id, 0) < p: return await i.response.send_message("אין כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h:u")
    async def rob_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא!", ephemeral=True)
        v = ui.View(); s = ui.UserSelect(placeholder="בחר קורבן...")
        async def cb(inter):
            target = s.values[0]
            if target.id == i.user.id: return
            p_v = PoliceView(i.user)
            await inter.response.send_message(f"🔫 שודד את {target.name}...", ephemeral=True)
            try: await target.send(f"🚨 {i.user.name} שודד אותך! מהר!", view=p_v)
            except: return
            await asyncio.sleep(10)
            if not p_v.called:
                loot = random.randint(1000, 3000)
                user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
                user_balances[target.id] = max(0, user_balances.get(target.id, 0) - loot)
                await i.followup.send(f"💰 הצלחת! גנבת ₪{loot}", ephemeral=True)
        s.callback = cb; v.add_item(s)
        await i.response.send_message("מי המטרה?", view=v, ephemeral=True)

    @ui.button(label="🔓 ערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="h:b")
    async def bail(self, i, b):
        v = ui.View(); s = ui.UserSelect(placeholder="את מי לשחרר?")
        async def cb(inter):
            friend = s.values[0]
            if friend.id in jail_list and user_balances.get(i.user.id, 0) >= 5000:
                del jail_list[friend.id]; user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 {friend.name} שוחרר!")
            else: await inter.response.send_message("אי אפשר.", ephemeral=True)
        s.callback = cb; v.add_item(s)
        await i.response.send_message("שחרר חבר:", view=v, ephemeral=True)

class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber; self.called = False
    @ui.button(label="🚨 משטרה!", style=discord.ButtonStyle.danger)
    async def call(self, i, b):
        self.called = True; self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 השודד נעצר!")

# --- הבוט ופקודות ה-30 ---
class MasterBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.jail_task.start(); await self.tree.sync()
    @tasks.loop(seconds=60)
    async def jail_task(self):
        now = datetime.now()
        to_del = [u for u, t in jail_list.items() if now >= t]
        for u in to_del: del jail_list[u]

bot = MasterBot()

# --- פקודות סטאפ ---
@bot.tree.command(name="setup_all")
async def s_all(i):
    if i.user.id != MY_USER_ID: return
    # חנות
    await i.channel.send(embed=discord.Embed(title="🏪 חנות השרת", color=0x2b2d31), view=ShopView())
    # שודים
    await i.channel.send(embed=discord.Embed(title="🔫 עולם הפשע", color=0x000000), view=HeistView())
    # פידבק ודיווח
    v_fb = ui.View(timeout=None)
    b_fb = ui.Button(label="📩 פידבק", style=discord.ButtonStyle.primary, custom_id="f:b")
    b_fb.callback = lambda inter: inter.response.send_modal(FeedbackModal())
    b_re = ui.Button(label="🚨 דווח", style=discord.ButtonStyle.danger, custom_id="r:e")
    b_re.callback = lambda inter: inter.response.send_modal(ReportModal())
    v_fb.add_item(b_fb); v_fb.add_item(b_re)
    await i.channel.send("📩 **פאנל פידבקים ודיווחים**", view=v_fb)
    await i.response.send_message("הכל הוקם!", ephemeral=True)

# --- פקודות כלכלה ומודרציה ---
@bot.tree.command(name="bal")
async def bal(i, user: discord.Member = None):
    u = user or i.user
    await i.response.send_message(f"💰 יתרה של {u.name}: ₪{user_balances.get(u.id, 0)}")

@bot.tree.command(name="work")
async def work(i):
    amt = random.randint(100, 500)
    user_balances[i.user.id] = user_balances.get(i.user.id, 0) + amt
    await i.response.send_message(f"🛠️ עבדת וקיבלת ₪{amt}")

@bot.tree.command(name="pay")
async def pay(i, to: discord.Member, amount: int):
    if user_balances.get(i.user.id, 0) < amount or amount <= 0: return await i.response.send_message("אין כסף.")
    user_balances[i.user.id] -= amount
    user_balances[to.id] = user_balances.get(to.id, 0) + amount
    await i.response.send_message(f"💸 העברת ₪{amount} ל-{to.mention}")

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    log = i.guild.get_channel(CHANNELS["WARNS_LOG"])
    await log.send(f"⚠️ {member.mention} הוזהר! ({user_warns[member.id]}/3). סיבה: {reason}")
    if user_warns[member.id] >= 3:
        await member.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    if i.user.id != MY_USER_ID: return
    await i.channel.purge(limit=amount)
    await i.response.send_message(f"🗑️ נמחקו {amount} הודעות.", ephemeral=True)

# לוג אונר
@bot.event
async def on_app_command_completion(i, cmd):
    log = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    if log: await log.send(f"🛠️ `{i.user.name}` הריץ: `/{cmd.name}`")

bot.run(TOKEN)
