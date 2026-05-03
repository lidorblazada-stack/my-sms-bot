import discord
from discord.ext import commands
from discord import app_commands
import os

# הגדרות בסיסיות
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ROLE_NAME = "Owner" # שם הרול של האדמין

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.blacklist = [] # רשימת בלאק-ליסט (ID של משתמשים)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

# בדיקה אם למשתמש יש רול Owner
def is_owner():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name=OWNER_ROLE_NAME)
        if role:
            return True
        await interaction.response.send_message("❌ פקודה זו מיועדת רק לבעלי רול Owner!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# פקודת Setup עם תיקון שגיאת התגובה
@bot.tree.command(name="setup", description="פתח את פאנל הניהול")
async def setup(interaction: discord.Interaction):
    # מונע את השגיאה בתמונה על ידי שליחת תגובה ראשונית מהירה
    await interaction.response.defer(ephemeral=True) 
    
    if interaction.user.id in bot.blacklist:
        return await interaction.followup.send("חסום! אתה ברשימה השחורה.")

    embed = discord.Embed(title="🔥 פאנל הפצצה", description="לחץ על הכפתור למטה כדי להתחיל", color=discord.Color.red())
    await interaction.followup.send(embed=embed)

# פקודות אדמין (רק למי שיש רול Owner)
@bot.tree.command(name="blacklist_add", description="הוסף משתמש לבלאק ליסט")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user: discord.Member):
    if user.id not in bot.blacklist:
        bot.blacklist.append(user.id)
        await interaction.response.send_message(f"✅ {user.display_name} נוסף לבלאק ליסט.")
    else:
        await interaction.response.send_message("המשתמש כבר חסום.")

@bot.tree.command(name="blacklist_remove", description="הסר משתמש מהבלאק ליסט")
@is_owner()
async def blacklist_remove(interaction: discord.Interaction, user: discord.Member):
    if user.id in bot.blacklist:
        bot.blacklist.remove(user.id)
        await interaction.response.send_message(f"✅ {user.display_name} הוסר מהבלאק ליסט.")
    else:
        await interaction.response.send_message("המשתמש לא נמצא בבלאק ליסט.")

bot.run(TOKEN)
