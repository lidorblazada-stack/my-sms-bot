import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- הגדרות IDs (המגילה של לידור) ---
TOKEN = os.getenv('DISCORD_TOKEN') # שים פה את הטוקן שלך או ב-Environment
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

# דאטה-בייס פנימי (בזיכרון)
user_balances = {}
user_warns = {}
jail_list = {} # {user_id: release_time}

# --- מערכת משטרה (הודעה לפרטי של הקורבן) ---
class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber
        self.called = False

    @ui.button(label="🚨 התקשר למשטרה! (10 שניות)", style=discord.ButtonStyle.danger)
    async def call_police(self, i, b):
        self.called = True
        self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 המשטרה בדרך! השודד נעצר ונשלח לכלא לשעתיים.", ephemeral=True)
        try: await self.robber.send("🚨 נתפסת על חם! הקורבן הזעיק משטרה. אתה בכלא ל-2 שעות.")
        except: pass

# --- פאנל שודים (Heist) ---
class HeistView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h_rob_u")
    async def rob_user(self, i, b):
        if i.user.id in jail_list:
            return await i.response.send_message("❌ אתה בכלא לשעתיים, אי אפשר לשדוד!", ephemeral=True)
        
        view = ui.View()
        select = ui.UserSelect(placeholder="בחר קורבן מהרשימה...")
        
        async def callback(inter):
            target = select.values[0]
            if target.id == i.user.id: return await inter.response.send_message("טמבל, אתה לא יכול לשדוד את עצמך.", ephemeral=True)
            
            p_view = PoliceView(i.user)
            await inter.response.send_message(f"🔫 השוד התחיל... לקורבן {target.name} יש 10 שניות להזעיק משטרה!", ephemeral=True)
            
            try:
                await target.send(f"⚠️ **ניסיון שוד!** {i.user.name} מנסה לשדוד אותך! לחץ מהר על הכפתור כדי לעצור אותו:", view=p_view)
            except:
                return await inter.followup.send("❌ המשתמש הזה חסום בפרטי, אי אפשר לשדוד אותו.", ephemeral=True)

            await asyncio.sleep(10)
            if not p_view.called:
                loot = random.randint(1000, 3000)
                user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
                user_balances[target.id] = max(0, user_balances.get(target.id, 0) - loot)
                await i.followup.send(f"💰 השוד הצליח! גנבת מ-{target.name} סכום של ₪{loot}!", ephemeral=True)
                await target.send(f"💸 {i.user.name} שדד אותך וברח עם ₪{loot}...")

        select.callback = callback
        view.add_item(select)
        await i.response.send_message("מי המטרה שלך?", view=view, ephemeral=True)

    @ui.button(label="🔓 שחרר בערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="h_bail")
    async def bail(self, i, b):
        if user_balances.get(i.user.id, 0) < 5000:
            return await i.response.send_message("אין לך 5000 שקל בבנק כדי לשחרר מישהו.", ephemeral=True)
        
        view = ui.View()
        select = ui.UserSelect(placeholder="את מי לשחרר מהכלא?")
        
        async def callback(inter):
            friend = select.values[0]
            if friend.id in jail_list:
                del jail_list[friend.id]
                user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 שילמת ₪5,000 ערבות! {friend.name} משוחרר!")
            else:
                await inter.response.send_message("הוא לא בכלא אחי.", ephemeral=True)
                
        select.callback = callback
        view.add_item(select)
        await i.response.send_message("בחר חבר לשחרור:", view=view, ephemeral=True)

# --- פאנל חנות (Shop) בזוגות ---
class ShopView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="s_buy_sup", row=0)
    async def b1(self, i, b): await self.buy(i, 2000, ROLES["SUPPORTER"])

    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="s_buy_vip", row=0)
    async def b2(self, i, b): await self.buy(i, 5000, ROLES["VIP"])

    @ui.button(label="קנה Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="s_buy_staff", row=1)
    async def b3(self, i, b): await self.buy(i, 15000, ROLES["TICKET_STAFF"])

    @ui.button(label="🎁 בונוס יומי", style=discord.ButtonStyle.success, custom_id="s_daily", row=1)
    async def b4(self, i, b):
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + 1000
        await i.response.send_message("💰 קיבלת ₪1,000 בונוס יומי!", ephemeral=True)

    async def buy(self, i, p, r_id):
        bal = user_balances.get(i.user.id, 0)
        if bal < p: return await i.response.send_message(f"❌ חסר לך כסף!", ephemeral=True)
        role = i.guild.get_role(r_id)
        user_balances[i.user.id] -= p
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש על רול {role.name}!", ephemeral=True)

# --- הבוט הראשי ---
class ShomerHaSharet(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(ShopView())
        self.add_view(HeistView())
        self.check_jail.start()
        await self.tree.sync()

    @tasks.loop(seconds=30)
    async def check_jail(self):
        now = datetime.now()
        to_del = [uid for uid, time in jail_list.items() if now >= time]
        for uid in to_del: del jail_list[uid]

bot = ShomerHaSharet()

@bot.tree.command(name="setup_panels")
async def setup(i):
    if i.user.id != MY_USER_ID: return
    # חנות
    await i.channel.send(embed=discord.Embed(title="🏪 חנות השרת - Cyber Store", color=0x2b2d31), view=ShopView())
    # שודים
    await i.channel.send(embed=discord.Embed(title="🔫 עולם הפשע - Heist Panel", color=0x000000), view=HeistView())
    await i.response.send_message("הפאנלים הוקמו!", ephemeral=True)

@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    embed = discord.Embed(title="🛠️ לוג פקודות אונר", color=0x5865f2, timestamp=datetime.now())
    embed.add_field(name="מפעיל:", value=i.user.mention)
    embed.add_field(name="פקודה:", value=f"/{cmd.name}")
    await log_ch.send(embed=embed)

bot.run(TOKEN)
