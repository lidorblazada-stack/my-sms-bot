import discord
from discord import app_commands
from discord.ext import commands
import os, datetime, httpx
from dotenv import load_dotenv

load_dotenv()

# הגדרות IDs
TOKEN = os.getenv("BOT_TOKEN")
FB_URL = os.getenv("FIREBASE_URL")
LOG_ID = 1499510962296721568
REPORT_CHANNEL_ID = 1501721217818824805
SUGGESTIONS_CHANNEL_ID = 1501721653112078639

class GuardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🛡️ שומר השרת מאובטח ומוכן!")

bot = GuardBot()

async def fb_request(method, path, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{FB_URL}{path}.json"
        try:
            if method == "PUT": res = await client.put(url, json=data)
            elif method == "GET": res = await client.get(url)
            elif method == "DELETE": res = await client.delete(url)
            return res.json() if method != "DELETE" else None
        except: return None

# --- פקודות ניהול (אדמינים) ---

@bot.tree.command(name="warn", description="מתן אזהרה למשתמש")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    await interaction.response.defer()
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    warns += 1
    await fb_request("PUT", f"warnings/{member.id}", warns)
    await interaction.followup.send(f"⚠️ {member.mention} הוזהר! ({warns}/5)")
    if warns == 3: await member.timeout(datetime.timedelta(minutes=30))
    elif warns >= 5: 
        await member.kick()
        await fb_request("DELETE", f"warnings/{member.id}")

@bot.tree.command(name="block_user", description="חסימת משתמש מדיווחים או המלצות")
@app_commands.choices(system=[
    app_commands.Choice(name="דיווחים (Report)", value="reports"),
    app_commands.Choice(name="המלצות (Suggest)", value="suggestions")
])
@app_commands.checks.has_permissions(administrator=True)
async def block_user(interaction: discord.Interaction, member: discord.Member, system: str):
    await fb_request("PUT", f"blocked_{system}/{member.id}", True)
    await interaction.response.send_message(f"🚫 {member.name} נחסם משימוש במערכת ה-{system}.")

@bot.tree.command(name="unblock_user", description="ביטול חסימה ממערכת")
@app_commands.choices(system=[
    app_commands.Choice(name="דיווחים (Report)", value="reports"),
    app_commands.Choice(name="המלצות (Suggest)", value="suggestions")
])
@app_commands.checks.has_permissions(administrator=True)
async def unblock_user(interaction: discord.Interaction, member: discord.Member, system: str):
    await fb_request("DELETE", f"blocked_{system}/{member.id}")
    await interaction.response.send_message(f"✅ החסימה של {member.name} ממערכת ה-{system} בוטלה.")

# --- פקודות משתמשים ---

@bot.tree.command(name="report", description="דווח על משתמש 🚨")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    is_blocked = await fb_request("GET", f"blocked_reports/{interaction.user.id}")
    if is_blocked: return await interaction.response.send_message("❌ אתה חסום משימוש במערכת הדיווחים.", ephemeral=True)
    
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.datetime.now())
        embed.add_field(name="מאת:", value=interaction.user.mention)
        embed.add_field(name="על המשתמש:", value=member.mention)
        embed.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="suggest", description="שלח המלצה 💡")
async def suggest(interaction: discord.Interaction, suggestion: str):
    is_blocked = await fb_request("GET", f"blocked_suggestions/{interaction.user.id}")
    if is_blocked: return await interaction.response.send_message("❌ אתה חסום משימוש במערכת ההמלצות.", ephemeral=True)
    
    channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="💡 המלצה חדשה", description=suggestion, color=0x00ff00)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_footer(text=f"נשלח בשעה {datetime.datetime.now().strftime('%H:%M')}")
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ ההמלצה פורסמה.", ephemeral=True)

@bot.tree.command(name="check_warns", description="בדיקת אזהרות")
async def check_warns(interaction: discord.Interaction, member: discord.Member):
    warns = await fb_request("GET", f"warnings/{member.id}") or 0
    await interaction.response.send_message(f"🔍 למשתמש **{member.name}** יש **{warns}** אזהרות.", ephemeral=True)

bot.run(TOKEN)
