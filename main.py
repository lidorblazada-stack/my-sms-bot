import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, json, random, asyncio
from datetime import datetime, timedelta

# --- 1. הגדרות ו-IDs מהמגילה של לידור ---
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = 1130542850883469443

CHANNELS = {
    "SUGGESTIONS": 1501947249658429470, # המלצות
    "REPORTS": 1501946934779449505,      # דיווחים
    "FEEDBACK": 1503475379942461522,      # פידבק אנונימי
    "OWNER_LOGS": 1503496964732354620,    # לוגים אונר
    "WARNS_LOG": 1502014872655888554,     # אזהרות
    "ANTI_ALT": 1503464176599695380,      # אנטי אלט
    "WELCOME": 1501713652217282591,       # וולקם
    "LEADERBOARD": 1502014872655888554    # טבלה
}
ROLES = {
    "OWNER": 1499868525844627478,
    "MUTE": 1501953906736103535,
    "SUSPECT": 1503464176599695380
}

# --- 2. מערכת פידבק חכמה ---
fb_cooldown = {}

class FeedbackModal(ui.Modal, title="📩 שלח פידבק חדש"):
    msg = ui.TextInput(label="הפידבק שלך (אחד ל-5 דקות)", style=discord.TextStyle.paragraph, min_length=5)
    anon = ui.TextInput(label="אנונימי? (כן/לא)", default="לא", max_length=2)

    async def on_submit(self, i):
        if i.user.id in fb_cooldown and datetime.now() < fb_cooldown[i.user.id]:
            return await i.response.send_message("❌ מותר לשלוח פידבק פעם ב-5 דקות!", ephemeral=True)
        
        display_name = "👤 משתמש אנונימי" if self.anon.value == "כן" else i.user.name
        embed = discord.Embed(title="✨ פידבק חדש", description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_footer(text=f"מאת: {display_name}")
        
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="שלח פידבק נוסף", style=discord.ButtonStyle.secondary, custom_id="fb_more"))
        
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        fb_cooldown[i.user.id] = datetime.now() + timedelta(minutes=5)
        await i.response.send_message("✅ נשלח!", ephemeral=True)

# --- 3. פאנלים קבועים (Views) ---

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def bank(self, i, b):
        res = random.choice(["הצלחת! שדדת ₪5,000", "נכשלת! המשטרה תפסה אותך"])
        await i.response.send_message(f"🚨 {res}", ephemeral=True)
    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.secondary, custom_id="h_user")
    async def rob(self, i, b): await i.response.send_message("🔫 בחר משתמש (פקודת /rob)", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎁 בונוס יומי", style=discord.ButtonStyle.success, custom_id="s_daily")
    async def daily(self, i, b): await i.response.send_message("💰 קיבלת ₪1,000 בונוס (זמין פעם ביום)", ephemeral=True)

class SupportView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 פידבק", style=discord.ButtonStyle.primary, custom_id="v_feed")
    async def feed(self, i, b): await i.response.send_modal(FeedbackModal())
    @ui.button(label="🚨 דיווח", style=discord.ButtonStyle.danger, custom_id="v_rep")
    async def rep(self, i, b):
        modal = ui.Modal(title="דיווח")
        modal.add_item(ui.TextInput(label="על מי?"))
        modal.add_item(ui.TextInput(label="סיבה", style=discord.TextStyle.paragraph))
        async def on_rep_submit(inter):
            ch = inter.guild.get_channel(CHANNELS["REPORTS"])
            em = discord.Embed(title="🚨 דיווח חדש", color=0xff0000)
            em.add_field(name="מאת", value=inter.user.name); em.add_field(name="סיבה", value=modal.children[1].value)
            await ch.send(embed=em); await inter.response.send_message("נשלח", ephemeral=True)
        modal.on_submit = on_rep_submit
        await i.response.send_modal(modal)

class AntiAltView(ui.View):
    def __init__(self, m):
        super().__init__(timeout=None)
        self.m = m
    @ui.button(label="להעיף", style=discord.ButtonStyle.danger, custom_id="alt_kick")
    async def kick(self, i, b): await self.m.kick(); await i.response.send_message("הועף.")
    @ui.button(label="להשאיר", style=discord.ButtonStyle.success, custom_id="alt_stay")
    async def stay(self, i, b): await i.response.send_message("אושר.")
    @ui.button(label="רול חשוד", style=discord.ButtonStyle.secondary, custom_id="alt_sus")
    async def sus(self, i, b): 
        await self.m.add_roles(i.guild.get_role(ROLES["SUSPECT"]))
        await i.response.send_message("רול חשוד ניתן.")

# --- 4. הבוט המרכזי ---
class ShomerHaSharet(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(HeistView()); self.add_view(ShopView()); self.add_view(SupportView())
        self.update_lb.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_lb(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            em = discord.Embed(title="🏆 עשירי השרת", description="🥇 Nehoray\n🥈 Lidor", color=0xffd700)
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=em)

bot = ShomerHaSharet()

# --- 5. פקודות סטאפ ואונר ---
@bot.tree.command(name="setup")
async def setup(i):
    if i.user.id != OWNER_ID: return
    await i.channel.send(embed=discord.Embed(title="🛒 חנות", color=0x2f3136), view=ShopView())
    await i.channel.send(embed=discord.Embed(title="🔫 שודים", color=0x000000), view=HeistView())
    await i.channel.send(embed=discord.Embed(title="📩 תמיכה ופידבק", color=0x00fbff), view=SupportView())
    await i.response.send_message("הפאנלים הוקמו!", ephemeral=True)

@bot.event
async def on_member_join(m):
    await m.guild.get_channel(CHANNELS["WELCOME"]).send(f"👋 {m.mention} ברוך הבא!")
    if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 7:
        await m.guild.get_channel(CHANNELS["ANTI_ALT"]).send(f"🚨 אלט חשוד: {m.mention}", view=AntiAltView(m))

@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    await log_ch.send(f"🛠️ `{i.user.name}` הפעיל `/{cmd.name}` ב-{datetime.now().strftime('%H:%M')}")

bot.run(TOKEN)
