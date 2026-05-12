import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
import asyncio
from collections import defaultdict

# --- הגדרות IDs (לפי מה ששלחת) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443  # ה-ID שלך (להגנה מבאן)
SECOND_ID = 1493293951959044147   # ה-ID השני להגנה

# רולים
OWNER_CMD_ROLE = 1502014872655888554 # רול שמורשה להריץ פקודות
ALT_ROLE_ID = 1502014872655888554
REPORT_ROLE_ID = 1501946934779449505
RECOMMEND_ROLE_ID = 1501947249658429470
FEEDBACK_ROLE_ID = 1503475379942461522
MEMBER_ROLE_ID = 1501983948111352091
MUTE_2DAYS_ROLE = 1501953906736103535
SUSPECT_ROLE_ID = 1503464176599695380

# הגדרות לוגיקה
spam_tracker = defaultdict(list)
user_warnings = defaultdict(int)

class VerifyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="אימות וכניסה ✅", style=discord.ButtonStyle.green, custom_id="final_v")
    async def v(self, i: discord.Interaction, b: ui.Button):
        role = i.guild.get_role(MEMBER_ROLE_ID)
        if role:
            await i.user.add_roles(role)
            await i.response.send_message("ברוך הבא! קיבלת רול Member.", ephemeral=True)
        else:
            await i.response.send_message("שגיאה במציאת רול הממבר.", ephemeral=True)

class NLShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = NLShield()

# פונקציית עזר לבדיקת רול אונר
async def has_owner_perms(i: discord.Interaction):
    if any(role.id == OWNER_CMD_ROLE for role in i.user.roles) or i.user.id == MY_USER_ID:
        return True
    await i.response.send_message("🚫 אין לך רול מורשה לפקודה זו!", ephemeral=True)
    return False

# --- הגנה עצמית (Anti-Ban) ---
@bot.event
async def on_member_remove(member):
    # בודק אם זה אתה או ה-ID השני
    if member.id in [MY_USER_ID, SECOND_ID]:
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == member.id:
                # 1. מבטל את הבאן ישר
                await member.guild.unban(member)
                
                # 2. יוצר קישור הזמנה חדש
                invite = await member.guild.text_channels[0].create_invite(max_uses=1, unique=True)
                
                # 3. שולח לך הודעה בפרטי
                try:
                    user = await bot.fetch_user(member.id)
                    await user.send(f"⚠️ אחי, ניסו לתת לך באן בשרת {member.guild.name}!\n"
                                   f"המבצע: {entry.user.name}\n"
                                   f"ביטלתי את הבאן. הנה קישור חזרה: {invite}")
                except: pass

# --- פקודות ניהול ---

@bot.tree.command(name="sync")
async def sync(i: discord.Interaction):
    if await has_owner_perms(i):
        await bot.tree.sync()
        await i.response.send_message("✅ פקודות סונכרנו!", ephemeral=True)

@bot.tree.command(name="setup_verify")
async def sv(i: discord.Interaction):
    if await has_owner_perms(i):
        emb = discord.Embed(title="🛡️ אימות NL", description="לחץ למטה כדי לקבל רול Member.", color=0x2ecc71)
        await i.channel.send(embed=emb, view=VerifyView())
        await i.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="mute_2d", description="מיוט ליומיים")
async def mute_2d(i: discord.Interaction, member: discord.Member):
    if await has_owner_perms(i):
        role = i.guild.get_role(MUTE_2DAYS_ROLE)
        await member.add_roles(role)
        await i.response.send_message(f"🔇 {member.mention} הושתק ליומיים.")

@bot.tree.command(name="suspect", description="שים מישהו כחשוד")
async def suspect(i: discord.Interaction, member: discord.Member):
    if await has_owner_perms(i):
        role = i.guild.get_role(SUSPECT_ROLE_ID)
        await member.add_roles(role)
        await i.response.send_message(f"🕵️ {member.mention} נוסף לרשימת החשודים.")

@bot.tree.command(name="clear")
async def clear(i: discord.Interaction, amount: int):
    if await has_owner_perms(i):
        await i.channel.purge(limit=amount)
        await i.response.send_message(f"🧹 נמחקו {amount} הודעות.", ephemeral=True)

@bot.tree.command(name="report", description="שלח דיווח (לכולם)")
async def report(i: discord.Interaction, text: str):
    role = i.guild.get_role(REPORT_ROLE_ID)
    emb = discord.Embed(title="🚨 דיווח חדש", description=text, color=0xff0000)
    emb.set_footer(text=f"מאת: {i.user.name}")
    await i.channel.send(content=role.mention if role else "", embed=emb)
    await i.response.send_message("הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="feedback", description="שלח פידבק")
async def feedback(i: discord.Interaction, text: str):
    role = i.guild.get_role(FEEDBACK_ROLE_ID)
    emb = discord.Embed(title="💬 פידבק חדש", description=text, color=0x00ff00)
    await i.channel.send(content=role.mention if role else "", embed=emb)
    await i.response.send_message("תודה על הפידבק!", ephemeral=True)

@bot.tree.command(name="recommend", description="שלח המלצה")
async def recommend(i: discord.Interaction, text: str):
    role = i.guild.get_role(RECOMMEND_ROLE_ID)
    emb = discord.Embed(title="⭐ המלצה חדשה", description=text, color=0xffff00)
    await i.channel.send(content=role.mention if role else "", embed=emb)
    await i.response.send_message("ההמלצה פורסמה!", ephemeral=True)

# --- הגנה מספאם ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(role.id == OWNER_CMD_ROLE for role in message.author.roles if hasattr(message.author, 'roles')): return
    
    now = asyncio.get_event_loop().time()
    spam_tracker[message.author.id].append(now)
    if len([t for t in spam_tracker[message.author.id] if now - t < 3]) > 5:
        await message.author.timeout(timedelta(minutes=10), reason="Spam")
        await message.channel.send(f"🔇 {message.author.mention} הושבת (ספאם).", delete_after=5)

if TOKEN: bot.run(TOKEN)
