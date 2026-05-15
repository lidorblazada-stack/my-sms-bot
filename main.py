import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs (שומר השרת) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
MEMBER_ROLE_ID = 1501983948111352091
CH_HEIST_LOGS = 1504815433004617798
MY_USER_ID = 1130542850883469443

user_messages = {}
rob_cooldowns = {}
jail_list = {} # {'uid': [time, bail_amount]}
last_robbed = {}

# --- 3. פונקציות נתונים ועזר ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner_check(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == MY_USER_ID

async def send_heist_log(guild, text):
    ch = guild.get_channel(CH_HEIST_LOGS)
    if ch: await ch.send(f"📋 **לוג מערכת:** {text}")

# --- 4. מערכת המשטרה והכלא ---
class PoliceCallView(ui.View):
    def __init__(self, robber, victim, amount):
        super().__init__(timeout=10)
        self.robber, self.victim, self.amount = robber, victim, amount
        self.caught = False

    @ui.button(label="🚨 קרא למשטרה!", style=discord.ButtonStyle.danger)
    async def call_police(self, i: discord.Interaction, b: ui.Button):
        self.caught = True; self.stop()
        bail = self.amount * 10
        jail_list[self.robber.id] = [datetime.now(), bail]
        r_bal, _ = get_data(self.robber.id); v_bal, _ = get_data(self.victim.id)
        update_data(self.robber.id, b=max(0, r_bal - (self.amount + 200)))
        update_data(self.victim.id, b=v_bal + self.amount)
        await i.response.send_message(f"👮 המשטרה הגיעה! השודד נשלח לכלא! ערבות לשחרור: {bail}", ephemeral=True)
        await send_heist_log(i.guild, f"הקורבן {self.victim.mention} תפס את {self.robber.mention}! השודד נשלח לכלא.")

# --- 5. שחרור בערבות ---
class BailSelect(ui.UserSelect):
    def __init__(self): super().__init__(placeholder="בחר משתמש לשחרור מהכלא... 💸", min_values=1, max_values=1)
    async def callback(self, i: discord.Interaction):
        target = self.values[0]
        if target.id not in jail_list: return await i.response.send_message("הוא לא בכלא אחי.", ephemeral=True)
        bail_cost = jail_list[target.id][1]
        my_bal, _ = get_data(i.user.id)
        if my_bal < bail_cost: return await i.response.send_message(f"אין לך מספיק כסף! צריך {bail_cost}", ephemeral=True)
        update_data(i.user.id, b=my_bal - bail_cost); del jail_list[target.id]
        await i.response.send_message(f"✅ שחררת את {target.mention} מהכלא!", ephemeral=True)
        await send_heist_log(i.guild, f"{i.user.mention} שילם ערבות ושחרר את {target.mention}.")

# --- 6. מערכת השודים ---
class RobAmountSelect(ui.Select):
    def __init__(self, victim):
        self.victim = victim
        options = [
            discord.SelectOption(label="100 מטבעות", description="50% הצלחה | ערבות: 1000", value="100"),
            discord.SelectOption(label="200 מטבעות", description="30% הצלחה | ערבות: 2000", value="200"),
            discord.SelectOption(label="300 מטבעות", description="15% הצלחה | ערבות: 3000", value="300")
        ]
        super().__init__(placeholder="בחר סכום לשוד...", options=options)

    async def callback(self, i: discord.Interaction):
        amount = int(self.values[0]); uid = i.user.id
        chance = 50 if amount == 100 else 30 if amount == 200 else 15
        rob_cooldowns[uid] = datetime.now()
        s_bal, _ = get_data(uid); v_bal, _ = get_data(self.victim.id)

        if random.randint(1, 100) <= chance:
            update_data(uid, b=s_bal + amount); update_data(self.victim.id, b=v_bal - amount)
            await i.response.send_message(f"🥷 השוד הצליח! לקחת {amount}. לקורבן יש 10 שניות לקרוא למשטרה...", ephemeral=True)
            view = PoliceCallView(i.user, self.victim, amount)
            try: await self.victim.send(f"⚠️ **נשדדת!** {i.user.name} לקח לך {amount} מטבעות! יש לך 10 שניות לקרוא למשטרה!", view=view)
            except: pass
        else:
            bail = amount * 10
            jail_list[uid] = [datetime.now(), bail]
            update_data(uid, b=max(0, s_bal - amount))
            await i.response.send_message(f"🚓 המשטרה תפסה אותך! נכנסת לכלא לשעתיים. ערבות: {bail}", ephemeral=True)
            await send_heist_log(i.guild, f"{i.user.mention} נכשל בשוד של {self.victim.mention} ונכנס לכלא.")

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא אחי!", ephemeral=True)
        if i.user.id in rob_cooldowns and (datetime.now() - rob_cooldowns[i.user.id]).seconds < 3600:
            return await i.response.send_message("⏳ חכה שעה בין פשיעות.", ephemeral=True)
        s_bal, _ = get_data(i.user.id); rob_cooldowns[i.user.id] = datetime.now()
        if random.randint(1, 100) <= 20:
            win = random.randint(300, 800); update_data(i.user.id, b=s_bal+win)
            await i.response.send_message(f"💰 הבנק נפרץ! השגת {win} מטבעות!", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת בבנק! קנס של 500.", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא אחי!", ephemeral=True)
        v = ui.View(); v.add_item(VictimSelectView())
        await i.response.send_message("מי הקורבן שלך? 😈", view=v, ephemeral=True)

    @ui.button(label="שחרור בערבות 💸", style=discord.ButtonStyle.success, custom_id="h_bail")
    async def h_bail(self, i, b):
        v = ui.View(); v.add_item(BailSelect())
        await i.response.send_message("מי אתה רוצה לשחרר?", view=v, ephemeral=True)

class VictimSelectView(ui.UserSelect):
    def __init__(self): super().__init__(placeholder="בחר קורבן...", min_values=1, max_values=1)
    async def callback(self, i: discord.Interaction):
        victim = self.values[0]
        if await is_owner_check(victim): return await i.response.send_message("❌ אונר חסין לשודים!", ephemeral=True)
        v = ui.View(); v.add_item(RobAmountSelect(victim))
        await i.response.send_message(f"בחרת ב-{victim.name}. כמה אתה מסכן?", view=v, ephemeral=True)

# --- 7. בוט ופקודות ניהול (שומר השרת) ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(HeistPanelView()); await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="warn", description="[Owner] מתן אזהרה למשתמש")
async def warn(i: discord.Interaction, m: discord.Member, reason: str):
    if await is_owner_check(i.user):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר! סיבה: {reason}. (אזהרות: {w+1})")
        await send_heist_log(i.guild, f"{m.name} קיבל אזהרה מהאונר על {reason}.")

@bot.tree.command(name="mute", description="[Owner] השתקת משתמש")
async def mute(i: discord.Interaction, m: discord.Member):
    if await is_owner_check(i.user):
        await m.add_roles(i.guild.get_role(MUTE_ROLE_ID))
        await i.response.send_message(f"🔇 {m.mention} הושתק.")

@bot.tree.command(name="ban", description="[Owner] הרחקת משתמש")
async def ban(i: discord.Interaction, m: discord.Member, r: str = "לא צוינה"):
    if await is_owner_check(i.user):
        await m.ban(reason=r); await i.response.send_message(f"🔨 {m.name} הורחק מהשרת.")

@bot.tree.command(name="jail_add", description="[Owner] הכנסה לכלא ידנית")
async def j_add(i: discord.Interaction, m: discord.Member, bail: int = 2000):
    if await is_owner_check(i.user):
        jail_list[m.id] = [datetime.now(), bail]
        await i.response.send_message(f"🔒 {m.mention} נכלא ע\"י האונר! ערבות: {bail}")

@bot.tree.command(name="jail_remove", description="[Owner] שחרור מהכלא")
async def j_rem(i: discord.Interaction, m: discord.Member):
    if await is_owner_check(i.user):
        if m.id in jail_list:
            del jail_list[m.id]; await i.response.send_message(f"🔓 {m.mention} שוחרר!")
        else: await i.response.send_message("הוא לא בכלא.", ephemeral=True)

@bot.tree.command(name="clear", description="[Owner] ניקוי צ'אט")
async def clear(i: discord.Interaction, amount: int):
    if await is_owner_check(i.user):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🗑️ נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="setup_heist", description="[Owner] הקמת פאנל הפשיעה")
async def s_h(i: discord.Interaction):
    if await is_owner_check(i.user):
        emb = discord.Embed(title="🥷 HEIST ZONE | עולם הפשע", description="מערכת הפשיעה הרשמית של השרת.\nמנוהל ע\"י המערכת של האונר.", color=0x2b2d31)
        emb.add_field(name="⚖️ חוקי הכלא", value="• כישלון בשוד משתמש = כלא לשעתיים.\n• ניתן להשתחרר בערבות ע\"י חבר.", inline=False)
        emb.set_image(url="https://images2.alphacoders.com/519/519509.jpg")
        emb.set_footer(text="Guard of the Server | Owner System")
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("✅ הפאנל הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="stats", description="בדיקת מצב חשבון")
async def stats(i: discord.Interaction, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **סטטיסטיקה עבור {t.name}:**\n💰 כסף: {b}\n⚠️ אזהרות: {w}")

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = msg.author.id; now = datetime.now()
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not await is_owner_check(msg.author):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

bot.run(TOKEN)
