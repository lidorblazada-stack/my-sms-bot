import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, json, random, asyncio
from datetime import datetime, timedelta

# --- 1. הגדרות IDs (המגילה של לידור) ---
CHANNELS = {
    "SUGGESTIONS": 1501947249658429470, "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522, "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554, "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591, "LEADERBOARD": 1502014872655888554
}
ROLES = {"MUTE": 1501953906736103535, "SUSPECT": 1503464176599695380, "OWNER": 1499868525844627478}
OWNER_ID = 1130542850883469443

# --- 2. מערכת פידבק עם אנונימיות ודיליי ---
feedback_cooldown = {}

class FeedbackModal(ui.Modal, title="📩 שליחת פידבק חדש"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, min_length=10)
    anon = ui.TextInput(label="להפוך לאנונימי? (כן/לא)", default="לא", max_length=2)

    async def on_submit(self, i: discord.Interaction):
        if i.user.id in feedback_cooldown and datetime.now() < feedback_cooldown[i.user.id]:
            remain = (feedback_cooldown[i.user.id] - datetime.now()).seconds // 60
            return await i.response.send_message(f"❌ תוכל לשלוח פידבק נוסף בעוד {remain} דקות.", ephemeral=True)
        
        user_display = "👤 משתמש אנונימי" if self.anon.value == "כן" else f"{i.user.name} ({i.user.id})"
        embed = discord.Embed(title="✨ פידבק חדש התקבל", description=self.msg.value, color=0x00fbff, timestamp=datetime.now())
        embed.set_author(name=user_display, icon_url=i.user.display_avatar.url if self.anon.value != "כן" else None)
        
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="שלח פידבק נוסף", style=discord.ButtonStyle.blurple, custom_id="send_more_fb"))
        
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=embed, view=view)
        feedback_cooldown[i.user.id] = datetime.now() + timedelta(minutes=5)
        await i.response.send_message("✅ הפידבק שלך נשלח בהצלחה!", ephemeral=True)

# --- 3. פאנל שודים (Heist) ---
class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="👤 שדוד משתמש", style=discord.ButtonStyle.grey, custom_id="rob_user")
    async def rob_user(self, i, b):
        await i.response.send_message("🔫 בחר משתמש לשדידה (פקודת /rob)...", ephemeral=True)

    @ui.button(label="💰 שוד בנק", style=discord.ButtonStyle.red, custom_id="rob_bank")
    async def rob_bank(self, i, b):
        chance = random.randint(1, 100)
        if chance > 40:
            loot = random.randint(1000, 5000)
            await i.response.send_message(f"🏦 **השוד הצליח!** ברחת מהבנק עם ₪{loot}!", ephemeral=True)
        else:
            await i.response.send_message("🚨 **המשטרה הגיעה!** נכשלת בשוד ונכנסת לכלא.", ephemeral=True)

# --- 4. פאנל חנות (Shop) עם אימבד יפה ---
class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="🎁 בונוס יומי", style=discord.ButtonStyle.green, custom_id="daily_bonus")
    async def daily(self, i, b):
        await i.response.send_message("💰 קיבלת ₪1,000 בונוס יומי! נתראה מחר.", ephemeral=True)

    @ui.button(label="🎭 קניית רול VIP", style=discord.ButtonStyle.blurple, custom_id="buy_vip")
    async def buy_vip(self, i, b):
        await i.response.send_message("🛒 רול VIP עולה ₪50,000. בודק יתרה...", ephemeral=True)

# --- 5. בוט מרכזי ופקודות ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(HeistView())
        self.add_view(ShopView())
        self.update_leaderboard.start()
        await self.tree.sync()

    @tasks.loop(minutes=5)
    async def update_leaderboard(self):
        ch = self.get_channel(CHANNELS["LEADERBOARD"])
        if ch:
            embed = discord.Embed(title="🏆 טבלת עשירי השרת - מתעדכן", color=0xffd700)
            embed.description = "🥇 **Nehoray** - ₪1,500,000\n🥈 **Lidor** - ₪1,200,000"
            async for m in ch.history(limit=5):
                if m.author == self.user: await m.delete()
            await ch.send(embed=embed)

bot = CyberShield()

# פקודות סטאפ
@bot.tree.command(name="setup_all")
async def setup_all(i: discord.Interaction):
    if i.user.id != OWNER_ID: return
    
    # סטאפ שופ
    shop_em = discord.Embed(title="🏪 חנות השרת - Cyber Shop", description="כאן תוכלו לקנות רולים ולקבל בונוסים", color=0x2f3136)
    await i.channel.send(embed=shop_em, view=ShopView())
    
    # סטאפ אייסט
    heist_em = discord.Embed(title="🔫 עולם הפשע - Heist Panel", description="מוכנים להסתכן בשביל הכסף?", color=0x000000)
    await i.channel.send(embed=heist_em, view=HeistView())
    
    await i.response.send_message("✅ כל הפאנלים הוקמו!", ephemeral=True)

# לוג פקודות אונר
@bot.event
async def on_app_command_completion(i: discord.Interaction, cmd: app_commands.Command):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    embed = discord.Embed(title="🛠️ לוג פקודת אונר", color=0x5865f2, timestamp=datetime.now())
    embed.add_field(name="משתמש:", value=i.user.mention)
    embed.add_field(name="פקודה:", value=f"/{cmd.name}")
    await log_ch.send(embed=embed)

bot.run("TOKEN_HERE")
