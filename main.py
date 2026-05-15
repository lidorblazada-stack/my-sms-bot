import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- הגדרות IDs (המגילה של לידור) ---
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

# דאטה-בייס פנימי
user_balances = {}
user_warns = {} # {user_id: count}
jail_list = {} # {user_id: release_time}

# --- 1. מערכת אזהרות (Warns) ---
async def add_warn(i, member, reason):
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    count = user_warns[member.id]
    
    log_ch = i.guild.get_channel(CHANNELS["WARNS_LOG"])
    embed = discord.Embed(title="⚠️ אזהרה רשמית", color=0xffa500, timestamp=datetime.now())
    embed.add_field(name="משתמש:", value=member.mention)
    embed.add_field(name="סיבה:", value=reason)
    embed.add_field(name="מספר אזהרה:", value=f"{count}/3")
    embed.set_footer(text=f"ניתן ע\"י: {i.user.name}")
    await log_ch.send(embed=embed)
    
    if count >= 3:
        mute_role = i.guild.get_role(ROLES["MUTE"])
        await member.add_roles(mute_role)
        await log_ch.send(f"🚫 {member.mention} הגיע ל-3 אזהרות וקיבל מיוט אוטומטי.")
        user_warns[member.id] = 0 # איפוס אחרי עונש

# --- 2. מערכת שודים, משטרה וכלא ---
class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber
        self.called = False

    @ui.button(label="🚨 התקשר למשטרה! (10 שניות)", style=discord.ButtonStyle.danger)
    async def call_police(self, i, b):
        self.called = True; self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 המשטרה בדרך! השודד נשלח לכלא לשעתיים.", ephemeral=True)
        try: await self.robber.send("🚨 נתפסת! אתה בכלא לשעתיים.")
        except: pass

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h:u")
    async def rob_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא!", ephemeral=True)
        view = ui.View(); select = ui.UserSelect(placeholder="בחר קורבן...")
        async def callback(inter):
            target = select.values[0]
            if target.id == i.user.id: return await inter.response.send_message("לא לשדוד את עצמך!", ephemeral=True)
            p_view = PoliceView(i.user)
            await inter.response.send_message(f"🔫 השוד התחיל... מחכה לראות אם {target.name} יזעיק משטרה.", ephemeral=True)
            try: await target.send(f"⚠️ {i.user.name} מנסה לשדוד אותך! לחץ מהר!", view=p_view)
            except: return
            await asyncio.sleep(10)
            if not p_view.called:
                loot = random.randint(1000, 3000)
                user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
                user_balances[target.id] = max(0, user_balances.get(target.id, 0) - loot)
                await i.followup.send(f"💰 הצלחת! גנבת ₪{loot}.", ephemeral=True)
        select.callback = callback; view.add_item(select)
        await i.response.send_message("מי הקורבן?", view=view, ephemeral=True)

    @ui.button(label="🔓 שחרר בערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="h:b")
    async def bail(self, i, b):
        if user_balances.get(i.user.id, 0) < 5000: return await i.response.send_message("אין כסף.", ephemeral=True)
        view = ui.View(); select = ui.UserSelect(placeholder="את מי לשחרר?")
        async def callback(inter):
            target = select.values[0]
            if target.id in jail_list:
                del jail_list[target.id]; user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 {target.name} שוחרר!")
            else: await inter.response.send_message("הוא לא בכלא.", ephemeral=True)
        select.callback = callback; view.add_item(select)
        await i.response.send_message("בחר חבר:", view=view, ephemeral=True)

# --- 3. חנות וסטאפ ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLES["SUPPORTER"])
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLES["VIP"])
    @ui.button(label="🎁 בונוס יומי", style=discord.ButtonStyle.success, row=1)
    async def b3(self, i, b):
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + 1000
        await i.response.send_message("💰 קיבלת ₪1,000!", ephemeral=True)

    async def buy(self, i, p, r_id):
        if user_balances.get(i.user.id, 0) < p: return await i.response.send_message("חסר כסף.", ephemeral=True)
        user_balances[i.user.id] -= p
        await i.user.add_roles(i.guild.get_role(r_id))
        await i.response.send_message("✅ תתחדש!", ephemeral=True)

# --- 4. הבוט הראשי ולוגים של אונר ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.check_jail.start()
        await self.tree.sync()

    @tasks.loop(seconds=60)
    async def check_jail(self):
        now = datetime.now()
        to_del = [k for k, v in jail_list.items() if now >= v]
        for k in to_del: del jail_list[k]

bot = CyberShield()

@bot.tree.command(name="warn", description="מתן אזהרה לשחקן")
async def warn_cmd(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return
    await add_warn(i, member, reason)
    await i.response.send_message(f"⚠️ {member.name} הוזהר.", ephemeral=True)

@bot.tree.command(name="setup_all")
async def setup(i):
    if i.user.id != MY_USER_ID: return
    await i.channel.send(embed=discord.Embed(title="🏪 חנות", color=0x2b2d31), view=ShopView())
    await i.channel.send(embed=discord.Embed(title="🔫 שודים", color=0x000000), view=HeistView())
    await i.response.send_message("הוקם!", ephemeral=True)

@bot.event
async def on_app_command_completion(i, cmd):
    log = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    embed = discord.Embed(title="🛠️ לוג אונר", color=0x5865f2, timestamp=datetime.now())
    embed.add_field(name="אונר:", value=i.user.mention)
    embed.add_field(name="פקודה:", value=f"/{cmd.name}")
    await log.send(embed=embed)

bot.run(TOKEN)
