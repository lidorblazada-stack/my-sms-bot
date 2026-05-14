import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import os
from collections import defaultdict

# --- הגדרות ו-IDs (לפי מה שסיפקת) ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ROLE_ID = 1499868525844627478  # רול אונר
LOG_CH_ID = 1503496964732354620       # לוג ניסיונות פריצה
ALT_LOG_ID = 1503464176599695380      # לוג אלטים
SUSPECT_ROLE_ID = 1503464176599695380 # רול חשוד

# רולים לחנות
ROLE_SUPPORTER = 1503819239310627068
ROLE_VIP = 1503817695466881255
ROLE_TICKET_STAFF = 1501316672345211041

# דאטה (בזיכרון - מתאפס בריסטארט)
user_balances = defaultdict(int)
attack_warnings = defaultdict(int)

# --- 1. חנות מעוצבת (בדיוק לפי הבקשה האחרונה) ---
class ShopView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="shop:supporter", row=0)
    async def buy_supp(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 2000, ROLE_SUPPORTER)

    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.primary, custom_id="shop:vip", row=0)
    async def buy_vip(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 5000, ROLE_VIP)

    @ui.button(label="קנה Ticket-Staff 🛠️", style=discord.ButtonStyle.danger, custom_id="shop:staff", row=1)
    async def buy_staff(self, i: discord.Interaction, b: ui.Button):
        await self.handle_purchase(i, 15000, ROLE_TICKET_STAFF)

    @ui.button(label="בדיקת יתרה 💳", style=discord.ButtonStyle.success, custom_id="shop:bal", row=1)
    async def check_bal(self, i: discord.Interaction, b: ui.Button):
        bal = user_balances[i.user.id]
        await i.response.send_message(f"💰 היתרה הנוכחית שלך: `{bal}` מטבעות.", ephemeral=True)

    async def handle_purchase(self, i, price, role_id):
        bal = user_balances[i.user.id]
        if bal < price:
            return await i.response.send_message(f"❌ חסר לך `{price - bal}` מטבעות!", ephemeral=True)
        
        role = i.guild.get_role(role_id)
        if not role or role in i.user.roles:
            return await i.response.send_message("❌ תקלה ברול או שכבר יש לך אותו!", ephemeral=True)

        user_balances[i.user.id] -= price
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ תתחדש! קיבלת את הרול **{role.name}**!", ephemeral=True)

# --- 2. ניהול אלטים (השארה/העפה/חשוד) ---
class AltActionView(ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @ui.button(label="להעיף 👞", style=discord.ButtonStyle.danger)
    async def kick_alt(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.member_id)
        if m: await m.kick(); await i.response.send_message("הועף", ephemeral=True); await i.message.delete()

    @ui.button(label="להשאיר ✅", style=discord.ButtonStyle.success)
    async def stay_alt(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        await i.response.send_message("אושר", ephemeral=True); await i.message.delete()

    @ui.button(label="רול חשוד ⚠️", style=discord.ButtonStyle.secondary)
    async def suspect_alt(self, i, b):
        if not any(r.id == OWNER_ROLE_ID for r in i.user.roles): return
        m = i.guild.get_member(self.member_id)
        r = i.guild.get_role(SUSPECT_ROLE_ID)
        if m and r: await m.add_roles(r); await i.response.send_message("ניתן רול חשוד", ephemeral=True); await i.message.delete()

# --- 3. מנגנון הגנה על פקודות אונר ---
async def check_owner_and_punish(i: discord.Interaction):
    if any(role.id == OWNER_ROLE_ID for role in i.user.roles):
        return True
    
    await i.response.send_message(f"❌ אזהרה מילולית! אין לך גישה לפקודה זו.", ephemeral=True)
    attack_warnings[i.user.id] += 1
    count = attack_warnings[i.user.id]
    
    log_ch = i.guild.get_channel(LOG_CH_ID)
    if log_ch: await log_ch.send(f"⚠️ **ניסיון פריצה:** {i.user.mention} ניסה להשתמש ב-`/{i.command.name}`. פעם מספר: {count}/5")

    if count == 3:
        await i.user.timeout(timedelta(days=2), reason="3 ניסיונות פריצה לפקודות אונר")
        try: await i.user.send("⚠️ הושתקת ליומיים עקב ניסיונות פריצה למערכת הפקודות.")
        except: pass
    elif count >= 5:
        await i.user.kick(reason="5 ניסיונות פריצה - עונש סופי")
        attack_warnings[i.user.id] = 0
    return False

# --- 4. הגדרות בוט ואירועים ---
class GuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(ShopView())
        await self.tree.sync()

bot = GuardBot()

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        user_balances[msg.author.id] += 5 # 5 מטבעות לכל הודעה
    await bot.process_commands(msg)

@bot.event
async def on_member_join(member):
    if (datetime.utcnow() - member.created_at).days < 7:
        ch = member.guild.get_channel(ALT_LOG_ID)
        if ch:
            emb = discord.Embed(title="⚠️ זיהוי חשבון חדש (Alt)", description=f"המשתמש {member.mention} הצטרף. מה לעשות?", color=0xffa500)
            await ch.send(embed=emb, view=AltActionView(member.id))

# --- 5. פקודות אונר בלבד ---
@bot.tree.command(name="setup_shop", description="[OWNER] הקמת החנות המעוצבת")
async def setup_shop(i: discord.Interaction):
    if await check_owner_and_punish(i):
        emb = discord.Embed(title="═══ 💠 CYBER-STORE MARKET 💠 ═══", color=0x2b2d31)
        emb.description = "👋 **ברוכים הבאים לחנות!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        emb.add_field(name="🎗️ | Server-Supporter", value="**Price:** 2,000 Coins\nרול כבוד למשתתפים פעילים.", inline=False)
        emb.add_field(name="💎 | VIP Member", value="**Price:** 5,000 Coins\nגישה לחדרי VIP וצבע בולט.", inline=False)
        emb.add_field(name="🛠️ | TICKET-STAFF", value="**Price:** 15,000 Coins\n**הגישה למערכת הטיקטים!**", inline=False)
        emb.set_footer(text="Developed by NL 👑")
        await i.channel.send(embed=emb, view=ShopView())
        await i.response.send_message("החנות הוקמה!", ephemeral=True)

@bot.tree.command(name="add_money", description="[OWNER] הוספת כסף למשתמש")
async def add_money(i, member: discord.Member, amount: int):
    if await check_owner_and_punish(i):
        user_balances[member.id] += amount
        await i.response.send_message(f"💵 נוספו `{amount}` מטבעות ל-{member.mention}")

@bot.tree.command(name="clear", description="[OWNER] מחיקת הודעות")
async def clear(i, amount: int):
    if await check_owner_and_punish(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"נמחקו {amount} הודעות", ephemeral=True)

bot.run(TOKEN)
