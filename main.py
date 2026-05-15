import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db

# --- 1. חיבור Firebase ---
TOKEN = os.getenv('DISCORD_TOKEN')
FB_CONFIG = os.getenv('FIREBASE_CONFIG')
FB_URL = os.getenv('FIREBASE_URL')

if FB_CONFIG and FB_URL:
    cred = credentials.Certificate(json.loads(FB_CONFIG))
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- 2. הגדרות IDs (המרכז של שומר השרת) ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535
CH_RECOMMENDATIONS = 1501947249658429470
CH_REPORTS = 1501946934779449505
CH_HEIST_LOGS = 1504815433004617798
MY_USER_ID = 1130542850883469443

jail_list = {} # רשימת כלואים וסכום ערבות
user_messages = {} # למערכת האנטי-ספאם

# --- 3. פונקציות נתונים ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner_check(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == MY_USER_ID

# --- 4. פאנלים קבועים (Persistent Views) ---

# פאנל חנות
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="חסינות משוד (5,000)", style=discord.ButtonStyle.success, custom_id="s_shield_f")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id)
        if bal < 5000: return await i.response.send_message("אין לך מספיק כסף בחשבון אחי!", ephemeral=True)
        update_data(i.user.id, b=bal-5000); await i.response.send_message("🛡️ קנית חסינות משודים!", ephemeral=True)

    @ui.button(label="הורדת אזהרה (10,000)", style=discord.ButtonStyle.danger, custom_id="s_unwarn_f")
    async def b2(self, i, b):
        bal, w = get_data(i.user.id)
        if bal < 10000 or w <= 0: return await i.response.send_message("או שאין לך כסף או שאין לך אזהרות להוריד!", ephemeral=True)
        update_data(i.user.id, b=bal-10000, w=w-1); await i.response.send_message("✅ אזהרה הוסרה מחשבונך!", ephemeral=True)

# פאנל פשיעה
class HeistPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שוד בנק 🏦", style=discord.ButtonStyle.danger, custom_id="h_bank_f")
    async def b1(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא, אתה לא יכול לשדוד!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.2:
            win = random.randint(500, 1000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 שוד הבנק הצליח! הרווחת {win}!", ephemeral=True)
        else:
            jail_list[i.user.id] = 2000; update_data(i.user.id, b=max(0, bal-500))
            await i.response.send_message("🚨 האזעקה הופעלה! נכנסת לכלא. ערבות: 2000", ephemeral=True)

    @ui.button(label="היתרה שלי 💳", style=discord.ButtonStyle.secondary, custom_id="h_bal_f")
    async def b2(self, i, b):
        bal, _ = get_data(i.user.id)
        await i.response.send_message(f"💳 היתרה שלך בבנק: **{bal}** מטבעות.", ephemeral=True)

# פאנל קהילה
class CommunityView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="המלצה 💡", style=discord.ButtonStyle.success, custom_id="c_rec_f")
    async def b1(self, i, b):
        modal = ui.Modal(title="המלצה לשיפור השרת")
        inp = ui.TextInput(label="מה היית רוצה להוסיף?", style=discord.TextStyle.paragraph)
        modal.add_item(inp)
        async def callback(inter):
            ch = inter.guild.get_channel(CH_RECOMMENDATIONS)
            if ch: await ch.send(embed=discord.Embed(title="💡 המלצה חדשה", description=inp.value, color=0x00ff00).set_footer(text=f"מאת: {inter.user}"))
            await inter.response.send_message("תודה! ההמלצה נשלחה לאונר.", ephemeral=True)
        modal.on_submit = callback; await i.response.send_modal(modal)

    @ui.button(label="דיווח 🚨", style=discord.ButtonStyle.danger, custom_id="c_rep_f")
    async def b2(self, i, b):
        modal = ui.Modal(title="דיווח על משתמש/תקלה")
        t = ui.TextInput(label="על מי הדיווח?"); r = ui.TextInput(label="פירוט", style=discord.TextStyle.paragraph)
        modal.add_item(t); modal.add_item(r)
        async def callback(inter):
            ch = inter.guild.get_channel(CH_REPORTS)
            if ch: await ch.send(embed=discord.Embed(title="🚨 דיווח חדש", description=f"**יעד:** {t.value}\n**סיבה:** {r.value}", color=0xff0000))
            await inter.response.send_message("הדיווח התקבל ויועבר לטיפול.", ephemeral=True)
        modal.on_submit = callback; await i.response.send_modal(modal)

# --- 5. הגדרות הבוט ופקודות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistPanelView()); self.add_view(CommunityView())
        await self.tree.sync()

bot = GuardBot()

# --- פקודות ניהול (Owner Only) ---

@bot.tree.command(name="warn", description="[Owner] נותן אזהרה למשתמש ושומר ב-Firebase")
async def warn(i, m: discord.Member, r: str):
    if await is_owner_check(i.user):
        b, w = get_data(m.id); update_data(m.id, w=w+1)
        await i.response.send_message(f"⚠️ {m.mention} הוזהר! סיבה: {r}. (סה\"כ אזהרות: {w+1})")

@bot.tree.command(name="unwarn", description="[Owner] מוריד אזהרה אחת למשתמש")
async def unwarn(i, m: discord.Member):
    if await is_owner_check(i.user):
        b, w = get_data(m.id); update_data(m.id, w=max(0, w-1))
        await i.response.send_message(f"✅ הוסרה אזהרה ל-{m.mention}. נשארו: {max(0, w-1)}")

@bot.tree.command(name="mute", description="[Owner] משתיק משתמש לזמן מוגדר")
async def mute(i, m: discord.Member, time: int):
    if await is_owner_check(i.user):
        r = i.guild.get_role(MUTE_ROLE_ID)
        await m.add_roles(r); await i.response.send_message(f"🔇 {m.mention} הושתק ל-{time} דקות.")
        await asyncio.sleep(time*60); await m.remove_roles(r)

@bot.tree.command(name="unmute", description="[Owner] מחזיר למשתמש את זכות הדיבור")
async def unmute(i, m: discord.Member):
    if await is_owner_check(i.user):
        await m.remove_roles(i.guild.get_role(MUTE_ROLE_ID)); await i.response.send_message(f"🔊 {m.mention} שוחרר מההשתקה.")

@bot.tree.command(name="clear", description="[Owner] מוחק הודעות בצ'אט")
async def clear(i, amount: int):
    if await is_owner_check(i.user):
        await i.channel.purge(limit=amount); await i.response.send_message(f"🗑️ נוקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="jail_add", description="[Owner] מכניס משתמש לכלא ידנית")
async def j_add(i, m: discord.Member, b: int = 2000):
    if await is_owner_check(i.user):
        jail_list[m.id] = b; await i.response.send_message(f"🔒 {m.mention} נשלח לכלא ע\"י האונר. ערבות: {b}")

@bot.tree.command(name="jail_remove", description="[Owner] משחרר משתמש מהכלא ללא תשלום")
async def j_rem(i, m: discord.Member):
    if await is_owner_check(i.user):
        if m.id in jail_list: del jail_list[m.id]; await i.response.send_message(f"🔓 {m.mention} שוחרר מהכלא.")

@bot.tree.command(name="give_money", description="[Owner] מעניק כסף למשתמש מהאוויר")
async def g_m(i, m: discord.Member, a: int):
    if await is_owner_check(i.user):
        bal, _ = get_data(m.id); update_data(m.id, b=bal+a); await i.response.send_message(f"💰 האונר הביא {a} מטבעות ל-{m.mention}")

# --- פקודות כלליות וכלכלה ---

@bot.tree.command(name="stats", description="מציג כסף ואזהרות (שלך או של אחר)")
async def stats(i, m: discord.Member = None):
    t = m or i.user; b, w = get_data(t.id)
    await i.response.send_message(f"📊 **סטטיסטיקה ל-{t.name}:**\n💰 כסף: {b}\n⚠️ אזהרות: {w}")

@bot.tree.command(name="pay", description="מעביר כסף מהחשבון שלך למשתמש אחר")
async def pay(i, m: discord.Member, a: int):
    b1, _ = get_data(i.user.id)
    if b1 < a or a <= 0: return await i.response.send_message("אין לך מספיק כסף להעברה!")
    b2, _ = get_data(m.id); update_data(i.user.id, b=b1-a); update_data(m.id, b=b2+a)
    await i.response.send_message(f"💸 העברת {a} מטבעות ל-{m.mention}")

@bot.tree.command(name="rob", description="מנסה לשדוד משתמש אחר (סיכון לכלא!)")
async def rob(i, m: discord.Member):
    if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!")
    if await is_owner_check(m): return await i.response.send_message("❌ האונר חסין לשודים!")
    b1, _ = get_data(i.user.id); b2, _ = get_data(m.id)
    if b2 < 200: return await i.response.send_message("הוא עני מדי, אין מה לקחת...")
    if random.random() < 0.3:
        win = int(b2 * 0.25); update_data(i.user.id, b=b1+win); update_data(m.id, b=b2-win)
        await i.response.send_message(f"🥷 הצלחת! שדדת {win} מטבעות מ-{m.name}!")
    else:
        jail_list[i.user.id] = 1500; await i.response.send_message("🚓 המשטרה תפסה אותך! נכנסת לכלא.")

@bot.tree.command(name="bail", description="משלם ערבות ויוצא מהכלא")
async def bail(i):
    if i.user.id not in jail_list: return await i.response.send_message("אתה לא בכלא אחי.")
    bal, _ = get_data(i.user.id); cost = jail_list[i.user.id]
    if bal < cost: return await i.response.send_message(f"אין לך מספיק לערבות ({cost})")
    update_data(i.user.id, b=bal-cost); del jail_list[i.user.id]
    await i.response.send_message("🔓 שילמת ויצאת לחופשי!")

# --- פקודות Setup (Owner Only) ---

@bot.tree.command(name="setup_all", description="[Owner] מקים את כל הפאנלים בבת אחת")
async def s_all(i: discord.Interaction):
    if await is_owner_check(i.user):
        await i.channel.send("🛒 **חנות השרת הרשמית**", view=ShopView())
        await i.channel.send("🕵️ **עולם הפשע (Heist Zone)**", view=HeistPanelView())
        await i.channel.send("💡 **מרכז הקהילה (המלצות ודיווחים)**", view=CommunityView())
        await i.response.send_message("כל המערכות הוקמו בהצלחה!", ephemeral=True)

# --- 6. אירועים (אנטי ספאם וכסף על הודעות) ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    uid = msg.author.id; now = datetime.now()
    # אנטי ספאם
    user_messages[uid] = [t for t in user_messages.get(uid, []) if (now - t).seconds < 5]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > 5 and not await is_owner_check(msg.author):
        r = msg.guild.get_role(MUTE_ROLE_ID)
        if r: await msg.author.add_roles(r); await msg.channel.send(f"🔇 {msg.author.mention} הושתק על ספאם.")
        return
    # כסף על הודעה
    b, w = get_data(uid); update_data(uid, b=b+10)
    await bot.process_commands(msg)

bot.run(TOKEN)
