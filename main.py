import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os

# --- הגדרות ---
TOKEN = os.getenv('CYBER_SHIELD_TOKEN')
FEEDBACK_CHANNEL_ID = 1502014872655888554 

# ניהול זמני המתנה (Cooldown) - שומר מתי כל משתמש שלח פידבק לאחרונה
feedback_cooldowns = {}
user_warnings = {}

# --- הגנה: רק רול Owner יכול להשתמש בפקודות ניהול ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        has_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_role:
            return True
        await interaction.response.send_message("❌ פקודה זו שמורה ל-**Owner** בלבד!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- מערכת הפידבק (Modal) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק לשומר השרת'):
    feedback_msg = ui.TextInput(
        label='מה תרצה לרשום בפידבק?',
        placeholder='כתוב כאן...',
        style=discord.TextStyle.long,
        required=True
    )
    anonymous = ui.TextInput(
        label='לשלוח באנונימיות? (כן/לא)',
        placeholder='כן = Anonymous User | לא = השם שלך',
        min_length=2, max_length=2, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        is_anon = self.anonymous.value.strip() == "כן"
        embed = discord.Embed(
            description=f"💬 **New Feedback**\n\n{self.feedback_msg.value}",
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Today at {datetime.now().strftime('%I:%M %p')}")

        if is_anon:
            embed.set_author(name="Anonymous User", icon_url="https://i.imgur.com/8fS0S9G.png")
            embed.color = 0x2b2d31
        else:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            embed.color = 0x2ecc71

        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed, view=FeedbackView())
            # עדכון זמן השליחה האחרון של המשתמש
            feedback_cooldowns[interaction.user.id] = datetime.now()
            await interaction.response.send_message("הפידבק נשלח בהצלחה! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        # בדיקת Cooldown של 5 דקות
        last_sent = feedback_cooldowns.get(interaction.user.id)
        if last_sent:
            delta = datetime.now() - last_sent
            if delta < timedelta(minutes=5):
                minutes_left = 5 - int(delta.total_seconds() // 60)
                return await interaction.response.send_message(f"⏳ אתה יכול לשלוח פידבק נוסף בעוד {minutes_left} דקות.", ephemeral=True)
        
        await interaction.response.send_modal(FeedbackModal())

# --- הגדרת הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# --- פקודות ניהול (Owner Only) ---

@bot.tree.command(name="setup_feedback", description="יצירת פאנל פידבק (Owner Only)")
@is_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(
        title="『💎』 מערכת פידבק שומר השרת",
        description="לחצו על הכפתור למטה כדי לשתף את החוויה שלכם איתנו!\nניתן לשלוח פידבק פעם ב-5 דקות.",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר בהצלחה!", ephemeral=True)

@bot.tree.command(name="warn", description="מתן אזהרה (Owner Only)")
@is_owner()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "ללא סיבה"):
    user_id = member.id
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
    count = user_warnings[user_id]
    msg = f"⚠️ {member.mention} קיבל אזהרה! ({count}/5)\nסיבה: {reason}"
    if count == 3:
        await member.timeout(timedelta(hours=1), reason="3 אזהרות")
        msg += "\n🔇 הושם במיוט לשעה."
    elif count >= 5:
        await member.kick(reason="5 אזהרות")
        msg += "\n👢 הוצא מהשרת."
        user_warnings[user_id] = 0
    await interaction.response.send_message(msg)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield Integrated is ONLINE.')

if TOKEN:
    bot.run(TOKEN)
