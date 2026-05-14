# --- מערכת פידבק משודרגת (אנונימי / גלוי) ---

class FeedbackModal(ui.Modal, title="שליחת פידבק / הצעה"):
    inp = ui.TextInput(label="הפידבק שלך", style=discord.TextStyle.paragraph, placeholder="כתוב כאן את ההצעה או הדיווח שלך...")
    
    # הוספת בחירה בין אנונימי לגלוי
    anon_choice = ui.Select(
        placeholder="בחר סוג שליחה",
        options=[
            discord.SelectOption(label="שליחה גלויה (עם השם שלי)", value="public", emoji="👤"),
            discord.SelectOption(label="שליחה אנונימית", value="anon", emoji="👻")
        ]
    )

    async def on_submit(self, i: discord.Interaction):
        ch = i.guild.get_channel(FEEDBACK_CH_ID)
        if not ch:
            return await i.response.send_message("❌ ערוץ הפידבקים לא הוגדר כראוי.", ephemeral=True)

        # בדיקה מה המשתמש בחר (ברירת מחדל לגלוי אם לא בחר)
        is_anon = self.anon_choice.values[0] == "anon" if self.anon_choice.values else False
        
        emb = discord.Embed(
            title="💬 פידבק חדש התקבל!",
            description=self.inp.value,
            color=0x00ffff if not is_anon else discord.Color.light_grey()
        )
        
        if is_anon:
            emb.set_author(name="משתמש אנונימי 👻")
            emb.set_footer(text="הפידבק נשלח בצורה אנונימית")
        else:
            emb.set_author(name=f"נשלח על ידי: {i.user.name}", icon_url=i.user.display_avatar.url)
            emb.set_footer(text=f"ID: {i.user.id}")

        await ch.send(embed=emb)
        await i.response.send_message("✅ הפידבק שלך נשלח בהצלחה לצוות!", ephemeral=True)

class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="שלח פידבק 💬", style=discord.ButtonStyle.primary, custom_id="fb_v_v2")
    async def fb(self, i, b): 
        # כאן אנחנו יוצרים את המודאל ומוסיפים לו את תפריט הבחירה
        modal = FeedbackModal()
        # הערה: ב-Discord API החדש, עדיף להשתמש ב-Modal עם ה-Select בפנים
        await i.response.send_modal(modal)
