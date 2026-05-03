import discord
from discord import app_commands, Webhook
from discord.ext import commands
import asyncio
import os
import json
import httpx
import aiohttp
import http.server
import socketserver
import threading

# --- הגדרות ---
LOG_CHANNEL_ID = 1499510962296721568
WEBHOOK_URL = "https://discord.com/api/webhooks/1499107473347313846/VN0GUsgF-yvXR5KoUszjJuIZbBqqYFs6hIVhGe-ZF7ppMqGDLW4WY-zZbYPk23ls2nl4"
DB_FILE = "credits_db.json"
ADMIN_ROLE_NAME = "Owner"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("credits", {}), set(data.get("lifetime", []))
            except: pass
    return {}, set()

def save_data(credits, lifetime):
    with open(DB_FILE, "w") as f:
        json.dump({"credits": credits, "lifetime": list(lifetime)}, f)

user_credits, lifetime_users = load_data()

# שרת Render
def run_on_render():
    PORT = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()
threading.Thread(target=run_on_render, daemon=True).start()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

async def broadcast_log(embed):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel: await channel.send(embed=embed)
    async with aiohttp.ClientSession() as session:
        try:
            webhook = Webhook.from_url(WEBHOOK_URL, session=session)
            await webhook.send(embed=embed)
        except: pass

# --- פקודות ניהול (Admin Only) ---

@bot.tree.command(name="credits_add", description="הוספת קרדיטים למשתמש")
@app_commands.describe(user="המשתמש", amount="כמות להוספה")
async def credits_add(i: discord.Interaction, user: discord.Member, amount: int):
    if not any(r.name == ADMIN_ROLE_NAME for r in i.user.roles):
        return await i.response.send_message("❌ אין לך הרשאה!", ephemeral=True)
    
    user_id = str(user.id)
    user_credits[user_id] = user_credits.get(user_id, 0) + amount
    save_data(user_credits, lifetime_users)
    await i.response.send_message(f"✅ נוספו {amount} קרדיטים ל-{user.mention}. (סה\"כ: {user_credits[user_id]})")

@bot.tree.command(name="credits_remove", description="הורדת קרדיטים למשתמש")
async def credits_remove(i: discord.Interaction, user: discord.Member, amount: int):
    if not any(r.name == ADMIN_ROLE_NAME for r in i.user.roles):
        return await i.response.send_message("❌ אין לך הרשאה!", ephemeral=True)
    
    user_id = str(user.id)
    user_credits[user_id] = max(0, user_credits.get(user_id, 0) - amount)
    save_data(user_credits, lifetime_users)
    await i.response.send_message(f"📉 הורדו {amount} קרדיטים ל-{user.mention}. (נשאר: {user_credits[user_id]})")

@bot.tree.command(name="set_lifetime", description="הגדרת משתמש כלייפטיים")
async def set_lifetime(i: discord.Interaction, user: discord.Member):
    if not any(r.name == ADMIN_ROLE_NAME for r in i.user.roles):
        return await i.response.send_message("❌ אין לך הרשאה!", ephemeral=True)
    
    lifetime_users.add(user.id)
    save_data(user_credits, lifetime_users)
    await i.response.send_message(f"💎 {user.mention} הוגדר כמשתמש Lifetime!")

@bot.tree.command(name="remove_lifetime", description="ביטול לייפטיים למשתמש")
async def remove_lifetime(i: discord.Interaction, user: discord.Member):
    if not any(r.name == ADMIN_ROLE_NAME for r in i.user.roles):
        return await i.response.send_message("❌ אין לך הרשאה!", ephemeral=True)
    
    if user.id in lifetime_users:
        lifetime_users.remove(user.id)
        save_data(user_credits, lifetime_users)
        await i.response.send_message(f"❌ בוטל ה-Lifetime ל-{user.mention}.")
    else:
        await i.response.send_message("המשתמש אינו Lifetime.", ephemeral=True)

@bot.tree.command(name="user_info", description="בדיקת מצב משתמש")
async def user_info(i: discord.Interaction, user: discord.Member):
    credits = user_credits.get(str(user.id), 0)
    is_lt = "כן ✅" if user.id in lifetime_users else "לא ❌"
    await i.response.send_message(f"👤 **פרטי משתמש: {user.name}**\n💰 קרדיטים: {credits}\n💎 לייפטיים: {is_lt}", ephemeral=True)

# --- פונקציית ההספמה והפאנל (נשאר אותו דבר רק עם שיפורים) ---

async def send_spam(user, phone, seconds):
    # (הקוד של ה-APIs שקיבלת קודם נשאר כאן...)
    pass

class SpamModal(discord.ui.Modal, title='🚀 Spam-Me Control Panel'):
    phone = discord.ui.TextInput(label='מספר טלפון', min_length=10, max_length=10)
    credits = discord.ui.TextInput(label='קרדיטים')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        amt = int(self.credits.value)
        is_owner = any(r.name == ADMIN_ROLE_NAME for r in interaction.user.roles)
        is_lt = interaction.user.id in lifetime_users

        if not (is_lt or is_owner) and user_credits.get(user_id, 0) < amt:
            return await interaction.response.send_message("❌ אין לך מספיק קרדיטים!", ephemeral=True)

        if not (is_lt or is_owner):
            user_credits[user_id] -= amt
            save_data(user_credits, lifetime_users)

        # הודעת לוג...
        await interaction.response.send_message("התחלנו!", ephemeral=True)
        # קריאה ל-send_spam...

@bot.tree.command(name="setup")
async def setup(i: discord.Interaction):
    if not any(r.name == ADMIN_ROLE_NAME for r in i.user.roles): return
    emb = discord.Embed(title="🔥 לוח בקרה ראשי", color=0x2f3136)
    await i.response.send_message(embed=emb, view=ControlView())

bot.run(os.environ.get("DISCORD_TOKEN"))
