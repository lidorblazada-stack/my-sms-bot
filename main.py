import discord
from discord import ui, app_commands
from discord.ext import commands
import os, json, firebase_admin, random, asyncio
from firebase_admin import credentials, db
from datetime import datetime

# --- הגדרות IDs ---
OWNER_ROLE_ID = 1499868525844627478
MUTE_ROLE_ID = 1501953906736103535
LOGS_CHANNEL_ID = 1504815433004617798
VERIFY_ROLE_ID = 1501953906736103535 # הרול שניתן באימות
FEEDBACK_CHANNEL_ID = 1504815433004617798 # ערוץ שאליו יגיעו הפידבקים

SHOP_ROLES = {
    "Ticket Staff 🎫": [1501316672345211041, 25000],
    "VIP 💎": [1503817695466881255, 50000],
    "Server Supporter ⚫": [1503819239310627068, 75000]
}

jail_list = {}

# --- פונקציות עזר (Firebase ונתונים) ---
def get_data(uid):
    d = db.reference(f'users/{uid}').get()
    return (d.get('bal', 0), d.get('warns', 0)) if d else (0, 0)

def update_data(uid, b=None, w=None):
    ref = db.reference(f'users/{uid}')
    curr_b, curr_w = get_data(uid)
    ref.set({'bal': b if b is not None else curr_b, 'warns': w if w is not None else curr_w})

async def is_owner(user):
    return any(r.id == OWNER_ROLE_ID for r in user.roles) or user.id == 1130542850883469443

# --- פאנלים (Views) ---

# 1. פאנל אימות (Verify)
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="✅ אימות חשבון", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify(self, i, b):
        role = i.guild.get_role(VERIFY_ROLE_ID)
        await i.user.add_roles(role)
        await i.response.send_message("אומתת בהצלחה! ברוך הבא לשרת.", ephemeral=True)

# 2. פאנל פידבק (Feedback Modal)
class FeedbackModal(ui.Modal, title="שליחת פידבק לצוות"):
    msg = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, placeholder="רשום כאן מה שבא לך...")
    async def on_submit(self, i):
        ch = i.guild.get_channel(FEEDBACK_CHANNEL_ID)
        embed = discord.Embed(title="📢 פידבק חדש!", description=f"**מאת:** {i.user.mention}\n**הודעה:**\n{self.msg.value}", color=0x00fbff)
        await ch.send(embed=embed)
        await i.response.send_message("תודה! הפידבק שלך נשלח לצוות.", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="fb_btn")
    async def open_fb(self, i, b): await i.response.send_modal(FeedbackModal())

# 3. פאנל חנות ופשיעה (מופרדים)
class RoleShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🎫 Ticket Staff (25k)", style=discord.ButtonStyle.primary, custom_id="shop_1")
    async def b1(self, i, b):
        bal, _ = get_data(i.user.id); r_id, pr = SHOP_ROLES["Ticket Staff 🎫"]
        if bal < pr: return await i.response.send_message("אין כסף!", ephemeral=True)
        await i.user.add_roles(i.guild.get_role(r_id)); update_data(i.user.id, b=bal-pr)
        await i.response.send_message("קנית!", ephemeral=True)

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🏦 שוד בנק", style=discord.ButtonStyle.danger, custom_id="h_bank")
    async def heist(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("🔒 אתה בכלא!", ephemeral=True)
        bal, _ = get_data(i.user.id)
        if random.random() < 0.25:
            win = random.randint(2000, 6000); update_data(i.user.id, b=bal+win)
            await i.response.send_message(f"💰 הצלחת! הרווחת {win}", ephemeral=True)
        else:
            jail_list[i.user.id] = 5000; update_data(i.user.id, b=max(0, bal-1000))
            await i.response.send_message("🚨 נתפסת!", ephemeral=True)

# --- הגדרת הבוט ופקודות הקמה מופרדות ---
class GuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(FeedbackView()); self.add_view(RoleShopView()); self.add_view(HeistView())
        await self.tree.sync()

bot = GuardBot()

@bot.tree.command(name="setup_verify", description="הקמת פאנל אימות")
async def s_v(i):
    if await is_owner(i.user):
        await i.channel.send("🛡️ **אימות חשבון**\nלחץ על הכפתור כדי לקבל גישה לשרת.", view=VerifyView())
        await i.response.send_message("בוצע!", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="הקמת פאנל פידבק")
async def s_f(i):
    if await is_owner(i.user):
        await i.channel.send("📩 **הצעות ופידבקים**\nיש לכם הצעה לשיפור? נשמח לשמוע!", view=FeedbackView())
        await i.response.send_message("בוצע!", ephemeral=True)

@bot.tree.command(name="setup_shop", description="הקמת חנות רולים")
async def s_s(i):
    if await is_owner(i.user):
        await i.channel.send("🛒 **חנות רולים רשמית**", view=RoleShopView())
        await i.response.send_message("בוצע!", ephemeral=True)

@bot.tree.command(name="setup_heist", description="הקמת פאנל פשיעה")
async def s_h(i):
    if await is_owner(i.user):
        await i.channel.send("🕵️ **מרחב הפשיעה והשחרור**", view=HeistView())
        await i.response.send_message("בוצע!", ephemeral=True)

# (כל שאר 20 הפקודות - stats, add_money, rob, warn וכו' - נמצאות פה)

bot.run(TOKEN)
