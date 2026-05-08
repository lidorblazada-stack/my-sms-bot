import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os
from collections import defaultdict

# --- הגדרות ID (מעודכן לפי הבקשה שלך) ---
TOKEN = os.getenv('DISCORD_TOKEN') 
SECURITY_LOG_ID = 1502014872655888554 # ערוץ דיווח על ניסיונות פריצה
FEEDBACK_CH_ID = 1502028905253699735  
SUGGESTIONS_CH_ID = 1501947249658429470 
REPORTS_CH_ID = 1501946934779449505    
WELCOME_CH_ID = 1501713652217282591
VERIFY_ROLE_ID = 1501983948111352091 # רול ממבר המעודכן

BAD_WORDS = ["כוסאמק", "זונה", "מניאק", "שרמוטה", "נאצי", "בן זונה", "זין"]
user_warnings = defaultdict(int)

# --- בדיקת Owner ודיווח פריצות ---
async def check_is_owner(interaction: discord.Interaction) -> bool:
    is_owner = any(role.name == "Owner" for role in interaction.user.roles) or interaction.user.id == interaction.guild.owner_id
    if is_owner:
        return True
    
    # דיווח על ניסיון פריצה לערוץ האבטחה
    log_ch = interaction.guild.get_channel(SECURITY_LOG_ID)
    if log_ch:
        embed = discord.Embed(title="🚫 ניסיון גישה לא מורשה", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="משתמש:", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
        embed.add_field(name="הפקודה:", value=f"/{interaction.command.name}", inline=False)
        embed.set_footer(text="Cyber-Shield Security System")
        await log_ch.send(embed=embed)
    
    await interaction.response.send_message("❌ אין לך הרשאות להשתמש בפקודה זו!", ephemeral=True)
    return False

# --- מערכת פידבק אנונימית ---
class FeedbackModal(ui.Modal, title='💎 שליחת פידבק לצוות'):
    fb_text = ui.TextInput(label='הפידבק שלך', style=discord.TextStyle.long, required=True)
    anonymous = ui.TextInput(label='להישאר אנונימי? (כן/לא)', default='לא', max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(FEEDBACK_CH_ID)
        if ch:
            is_anon = self.anonymous.value.strip() == "כן"
            author = "אנונימי" if is_anon else interaction.user.name
            icon = "https://cdn-icons-png.flaticon.com/512/633/633779.png" if is_anon else interaction.user.display_avatar.url
            
            embed = discord.Embed(title="💎 פידבק חדש התקבל", description=self.fb_text.value, color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"מאת: {author}", icon_url=icon)
            await ch.send(embed=embed)
            await interaction.response.send_message("תודה! הפידבק שלך נשלח בהצלחה.", ephemeral=True)

# --- מערכת אימות (Verify) ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label='לחץ כאן לאימות כניסה ✅', style=discord.ButtonStyle.green, custom_id='v_btn_v3')
    async def v_callback(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה! ברוך הבא לקהילה.", ephemeral=True)
        else:
            await interaction.response.send_message("שגיאה: רול האימות לא נמצא. פנה למנהל.", ephemeral=True)

# --- בוט מרכזי ---
class CyberShield(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות סטאפ ---
@bot.tree.command(name="setup_verify", description="Owner: הקמת פאנל אימות")
async def s_v(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="🛡️ מערכת אימות", description="לחץ על הכפתור למטה כדי לקבל גישה לשרת.", color=0x2ecc71)
        embed.set_image(url="https://i.imgur.com/vHInoX2.png") # תמונה עיצובית
        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message("פאנל אימות הוקם.", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="Owner: הקמת פאנל פידבק")
async def s_f(interaction: discord.Interaction):
    if await check_is_owner(interaction):
        embed = discord.Embed(title="💎 פאנל פידבקים", description="דעתכם חשובה לנו! לחצו על הכפתור כדי לשלוח פידבק (ניתן לשלוח באנונימיות).", color=0x3498db)
        view = ui.View(timeout=None)
        btn = ui.Button(label="שלח פידבק 📩", style=discord.ButtonStyle.blurple, custom_id="f_btn_v2")
        btn.callback = lambda i: i.response.send_modal(FeedbackModal())
        view.add_item(btn)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("פאנל פידבק הוקם.", ephemeral=True)

# --- פקודות ניהול ---
@bot.tree.command(name="clear", description="Owner: ניקוי צ'אט")
async def cl(interaction: discord.Interaction, amount: int):
    if await check_is_owner(interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 נמחקו {amount} הודעות בהצלחה.")

@bot.tree.command(name="mute", description="Owner: השתקה")
async def mt(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if await check_is_owner(interaction):
        await member.timeout(timedelta(minutes=minutes))
        await interaction.response.send_message(f"🔇 {member.mention} הושתק ל-{minutes} דקות.")

# --- פקודות קהילה מעוצבות ---
@bot.tree.command(name="report", description="דיווח על משתמש")
async def rp(interaction: discord.Interaction, member: discord.Member, reason: str):
    ch = interaction.guild.get_channel(REPORTS_CH_ID)
    if ch:
        embed = discord.Embed(title="🚨 דיווח משתמש חדש", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="מדווח:", value=interaction.user.mention, inline=True)
        embed.add_field(name="נגד:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)
        await interaction.response.send_message("✅ הדיווח נשלח לצוות לבדיקה.", ephemeral=True)

@bot.tree.command(name="suggest", description="המלצה לשיפור השרת")
async def sg(interaction: discord.Interaction, description: str):
    ch = interaction.guild.get_channel(SUGGESTIONS_CH_ID)
    if ch:
        embed = discord.Embed(title="💡 המלצה חדשה", description=description, color=0xf1c40f, timestamp=datetime.now(timezone.utc))
        embed.set_author(name=f"מאת: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        await ch.send(embed=embed)
        await interaction.response.send_message("✅ ההמלצה שלך נשלחה! תודה.", ephemeral=True)

# --- אירוע וולקם מעוצב (כמו בתמונה) ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(WELCOME_CH_ID)
    if ch:
        # ההודעה שביקשת עם תיוג ותמונה
        content = f"אהלן {member.mention} !"
        embed = discord.Embed(description="**ברוך הבא לשרת ספאמר הכי טוב בארץ! 🔥**", color=0x00ffff)
        # לינק לתמונה של הקראנץ' מההודעה שלך
        embed.set_image(url="https://i.postimg.cc/85zXpT0Y/image.png") 
        await ch.send(content=content, embed=embed)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield ULTIMATE is ONLINE!')

if TOKEN: bot.run(TOKEN)
