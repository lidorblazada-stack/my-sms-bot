import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- קונפיגורציה ו-IDs (לפי המגילה של לידור) ---
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
    "SUSPECT": 1503464176599695380
}

user_balances = {}
user_warns = {}
jail_list = {} # {user_id: release_time}
feedback_cooldown = {}

# --- 1. מערכות קופצות (Modals) ---
class FeedbackModal(ui.Modal, title="📩 שליחת פידבק חדש"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)
    async def on_submit(self, i):
        if i.user.id in feedback_cooldown and datetime.now() < feedback_cooldown[i.user.id]:
            return await i.response.send_message("❌ חכה 5 דקות בין פידבק לפידבק!", ephemeral=True)
        display = "👤 אנונימי" if self.anon.value == "כן" else i.user.mention
        emb = discord.Embed(title="✨ פידבק חדש", description=self.msg.value, color=0x00fbff)
        emb.set_footer(text=f"נשלח ע\"י: {display}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=emb)
        feedback_cooldown[i.user.id] = datetime.now() + timedelta(minutes=5)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

# --- 2. פאנלים קבועים (Persistent Views) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s:sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLES["SUPPORTER"])
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="s:vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLES["VIP"])
    @ui.button(label="קנה Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="s:stf", row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLES["TICKET_STAFF"])
    @ui.button(label="🎁 בונוס ₪1,000", style=discord.ButtonStyle.success, custom_id="s:day", row=1)
    async def b4(self, i, b):
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + 1000
        await i.response.send_message("💰 קיבלת ₪1,000!", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances.get(i.user.id, 0) < p: return await i.response.send_message("❌ אין כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h:u")
    async def rob_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא!", ephemeral=True)
        view = ui.View(); select = ui.UserSelect(placeholder="בחר קורבן...")
        async def callback(inter):
            target = select.values[0]
            if target.id == i.user.id: return
            p_view = PoliceView(i.user)
            await inter.response.send_message("🔫 שוד מתחיל... לקורבן יש 10 שניות!", ephemeral=True)
            try: await target.send(f"🚨 {i.user.name} שודד אותך! לחץ מהר!", view=p_view)
            except: return
            await asyncio.sleep(10)
            if not p_view.called:
                loot = random.randint(1000, 3000)
                user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
                user_balances[target.id] = max(0, user_balances.get(target.id, 0) - loot)
                await i.followup.send(f"💰 הצלחת! גנבת ₪{loot}", ephemeral=True)
        select.callback = callback; view.add_item(select)
        await i.response.send_message("מי המטרה?", view=view, ephemeral=True)

    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h:b")
    async def rob_bank(self, i, b):
        if random.random() > 0.5:
            loot = random.randint(3000, 7000)
            user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
            await i.response.send_message(f"🏦 השוד הצליח! ברחת עם ₪{loot}", ephemeral=True)
        else:
            jail_list[i.user.id] = datetime.now() + timedelta(hours=2)
            await i.response.send_message("🚨 האזעקה פעלה! אתה בכלא לשעתיים.", ephemeral=True)

    @ui.button(label="🔓 ערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="h:bail")
    async def bail(self, i, b):
        view = ui.View(); select = ui.UserSelect(placeholder="את מי לשחרר?")
        async def callback(inter):
            friend = select.values[0]
            if friend.id in jail_list and user_balances.get(i.user.id, 0) >= 5000:
                del jail_list[friend.id]; user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 {friend.name} שוחרר!")
            else: await inter.response.send_message("לא ניתן לשחרר.", ephemeral=True)
        select.callback = callback; view.add_item(select)
        await i.response.send_message("בחר חבר:", view=view, ephemeral=True)

class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber; self.called = False
    @ui.button(label="🚨 משטרה!", style=discord.ButtonStyle.danger)
    async def call(self, i, b):
        self.called = True; self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 השודד נעצר!")

# --- 3. הבוט וכל פקודות הסטאפ הנפרדות ---
class CyberBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.check_jail.start(); self.update_lb.start()
        await self.tree.sync()

    @tasks.loop(seconds=60)
    async def check_jail(self):
        now = datetime.now()
        to_del = [u for u, t in jail_list.items() if now >= t]
        for u in to_del: del jail_list[u]

    @tasks.loop(minutes=5)
    async def update_lb(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            emb = discord.Embed(title="🏆 טבלת עשירים (מתעדכן)", color=0xffd700)
            sorted_bal = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
            emb.description = "\n".join([f"**{idx+1}.** <@{u}> - ₪{b}" for idx, (u, b) in enumerate(sorted_bal)])
            async for m in ch.history(limit=5): await m.delete()
            await ch.send(embed=emb)

bot = CyberBot()

# --- פקודות סטאפ נפרדות ---
@bot.tree.command(name="setup_shop")
async def s_shop(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🏪 CYBER-STORE", color=0x2b2d31), view=ShopView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_heist")
async def s_heist(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🔫 HEIST & CRIME", color=0x000000), view=HeistView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_feedback")
async def s_fb(i):
    if i.user.id != MY_USER_ID: return
    view = ui.View(timeout=None)
    btn = ui.Button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="fb_btn")
    btn.callback = lambda inter: inter.response.send_modal(FeedbackModal())
    view.add_item(btn)
    await i.channel.send(embed=discord.Embed(title="📩 פאנל פידבקים", description="לחץ לשליחת פידבק (ניתן לאנונימי)"), view=view)
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    log = i.guild.get_channel(CHANNELS["WARNS_LOG"])
    await log.send(f"⚠️ {member.mention} הוזהר! ({user_warns[member.id]}/3). סיבה: {reason}")
    if user_warns[member.id] >= 3:
        await member.add_roles(i.guild.get_role(ROLES["MUTE"]))
        await log.send(f"🚫 {member.name} הושתק אוטומטית.")
    await i.response.send_message("בוצע.", ephemeral=True)

@bot.event
async def on_app_command_completion(i, cmd):
    log = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log.send(embed=discord.Embed(title="🛠️ לוג אונר", description=f"הפקודה `/{cmd.name}` הופעלה.", color=0x5865f2))

bot.run(TOKEN)
