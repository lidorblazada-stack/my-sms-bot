import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- הגדרות קבועות (IDs מהמגילה) ---
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
    "TICKET_STAFF": 1501316672345211041, "MUTE": 1501953906736103535
}

# דאטה-בייס פנימי
user_balances = {}
jail_list = {}
user_warns = {}

# --- פאנלים ואינטראקציות ---

# 1. פאנל שודים (Heist) - עם המשטרה בפרטי
class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber
        self.called = False
    @ui.button(label="🚨 התקשר למשטרה!", style=discord.ButtonStyle.danger)
    async def call(self, i, b):
        self.called = True; self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 השודד נעצר ונשלח לכלא לשעתיים!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h:u")
    async def rob_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא!", ephemeral=True)
        v = ui.View(); s = ui.UserSelect(placeholder="בחר מטרה...")
        async def callb(inter):
            target = s.values[0]
            p_v = PoliceView(i.user)
            await inter.response.send_message("🔫 השוד התחיל! לקורבן יש 10 שניות!", ephemeral=True)
            try: await target.send(f"⚠️ {i.user.name} שודד אותך!", view=p_v)
            except: return
            await asyncio.sleep(10)
            if not p_v.called:
                loot = random.randint(1000, 3000)
                user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
                await i.followup.send(f"💰 גנבת ₪{loot}!", ephemeral=True)
        s.callback = callb; v.add_item(s)
        await i.response.send_message("מי הקורבן?", view=v, ephemeral=True)

    @ui.button(label="🔓 שחרר בערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="h:b")
    async def bail(self, i, b):
        v = ui.View(); s = ui.UserSelect(placeholder="מי לשחרר?")
        async def callb(inter):
            f = s.values[0]
            if f.id in jail_list and user_balances.get(i.user.id, 0) >= 5000:
                del jail_list[f.id]; user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 {f.name} חופשי!")
        s.callback = callb; v.add_item(s)
        await i.response.send_message("בחר חבר:", view=v, ephemeral=True)

# 2. חנות (Shop)
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s:s", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLES["SUPPORTER"])
    @ui.button(label="VIP 💎", style=discord.ButtonStyle.primary, custom_id="s:v", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLES["VIP"])
    @ui.button(label="בונוס ₪1,000 🎁", style=discord.ButtonStyle.success, custom_id="s:d", row=1)
    async def b3(self, i, b):
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + 1000
        await i.response.send_message("💰 קיבלת בונוס!", ephemeral=True)
    async def buy(self, i, p, r_id):
        if user_balances.get(i.user.id, 0) < p: return await i.response.send_message("אין כסף!", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

# --- הגדרת הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.jail_task.start(); await self.tree.sync()
    @tasks.loop(seconds=60)
    async def jail_task(self):
        now = datetime.now()
        to_del = [u for u, t in jail_list.items() if now >= t]
        for u in to_del: del jail_list[u]

bot = CyberShield()

# --- פקודות הסטאפ (כמו בתמונות שלך) ---
@bot.tree.command(name="setup_shop")
async def s_shop(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🏪 חנות Cyber-Store", color=0x2b2d31), view=ShopView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_heist")
async def s_heist(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🔫 פאנל שודים", color=0x000000), view=HeistView())
    await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    log = i.guild.get_channel(CHANNELS["WARNS_LOG"])
    await log.send(f"⚠️ {member.mention} הוזהר! ({user_warns[member.id]}/3). סיבה: {reason}")
    if user_warns[member.id] >= 3:
        await member.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message("בוצע.", ephemeral=True)

# לוג אונר אוטומטי (כל פעם שמפעילים פקודה)
@bot.event
async def on_app_command_completion(i, cmd):
    log = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log.send(f"🛠️ `{i.user.name}` הפעיל פקודה: `/{cmd.name}`")

bot.run(TOKEN)
