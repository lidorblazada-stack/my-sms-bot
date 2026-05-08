import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID קריטיות (מעודכן לפי הבקשות שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1502014872655888554 # ערוץ דיווח על ניסיונות פריצה
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)

# --- פונקציית אבטחה: Owner Only + Reporting System ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner:
        return True
    
    # 🚨 שליחת דיווח על ניסיון פריצה לפקודת אונר
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="המשתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה:", value=f"/{interaction.command.name}", inline=False)
        embed.set_footer(text="Cyber-Shield Security System")
        await log_ch.send(embed=embed)
    
    await interaction.response.send_message("❌ אין לך הרשאות להשתמש בפקודה זו!", ephemeral=True)
    return False

# --- מערכות אינטראקציה (Modals & Views) ---

class FeedbackModal(ui.Modal, title='💎 שליחת פידבק (אנונימי/גלוי)'):
    fb_text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='להישאר אנונימי? (כן/לא)', default='לא', max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anonymous.value.strip() == "כן"
            author = "אנונימי" if is_anon else interaction.user.name
            icon = "https://cdn-icons-png.flaticon.com/512/633/633779.png" if is_anon else interaction.user.display_avatar.url
            embed = discord.Embed(title="💎 פידבק חדש", description=self.fb_text.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"מאת: {author}", icon_url=icon)
            await ch.send(embed=embed)
            await interaction.response.send_message("נשלח בהצלחה!", ephemeral=True)

class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='אימות כניסה ✅', style=discord.ButtonStyle.green, custom_id='v_master')
    async def v_callback(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת!", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה ברול.", ephemeral=True)

# --- הבוט המרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות סטאפ וניהול (Owner Only) ---

@bot.tree.command(name="setup_verify", description="Owner: הקמת פאנל אימות")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="🛡️ מערכת אימות", description="לחץ על הכפתור כדי להיכנס.", color=0x2ecc71)
        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="Owner: הקמת פאנל פידבק")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="💎 פידבק לצוות", description="לחץ כדי לשלוח פידבק (אופציה לאנונימיות).", color=0x3498db)
        view = ui.View(timeout=None)
        btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="fb_v3")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal())
        view.add_item(btn)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("בוצע.", ephemeral=True)

@bot.tree.command(name="clear", description="Owner: ניקוי הודעות")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"נמחקו {amount} הודעות.")

@bot.tree.command(name="mute", description="Owner: השתקת משתמש")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק.")

@bot.tree.command(name="unmute", description="Owner: ביטול השתקה")
async def umt(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 {member.mention} הוחזר לצ'אט.")

@bot.tree.command(name="kick", description="Owner: העפת משתמש")
async def kk(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.kick()
        await interaction.response.send_message(f"👢 {member.mention} הועף.")

@bot.tree.command(name="ban", description="Owner: חסימת משתמש")
async def bn(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        await member.ban()
        await interaction.response.send_message(f"🚫 {member.mention} נחסם.")

@bot.tree.command(name="warn", description="Owner: מתן אזהרה")
async def wr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] += 1
        await interaction.response.send_message(f"⚠️ {member.mention} הוזהר ({user_warnings[member.id]}/5).")

@bot.tree.command(name="clear_warns", description="Owner: איפוס אזהרות")
async def cwr(interaction: discord.Interaction, member: discord.Member):
    if await check_is_owner(interaction):
        user_warnings[member.id] = 0
        await interaction.response.send_message(f"✅ האזהרות של {member.mention} אופסו.")

@bot.tree.command(name="slowmode", description="Owner: מצב איטי לערוץ")
async def slow(interaction: discord.Interaction, seconds: int):
    if await check_is_owner(interaction):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"⏳ מצב איטי הופעל: {seconds} שניות.")

@bot.tree.command(name="lock", description="Owner: נעילת ערוץ")
async def lock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 הערוץ ננעל.")

@bot.tree.command(name="unlock", description="Owner: פתיחת ערוץ")
async def unlock(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("🔓 הערוץ נפתח.")

# --- פקודות קהילה ומידע ---

@bot.tree.command(name="report", description="דיווח על משתמש")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="מדווח:", value=interaction.user.mention, inline=True)
        embed.add_field(name="נדווח:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)
        await interaction.response.send_message("הדיווח נשלח.", ephemeral=True)

@bot.tree.command(name="suggest", description="המלצה לשרת")
async def sg(interaction: discord.Interaction, text: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 המלצה חדשה", description=text, color=0xf1c40f)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        await ch.send(embed=embed)
        await interaction.response.send_message("תודה על ההמלצה!", ephemeral=True)

@bot.tree.command(name="warnings", description="בדיקת אזהרות")
async def wrs(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(f"📋 ל-{m.mention} יש {user_warnings[m.id]} אזהרות.")

@bot.tree.command(name="user_info", description="מידע על משתמש")
async def u_i(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"מידע על {member.name}", color=0x9b59b6)
    embed.add_field(name="תאריך הצטרפות:", value=member.joined_at.strftime("%d/%m/%Y"))
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="server_info", description="מידע על השרת")
async def s_i(interaction: discord.Interaction):
    embed = discord.Embed(title=f"מידע על {interaction.guild.name}", color=0x9b59b6)
    embed.add_field(name="כמות חברים:", value=interaction.guild.member_count)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="צפייה בתמונת פרופיל")
async def av(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    await interaction.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="בדיקת מהירות הבוט")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 פונג! {round(bot.latency * 1000)}ms")

# --- אירועים אוטומטיים (Welcome & Protection) ---

@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        content = f"אהלן {member.mention} !"
        embed = discord.Embed(description="**ברוך הבא לשרת ספאמר הכי טוב בארץ! 🔥**", color=0x00ffff)
        embed.set_thumbnail(url=member.display_avatar.url) # תמונת המשתמש
        embed.set_image(url="https://i.imgur.com/85zXpT0.png") # תמונת קראנץ'
        embed.set_footer(text=f"חבר מספר {member.guild.member_count}")
        await ch.send(content=content, embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(w in message.content for w in BAD_WORDS):
        await message.delete()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield Master Edition Online!')

if TOKEN: bot.run(TOKEN)
