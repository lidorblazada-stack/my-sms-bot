import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (מעודכן לפי הבקשות שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443
SECOND_ID = 1493293951959044147

WELCOME_CH_ID = 1501713652217282591 
FEEDBACK_CH_ID = 1503475379942461522
OWNER_CMD_ROLE_ID = 1502014872655888554
MEMBER_ROLE_ID = 1501983948111352091
MUTE_2DAYS_ROLE_ID = 1501953906736103535

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה-בייס בזיכרון
user_warnings = defaultdict(int)
user_balances = defaultdict(int)
owner_attempt_tracker = set()
spam_tracker = defaultdict(list)

# --- פונקציית ענישה (שומר השרת) ---
async def apply_punishment(interaction, member, count, reason):
    if count == 3:
        role = interaction.guild.get_role(MUTE_2DAYS_ROLE_ID)
        if role: await member.add_roles(role)
        try: await member.send(f"🔇 הושתקת ליומיים בשרת {interaction.guild.name}.")
        except: pass
        return f"⚠️ {member.mention} הגיע ל-3 אזהרות והושתק ליומיים!"
    elif count >= 5:
        try: await member.send(f"👢 הועפת מהשרת {interaction.guild.name} (5 אזהרות).")
        except: pass
        await member.kick(reason="5 אזהרות")
        user_warnings[member.id] = 0
        return f"👢 {member.mention} הועף מהשרת!"
    return f"⚠️ {member.mention} הוזהר ({count}/5). סיבה: {reason}"

# --- Views (פידבק ואימות - בדיוק כמו שרצית) ---
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
        if not is_anon: emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        else: emb.set_author(name="משתמש אנונימי")
        await ch.send(embed=emb); await i.response.send_message("נשלח!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💥", style=discord.ButtonStyle.green, custom_id="fb_v1")
    async def f(self, i, b): await i.response.send_modal(FeedbackModal())

# --- View של החנות (זוגות) ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supp", row=0)
    async def buy_supp(self, i, b): await self.handle_buy(i, 2000, ROLE_SUPPORTER)

    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i, b): await self.handle_buy(i, 5000, ROLE_VIP)

    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i, b): await self.handle_buy(i, 15000, ROLE_TICKET_STAFF)

    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop:bal", row=1)
    async def check_bal(self, i, b):
        bal = user_balances.get(i.user.id, 0)
        await i.response.send_message(f"💰 היתרה שלך: `{bal}`", ephemeral=True)

    async def handle_buy(self, i, price, role_id):
        bal = user_balances.get(i.user.id, 0)
        if bal < price: return await i.response.send_message("❌ אין לך מספיק כסף!", ephemeral=True)
        role = i.guild.get_role(role_id)
        if role in i.user.roles: return await i.response.send_message("❌ כבר יש לך את הרול!", ephemeral=True)
        user_balances[i.user.id] = bal - price
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש על {role.name}!", ephemeral=True)

# --- ליבת הבוט המאוחד ---
class CyberAllInOne(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView()); self.add_view(ShopView())
        await self.tree.sync()

bot = CyberAllInOne()

# --- אירועים (ספאם, כסף, הצטרפות) ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # אנטי ספאם
    now = asyncio.get_event_loop().time()
    spam_tracker[msg.author.id].append(now)
    if len([t for t in spam_tracker[msg.author.id] if now - t < 3]) > 5:
        await msg.author.timeout(timedelta(minutes=10))
        return await msg.channel.send(f"🔇 {msg.author.mention} הושתק (ספאם).", delete_after=5)
    # כסף
    user_balances[msg.author.id] += 10
    await bot.process_commands(msg)

# --- פקודות הקמה נפרדות ---
@bot.tree.command(name="setup_verify", description="הקמת הודעת אימות")
async def sv(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="🛡️ אימות", color=0x2ecc71), view=VerifyView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת הודעת פידבק")
async def sf(i):
    if i.user.id == MY_USER_ID: await i.channel.send(embed=discord.Embed(title="💬 פידבק אנונימי", color=0x00ffff), view=FeedbackView()); await i.response.send_message("בוצע", ephemeral=True)

@bot.tree.command(name="setup_shop", description="הקמת הודעת חנות")
async def ss(i):
    if i.user.id == MY_USER_ID:
        emb = discord.Embed(title="═══ 💠 CYBER-STORE 💠 ═══", color=0x2b2d31)
        emb.add_field(name="🎗️ Supporter", value="`2,000`", inline=True)
        emb.add_field(name="💎 VIP", value="`5,000`", inline=True)
        emb.add_field(name="🛠️ Ticket-Staff", value="`15,000`", inline=False)
        await i.channel.send(embed=emb, view=ShopView()); await i.response.send_message("בוצע", ephemeral=True)

# פקודות ניהול
@bot.tree.command(name="add_warn", description="הוספת אזהרה")
async def aw(i, member: discord.Member, reason: str):
    if i.user.id == MY_USER_ID:
        user_warnings[member.id] += 1
        res = await apply_punishment(i, member, user_warnings[member.id], reason)
        await i.response.send_message(res)

@bot.tree.command(name="add_money", description="הוספת כסף")
async def am(i, member: discord.Member, amount: int):
    if i.user.id == MY_USER_ID:
        user_balances[member.id] += amount
        await i.response.send_message(f"נוספו {amount} ל-{member.mention}")

bot.run(TOKEN)
