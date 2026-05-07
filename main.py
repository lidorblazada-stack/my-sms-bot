import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone
import os

# --- הגדרות ---
TOKEN = os.getenv('CYBER_SHIELD_TOKEN')
FEEDBACK_CHANNEL_ID = 1502014872655888554 # הערוץ שבו הפידבקים יפורסמו

# --- המודאל (החלונית שנפתחת) ---
class FeedbackModal(ui.Modal, title='שליחת פידבק'):
    feedback_msg = ui.TextInput(
        label='מה תרצה לרשום בפידבק?',
        placeholder='כתוב כאן את דעתך על השרת...',
        style=discord.TextStyle.long,
        required=True,
        max_length=1000
    )
    
    anonymous = ui.TextInput(
        label='לשלוח באנונימיות? (כן/לא)',
        placeholder='כן = Anonymous User | לא = השם שלך',
        min_length=2,
        max_length=2,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        is_anon = self.anonymous.value.strip() == "כן"
        
        embed = discord.Embed(
            description=f"💬 **New Feedback**\n\n{self.feedback_msg.value}",
            color=0x2f3136, # צבע כהה כמו בדיסקורד
            timestamp=datetime.now(timezone.utc)
        )

        if is_anon:
            embed.set_author(name="Anonymous User", icon_url="https://i.imgur.com/8fS0S9G.png")
        else:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            # שליחת הפידבק לערוץ
            await channel.send(embed=embed)
            await interaction.response.send_message("הפידבק שלך נשלח! תודה ❤️", ephemeral=True)

# --- הכפתור שמופיע מתחת להודעה ---
class FeedbackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # הכפתור לא יפסיק לעבוד

    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent_view:feedback')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FeedbackModal())

# --- הגדרת הבוט ---
class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # גורם לכפתור להמשיך לעבוד גם אחרי שהבוט עובר הפעלה מחדש
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield is ready with the Feedback Panel!')

# --- פקודה ליצירת הפאנל (מריצים פעם אחת בערוץ הפידבק) ---
@bot.tree.command(name="setup_feedback", description="יוצר את הודעת הפידבק עם הכפתור")
@app_commands.checks.has_permissions(administrator=True)
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💎 מערכת פידבק",
        description="לחצו על הכפתור למטה כדי לשתף את החוויה שלכם בשרת!\nניתן לשלוח פידבק אנונימי או גלוי.",
        color=0xFFD700
    )
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר בהצלחה!", ephemeral=True)

bot.run(TOKEN)
