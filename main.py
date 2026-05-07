import discord
from discord import ui, app_commands
from discord.ext import commands
from datetime import datetime, timezone
import os

TOKEN = os.getenv('CYBER_SHIELD_TOKEN')
# הערוץ שבו הפידבקים יפורסמו (תחליף ל-ID של ערוץ הפידבק שלך)
FEEDBACK_CHANNEL_ID = 1502014872655888554 

# הגנה קשיחה: רק רול בשם "Owner" עובר
def is_strictly_owner():
    async def predicate(interaction: discord.Interaction):
        has_owner_role = any(role.name == "Owner" for role in interaction.user.roles)
        if has_owner_role:
            return True
        
        await interaction.response.send_message("❌ גישה נדחתה. רק משתמש עם רול **Owner** מורשה לבצע זאת.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class FeedbackModal(ui.Modal, title='שליחת פידבק לשומר השרת'):
    feedback_msg = ui.TextInput(
        label='מה תרצה לרשום בפידבק?',
        placeholder='כתוב כאן את דעתך...',
        style=discord.TextStyle.long,
        required=True
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
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_footer(text=f"Today at {datetime.now().strftime('%I:%M %p')}")

        if is_anon:
            embed.set_author(name="Anonymous User", icon_url="https://i.imgur.com/8fS0S9G.png")
            embed.color = 0x2b2d31 # צבע אפור כהה
        else:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            embed.color = 0x2ecc71 # צבע ירוק

        channel = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed, view=FeedbackView())
            await interaction.response.send_message("הפידבק נשלח בהצלחה! 🌟", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='שלח פידבק 🌟', style=discord.ButtonStyle.gray, custom_id='persistent:fb_btn')
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FeedbackModal())

class CyberShield(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(FeedbackView())
        await self.tree.sync()

bot = CyberShield()

# פקודת Setup - חסומה לכולם חוץ מ-Owner
@bot.tree.command(name="setup_feedback", description="יצירת פאנל פידבק (Owner Only)")
@is_strictly_owner()
async def setup_feedback(interaction: discord.Interaction):
    embed = discord.Embed(
        title="『💎』 מערכת פידבק שומר השרת",
        description="לחצו על הכפתור למטה כדי לשתף את החוויה שלכם איתנו!\nניתן לשלוח פידבק אנונימי או גלוי.",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=FeedbackView())
    await interaction.response.send_message("הפאנל נוצר, בוס. המערכת תחת השגחת שומר השרת.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'🛡️ Cyber-Shield [OWNER EDITION] is online.')

bot.run(TOKEN)
