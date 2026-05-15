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

# --- 2. הגדרות IDs (הכל פה אחי!) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535       
CH_RECOMMENDATIONS = 1501947249658429470 
CH_REPORTS = 1501946934779449505         
CH_HEIST_LOGS = 1504815433004617798
MY_USER_ID = 1130542850883469443

user_messages = {}
rob_cooldowns = {}
jail_list = {} # {'uid': [time, bail_amount]}

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

# --- 4. מודאלים (חלוניות כתיבה) ---
class RecommendationModal(ui.Modal, title="המלצה חדשה לשרת"):
    rec_input = ui.TextInput(label="מה ההמלצה שלך?", style=discord.TextStyle.paragraph, placeholder="רשום כאן...", required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_RECOMMENDATIONS)
        emb = discord.Embed(title="💡 המלצה חדשה", description=self.rec_input.value, color=discord.Color.green())
        emb.set_footer(text=f"נשלח ע\"י {i.user}", icon_url=i.user.display_avatar.url)
        if ch: await ch.send(embed=emb)
        await i.response.send_message("תודה על ההמלצה אחי!", ephemeral=True)

class ReportModal(ui.Modal, title="דיווח על משתמש / תקלה"):
    target = ui.TextInput(label="על מי/מה הדיווח?", placeholder="שם המשתמש או הבעיה", required=True)
    reason = ui.TextInput(label="פירוט הדיווח", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(CH_REPORTS)
        emb = discord.Embed(title="🚨 דיווח חדש", color=discord.Color.red())
        emb.add_field(name="הנידון", value=self.target.value)
        emb.add_field(name="פירוט", value=self.reason.value)
        emb.set_footer(text=f"דווח ע\"י {i.user}")
        if ch: await ch.send(embed=emb)
        await i.response.send_message("הדיווח התקבל ויועבר לטיפול האונר.", ephemeral=True)

# --- 5. מערכת השודים והכלא ---
class PoliceCallView(ui.View):
    def __init__(self, robber, victim, amount):
        super().__init__(timeout=10)
        self.robber, self.victim, self.amount = robber, victim, amount
        self.caught = False
    @ui.button(label="🚨 קרא למשטרה!", style=discord.ButtonStyle.danger)
    async def call_police(self, i, b):
        self.caught = True; self.stop()
        jail_list[self.robber.id] = [datetime.now(), self.amount * 10]
        r_bal, _ = get_data(self.robber.id); v_bal, _ = get_data(self.victim.id)
        update_data(self.robber.id, b=max(0, r_bal - (self.amount + 200)))
        update_data(self.victim.id, b=v_bal + self.amount)
        await i.response.send_message("👮 תפסת את השודד! הוא בכלא.", ephemeral=True)

class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def h_bank(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        s_bal, _ = get_data(i.user.id); win = random.randint(300, 800)
        if random.randint(1, 100) <= 20:
            update_data(i.user.id, b=s_bal+win); await i.response.send_message(f"💰 הצלחת! {win} מטבעות.", ephemeral=True)
        else:
            update_data(i.user.id, b=max(0, s_bal-500)); await i.response.send_message("🚨 נתפסת!", ephemeral=True)

    @ui.button(label="שוד משתמש 🥷", style=discord.ButtonStyle.primary, custom_id="h_user")
    async def h_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        v = ui.View(); v.add_item(VictimSelectView())
        await i.response.send_message("בחר קורבן:", view=v, ephemeral=True)

    @ui.button(label="שחרור בערבות 💸", style=discord.ButtonStyle.success, custom_id="h_bail")
    async def h_bail(self, i, b):
        v = ui.View(); v.add_item(BailSelect())
        await i.response.send_message("מי לשחרר?", view=v, ephemeral=True)

# --- 6. בוט ופקודות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistPanelView())
        self.add_view(ui.View().add_item(ui.Button(label="שלח המלצה 💡", style=discord.ButtonStyle.success, custom_id="btn_rec")))
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_recommendations", description="הקמת פאנל המלצות")
async def s_rec(i: discord.Interaction):
    if await is_owner_check(i.user):
        v = ui.View(timeout=None)
        btn = ui.Button(label="שלח המלצה 💡", style=discord.ButtonStyle.success, custom_id="btn_rec")
        btn.callback = lambda inter: inter.response.send_modal(RecommendationModal())
        v.add_item(btn)
        await i.channel.send("💡 **יש לכם רעיון לשיפור השרת? נשמח לשמוע!**", view=v)
        await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="setup_reports", description="הקמת פאנל דיווחים")
async def s_rep(i: discord.Interaction):
    if await is_owner_check(i.user):
        v = ui.View(timeout=None)
        btn = ui.Button(label="דווח כאן 🚨", style=discord.ButtonStyle.danger, custom_id="btn_rep")
        btn.callback = lambda inter: inter.response.send_modal(ReportModal())
        v.add_item(btn)
        await i.channel.send("🚨 **נתקלתם בבעיה או משתמש שעובר על החוקים? דווחו לנו.**", view=v)
        await i.response.send_message("הוקם.", ephemeral=True)

@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    if await is_owner_check(i.user):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר על {r}.")

@bot.tree.command(name="clear")
async def clear(i, a: int):
    if await is_owner_check(i.user):
        await i.channel.purge(limit=a); await i.response.send_message(f"נמחקו {a}", ephemeral=True)

@bot.tree.command(name="setup_heist")
async def s_h(i: discord.Interaction):
    if await is_owner_check(i.user):
        emb = discord.Embed(title="🥷 HEIST ZONE", description="מערכת הפשיעה של האונר", color=0x2b2d31)
        emb.set_image(url="https://images2.alphacoders.com/519/519509.jpg")
        await i.channel.send(embed=emb, view=HeistPanelView())
        await i.response.send_message("הוקם.", ephemeral=True)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = msg.author.id; now = datetime.now()
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not await is_owner_check(msg.author):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r)
        return
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

bot.run(TOKEN)
