import asyncio
import discord

# תוסיף את זה איפה שכל הפקודות שלך נמצאות בתוך main.py
@tree.command(name="ping-user", description="לתייג חבר שלא עונה כדי להציק לו חחח")
async def ping_user(interaction: discord.Interaction, target: discord.User, amount: int):
    # הגבלת כמות כדי שלא יחסמו את הבוט
    if amount > 10:
        amount = 10
    if amount < 1:
        amount = 1
        
    # הודעה זמנית שרק אתה רואה
    await interaction.response.send_message(f"מתחיל לתייג את {target.mention} כ-{amount} פעמים...", ephemeral=True)
    
    # הלולאה שעושה את העבודה
    for i in range(amount):
        await interaction.channel.send(f"נוווו ענה כברררר {target.mention} !!!")
        await asyncio.sleep(1) # מחכה שנייה אחת בין תיוג לתיוג
