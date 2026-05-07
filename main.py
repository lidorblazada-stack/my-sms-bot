import discord
import os
from discord.ext import commands
import httpx

# הגדרות בסיסיות של הבוט
intents = discord.Intents.default()
intents.members = True  # חייב להיות דלוק כדי לזהות כניסה/עזיבה
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# משיכת נתונים מה-Secrets של GitHub
TOKEN = os.getenv('BOT_TOKEN')
FIREBASE_URL = os.getenv('FIREBASE_URL')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_member_join(member):
    # ערוץ הוולקם שביקשת
    channel_id = 1501713652217282591
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"ברוך הבא {member.mention} לשרת ספאמר הכי טוב בארץ! 🔥")

@bot.event
async def on_member_remove(member):
    # ערוץ העזיבה (נשאר אותו ID כפי שביקשת לא לשנות לוגיקה)
    channel_id = 1501713652217282591
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"המשתמש {member.name} עזב אותנו.. להתראות!")

# פקודת בדיקה פשוטה
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

# הרצת הבוט
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: BOT_TOKEN not found in environment variables.")
