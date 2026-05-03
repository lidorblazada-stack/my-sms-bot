import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # חשוב: כאן אנחנו מגדירים את הבוט לפני הכל
        super().__init__(command_prefix="!", intents=intents)
        self.user_credits = {}
        self.blacklist = []

    async def setup_hook(self):
        # מסנכרן את פקודות ה-Slash עם השרתים
        await self.tree.sync()
        print(f"✅ הפקודות סונכרנו בהצלחה עבור {self.user}")

bot = MyBot()

# פקודת Setup המעוצבת לפי התמונה ששלחת (image_0bc6bc.png)
@bot.tree.command(name="setup", description="הצגת פאנל ההפצצה")
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Spam sms bomber | By Nehoray yosef Lidor belazada",
        description="**💣 Spam Phone**\n1 Credit = 35 seconds\n\n**💰 My Credits**\nCheck your balance",
        color=discord.Color.from_rgb(43, 45, 49)
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Spam Phone", style=discord.ButtonStyle.primary, emoji="🚀"))
    view.add_item(discord.ui.Button(label="My Credits", style=discord.ButtonStyle.secondary, emoji="💰"))
    await interaction.response.send_message(embed=embed, view=view)

# פקודת Spam (שדיסקורד לא מצא קודם)
@bot.tree.command(name="spam", description="הפצצת מספר טלפון")
@app_commands.describe(phone="המספר להפצצה")
async def spam(interaction: discord.Interaction, phone: str):
    await interaction.response.defer(ephemeral=True)
    # כאן יבוא מנוע ה-API שדיברנו עליו
    await interaction.followup.send(f"🚀 מתחיל הפצצה על {phone}...")

# פקודת אדמין (חייב רול בשם Owner)
@bot.tree.command(name="add_credits")
async def add_credits(interaction: discord.Interaction, user: discord.Member, amount: int):
    role = discord.utils.get(interaction.user.roles, name="Owner")
    if not role:
        return await interaction.response.send_message("❌ אין לך גישת אדמין!", ephemeral=True)
    
    bot.user_credits[user.id] = bot.user_credits.get(user.id, 0) + amount
    await interaction.response.send_message(f"✅ הוספת {amount} קרדיטים ל-{user.mention}")

bot.run(TOKEN)
