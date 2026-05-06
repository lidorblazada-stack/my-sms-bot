@bot.tree.command(name="warn", description="מתן אזהרה למשתמש ושמירה ב-Firebase")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "לא צוינה סיבה"):
    # מושכים את נתוני האזהרות מה-Firebase
    all_warns = await fb_get("warnings") or {}
    user_id = str(member.id)
    
    # בודקים כמה אזהרות כבר יש לו
    if user_id not in all_warns:
        all_warns[user_id] = []
    
    # מוסיפים את האזהרה החדשה
    warn_data = {
        "reason": reason,
        "admin": interaction.user.name,
        "date": str(datetime.datetime.now().date())
    }
    all_warns[user_id].append(warn_data)
    
    # שומרים חזרה ב-Firebase
    await fb_put("warnings", all_warns)
    
    warn_count = len(all_warns[user_id])
    
    embed = discord.Embed(title=f"⚠️ אזהרה נרשמה במערכת", color=discord.Color.orange())
    embed.add_field(name="משתמש", value=member.mention, inline=True)
    embed.add_field(name="מספר אזהרה", value=f"**{warn_count}**", inline=True)
    embed.add_field(name="סיבה", value=reason, inline=False)
    embed.set_footer(text=f"נרשם על ידי {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)

    # אם הוא הגיע ל-3 אזהרות - הגנה אוטומטית
    if warn_count >= 3:
        await member.timeout(datetime.timedelta(hours=2), reason="צבר 3 אזהרות במערכת Cyber-Shield")
        await interaction.followup.send(f"🛡️ המשתמש {member.mention} הושתק אוטומטית לשעתיים כי הגיע ל-3 אזהרות.")
