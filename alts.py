import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import os

# משתמש בטוקן שונה מהבוט הראשון!
TOKEN = os.getenv('ALT_BOT_TOKEN')
LOG_CHANNEL_ID = 1499510962296721568 
MIN_AGE_DAYS = 7 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'🕵️ Alt Detector Online and Running!')

@bot.event
async def on_member_join(member):
    now = datetime.now(timezone.utc)
    diff = now - member.created_at
    
    if diff.days < MIN_AGE_DAYS:
        log_ch = bot.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            embed = discord.Embed(title="🚨 חשד למשתמש אלט!", color=0xffa500, timestamp=now)
            embed.add_field(name="משתמש", value=f"{member.mention} ({member.name})", inline=False)
            embed.add_field(name="גיל החשבון", value=f"{diff.days} ימים", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_ch.send(embed=embed)

bot.run(TOKEN)
