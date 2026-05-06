# --- פקודת דיווח מתוקנת ---
@bot.tree.command(name="report", description="דווח על משתמש לצוות 🚨")
async def report(interaction: discord.Interaction, member: discord.Member, reason: str):
    if await fb_request("GET", f"blocked_reports/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🚨 דיווח חדש", color=0xff0000, timestamp=datetime.datetime.now())
        # הפכתי את הסדר: קודם 'מאת' ואז 'על המשתמש' כדי שזה ייראה נכון בעברית
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=True)
        embed.add_field(name="על המשתמש:", value=member.mention, inline=True)
        embed.add_field(name="סיבה:", value=f"```\n{reason}\n```", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await channel.send(embed=embed)
        await interaction.response.send_message("הדיווח התקבל, הצוות יבדוק ויעדכן. ✅", ephemeral=True)

# --- פקודת המלצה מתוקנת ---
@bot.tree.command(name="suggest", description="שלח המלצה לצוות 💡")
async def suggest(interaction: discord.Interaction, suggestion: str):
    if await fb_request("GET", f"blocked_suggestions/{interaction.user.id}"):
        return await interaction.response.send_message("❌ אתה חסום מהמערכת.", ephemeral=True)
    
    channel = bot.get_channel(SUGGESTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="💡 המלצה חדשה", color=0x00ff00, timestamp=datetime.datetime.now())
        # כאן זה שדה אחד ארוך, אז זה תמיד ייראה טוב
        embed.add_field(name="מאת:", value=interaction.user.mention, inline=False)
        embed.add_field(name="ההמלצה:", value=f"```\n{suggestion}\n```", inline=False)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        
        await channel.send(embed=embed)
        await interaction.response.send_message("ההמלצה התקבלה, תודה על העזרה! ✅", ephemeral=True)
