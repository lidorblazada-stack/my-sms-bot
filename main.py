import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, random, asyncio
from datetime import datetime, timedelta

# --- הגדרות בסיסיות ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443

# IDs של ערוצים (לפי המגילה של לידור)
CHANNELS = {
    "SUGGESTIONS": 1501947249658429470,
    "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522,
    "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554,
    "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591,
    "LEADERBOARD": 1502014872655888554
}

# IDs של רולים
ROLES = {
    "SUPPORTER": 1503819239310627068,
    "VIP": 1503817695466881255,
    "TICKET_STAFF": 1501316672345211041,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380
}

# דאטה-בייס זמני (כדאי לחבר ל-Firebase בהמשך)
user_balances = {}
feedback_cooldown = {}

# --- 1. מערכת פידבק ודיווח ---
class FeedbackModal(ui.Modal, title="📩 שלח פידבק"):
    msg = ui.TextInput(label="מה הפידבק שלך?", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)

    async def on_submit(self, i: discord.Interaction):
        if i.user.id in feedback_cooldown and datetime.now() < feedback_cooldown[i.user.id]:
            return await i.response.send_message("❌ מותר לשלוח פידבק פעם ב-5 דקות!", ephemeral=True)
        
        user_display = "👤 אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="✨ פידבק חדש", description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_footer(text=f"נשלח ע\"י: {user_display}")
        
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="שלח פידבק חדש", style=discord.ButtonStyle.secondary, custom_id="new_fb_btn"))
        
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        feedback_cooldown[i.user.id] = datetime.now() + timedelta(minutes=5)
        await i.response.send_message("✅ הפידבק נשלח!", ephemeral=True)

# --- 2. מערכת שודים (Heist) ---
class RobUserSelect(ui.UserSelect, placeholder="בחר משתמש לשדוד..."):
    async def callback(self, i: discord.Interaction):
        target = self.values[0]
        if target.id == i.user.id: return await i.response.send_message("אתה לא יכול לשדוד את עצמך, טמבל.", ephemeral=True)
        
        chance = random.randint(1, 100)
        if chance > 50:
            loot = random.randint(500, 2000)
            user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
            user_balances[target.id] = max(0, user_balances.get(target.id, 0) - loot)
            await i.response.send_message(f"🔫 השוד הצליח! גנבת ל-{target.name} `{loot}` מטבעות!", ephemeral=True)
        else:
            await i.response.send_message(f"🚨 נכשלת בשוד! {target.name} הזמין משטרה.", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="heist:bank")
    async def rob_bank(self, i, b):
        chance = random.randint(1, 100)
        if chance > 60:
            loot = random.randint(2000, 5000)
            user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
            await i.response.send_message(f"🏦 השוד הצליח! ברחת מהבנק עם `{loot}` מטבעות!", ephemeral=True)
        else:
            await i.response.send_message("🚨 האזעקה הופעלה! נכשלת בשוד.", ephemeral=True)

    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="heist:user")
    async def rob_user_btn(self, i, b):
        view = ui.View(); view.add_item(RobUserSelect())
        await i.response.send_message("בחר את הקורבן:", view=view, ephemeral=True)

    @ui.button(label="💳 יתרה", style=discord.ButtonStyle.success, custom_id="heist:bal")
    async def check_bal(self, i, b):
        bal = user_balances.get(i.user.id, 0)
        await i.response.send_message(f"💰 היתרה שלך: `{bal}` מטבעות.", ephemeral=True)

# --- 3. חנות (Shop) במבנה זוגות ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supporter", row=0)
    async def buy_supp(self, i, b): await self.handle_buy(i, 2000, ROLES["SUPPORTER"])

    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i, b): await self.handle_buy(i, 5000, ROLES["VIP"])

    @ui.button(label="קנה Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i, b): await self.handle_buy(i, 15000, ROLES["TICKET_STAFF"])

    @ui.button(label="🎁 בונוס יומי", style=discord.ButtonStyle.success, custom_id="shop:daily", row=1)
    async def daily(self, i, b):
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + 1000
        await i.response.send_message("💰 קיבלת בונוס של `1000` מטבעות!", ephemeral=True)

    async def handle_buy(self, i, price, role_id):
        bal = user_balances.get(i.user.id, 0)
        if bal < price: return await i.response.send_message(f"❌ חסר לך `{price - bal}` מטבעות!", ephemeral=True)
        role = i.guild.get_role(role_id)
        if not role or role in i.user.roles: return await i.response.send_message("❌ תקלה או שכבר יש לך את הרול.", ephemeral=True)
        user_balances[i.user.id] -= price
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש על הרול {role.name}!", ephemeral=True)

# --- 4. מערכת אנטי-אלט ---
class AntiAltView(ui.View):
    def __init__(self, m):
        super().__init__(timeout=None)
        self.m = m
    @ui.button(label="להעיף", style=discord.ButtonStyle.danger)
    async def k(self, i, b): await self.m.kick(); await i.response.send_message("הועף.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success)
    async def s(self, i, b): await i.response.send_message("אושר.")
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary)
    async def r(self, i, b): await self.m.add_roles(i.guild.get_role(ROLES["SUSPECT"])); await i.response.send_message("חשוד.")

# --- 5. הבוט המרכזי ---
class CyberBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView())
        self.update_lb.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_lb(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            em = discord.Embed(title="🏆 טבלת עשירים", color=0xffd700)
            em.description = "מתעדכן כל 5 דקות..."
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=em)

bot = CyberBot()

@bot.tree.command(name="setup_all")
async def setup_all(i: discord.Interaction):
    if i.user.id != MY_USER_ID: return
    # חנות
    emb_shop = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
    emb_shop.add_field(name="🎗️ | Supporter", value="2,000 Coins", inline=True)
    emb_shop.add_field(name="💎 | VIP", value="5,000 Coins", inline=True)
    await i.channel.send(embed=emb_shop, view=ShopView())
    # הייסט
    await i.channel.send(embed=discord.Embed(title="🔫 פאנל פשע ושודים", color=0x000000), view=HeistView())
    await i.response.send_message("הכל הוקם!", ephemeral=True)

@bot.event
async def on_member_join(m):
    await m.guild.get_channel(CHANNELS["WELCOME"]).send(f"👋 ברוך הבא {m.mention}!")
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        await m.guild.get_channel(CHANNELS["ANTI_ALT"]).send(f"🚨 אלט חשוד: {m.mention}", view=AntiAltView(m))

@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log_ch.send(f"🛠️ `{i.user.name}` הריץ `/{cmd.name}`")

bot.run(TOKEN)
