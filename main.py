import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict

# --- הגדרות - הותאם למשתנה שלך ב-Railway ---
TOKEN = os.getenv('ALT_BOT_TOKEN') 
FIREBASE_URL = os.getenv('FIREBASE_URL')
LOG_CHANNEL_ID = 1499510962296721568 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"] 

# --- חיבור לפיירבייס ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

message_counts = defaultdict(list) 

# --- הגנה: רק Owner ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        is_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if is_owner_role or interaction.user.id == interaction.guild.owner_id: return True
        await interaction.response.send_message("❌ פקודה זו למנהלי העל בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()

bot = CyberShield()

# --- פקודות ניהול ---

@bot.tree.command(name="warnings", description="בדיקת אזהרות של משתמש")
async def warnings(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    w = db.reference(f'users/{m.id}/warnings').get() or 0
    embed = discord.Embed(title=f"📋 מצב אזהרות: {m.display_name}", description=f"למשתמש יש **{w}/5** אזהרות.", color=0xe74c3c)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn", description="מתן אזהרה")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוין"):
    ref = db.reference(f'users/{member.id}/warnings')
    w = (ref.get() or 0) + 1
    ref.set(w)
    if w >= 5:
        await member.kick(reason="5 אזהרות")
        ref.set(0)
        await interaction.response.send_message(f"👢 {member.mention} הועף מהשרת עקב 5 אזהרות.")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({w}/5). סיבה: {reason}")

# --- הגנות אוטומטיות (כולל אנטי-ספאם) ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    is_staff = any(role.name == "Owner" for role in message.author.roles)
    
    if not is_staff:
        # אנטי-ספאם
        now = datetime.now()
        message_counts[message.author.id].append(now)
        message_counts[message.author.id] = [t for t in message_counts[message.author.id] if (now - t).total_seconds() < 3]
        if len(message_counts[message.author.id]) > 5:
            await message.author.timeout(timedelta(minutes=10))
            await message.channel.send(f"🔇 {message.author.mention} הושתקת ל-10 דקות עקב ספאם.")
            return

        # סינון מילים וקישורים
        if any(w in message.content for w in BAD_WORDS) or re.search(r'(https?://\S+|discord\.gg/\S+)', message.content):
            await message.delete()
            return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield is Online and Protecting!')

if TOKEN: bot.run(TOKEN)
