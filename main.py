import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os, asyncio, random
from datetime import datetime, timedelta

# --- 1. הגדרות קבועות ו-IDs ---
TOKEN = os.getenv('DISCORD_TOKEN')
MY_USER_ID = 1130542850883469443
JAIL_STAFF_ROLE_ID = 1501959601405427902

CHANNELS = {
    "SUGGESTIONS": 1501947249658429470, "REPORTS": 1501946934779449505,
    "FEEDBACK": 1503475379942461522, "OWNER_LOGS": 1503496964732354620,
    "WARNS_LOG": 1502014872655888554, "ANTI_ALT": 1503464176599695380,
    "WELCOME": 1501713652217282591
}
ROLES = {
    "SUPPORTER": 1503819239310627068, "VIP": 1503817695466881255,
    "TICKET_STAFF": 1501316672345211041, "MUTE": 1501953906736103535,
    "VERIFIED": 1501316672345211041
}

# דאטה-בייס פנימי
user_balances = {}
user_warns = {}
jail_list = {}        
daily_cooldown = {}   
work_cooldown = {}    
feedback_cooldown = {} 

leaderboard_config = {"channel_id": None, "message_id": None}

# פונקציית עזר לבדיקת הרשאות מנהל/צוות כלא
def is_owner_or_jail_staff(i: discord.Interaction):
    if i.user.id == MY_USER_ID:
        return True
    role = i.guild.get_role(JAIL_STAFF_ROLE_ID)
    if role in i.user.roles:
        return True
    return False

# --- 2. חלונות קופצים (Modals) ---
class SuggestionModal(ui.Modal, title="💡 הצעה חדשה לשיפור"):
    suggestion = ui.TextInput(label="מה ההצעה שלך?", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        emb = discord.Embed(title="💡 הצעה חדשה", description=self.suggestion.value, color=0xffd700, timestamp=datetime.now())
        emb.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        msg = await i.guild.get_channel(CHANNELS["SUGGESTIONS"]).send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await i.response.send_message("✅ ההצעה שלך נשלחה בהצלחה!", ephemeral=True)

class ReportModal(ui.Modal, title="🚨 דיווח על שחקן"):
    player = ui.TextInput(label="שם או ID של השחקן המדווח", placeholder="דוגמה: User#1111")
    reason = ui.TextInput(label="סיבת הדיווח ופרטים", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        emb = discord.Embed(title="🚨 דיווח חדש התקבל", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="המדווח:", value=i.user.mention, inline=True)
        emb.add_field(name="הנידון:", value=self.player.value, inline=True)
        emb.add_field(name="סיבה/פירוט:", value=self.reason.value, inline=False)
        await i.guild.get_channel(CHANNELS["REPORTS"]).send(embed=emb)
        await i.response.send_message("✅ הדיווח הועבר לטיפול הצוות.", ephemeral=True)

class FeedbackModal(ui.Modal, title="📩 שליחת פידבק לשרת"):
    content = ui.TextInput(label="רשום את הפידבק שלך", style=discord.TextStyle.paragraph)
    anon = ui.TextInput(label="האם לשלוח כאנונימי? (כן/לא)", max_length=2, default="לא")
    async def on_submit(self, i):
        now = datetime.now()
        if i.user.id in feedback_cooldown and now < feedback_cooldown[i.user.id] + timedelta(minutes=5):
            return await i.response.send_message("❌ יש להמתין 5 דקות בין פידבק לפידבק!", ephemeral=True)
        
        author = "👤 משתמש אנונימי" if self.anon.value == "כן" else i.user.mention
        emb = discord.Embed(title="✨ פידבק חדש מהקהילה", description=self.content.value, color=0x00ffff, timestamp=now)
        emb.set_footer(text=f"נשלח על ידי: {i.user.name if self.anon.value != 'כן' else 'אנונימי'}")
        await i.guild.get_channel(CHANNELS["FEEDBACK"]).send(embed=emb)
        feedback_cooldown[i.user.id] = now
        await i.response.send_message("✅ הפידבק נשלח בהצלחה, תודה לך!", ephemeral=True)

# --- 3. פאנלים קבועים ---
class VerifyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="✅ לחץ כאן לאימות", style=discord.ButtonStyle.success, custom_id="v_verify")
    async def verify_user(self, i, b):
        role = i.guild.get_role(ROLES["VERIFIED"])
        if role in i.user.roles: return await i.response.send_message("❌ אתה כבר מאומת בשרת!", ephemeral=True)
        await i.user.add_roles(role)
        await i.response.send_message("🎉 אומתת בהצלחה! ברוך הבא לשרת.", ephemeral=True)

class ShopView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="💰 בדיקת יתרה (Bal)", style=discord.ButtonStyle.primary, custom_id="sh_bal", row=0)
    async def check_bal(self, i, b):
        await i.response.send_message(f"💰 היתרה הנוכחית שלך עומדת על: **₪{user_balances.get(i.user.id, 0):,}**", ephemeral=True)

    @ui.button(label="🛠️ צא לעבודה (Work)", style=discord.ButtonStyle.primary, custom_id="sh_work", row=0)
    async def do_work(self, i, b):
        now = datetime.now()
        last = work_cooldown.get(i.user.id)
        if last and now < last + timedelta(minutes=10):
            diff = (last + timedelta(minutes=10)) - now
            return await i.response.send_message(f"❌ המשמרת שלך נגמרה! אתה עייף, חזור בעוד {diff.seconds // 60} דקות.", ephemeral=True)
        
        amt = random.randint(200, 600)
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + amt
        work_cooldown[i.user.id] = now
        jobs = ["מתכנת בוטים לדיסקורד 💻", "ברמן במועדון לילה 🍹", "נהג מונית במרכז העיר 🚖", "מאבטח בקניון 👮"]
        await i.response.send_message(f"🛠️ עבדת בתור **{random.choice(jobs)}** והרווחת סכום של **₪{amt}**!", ephemeral=True)

    @ui.button(label="קנה Supporter 🎗️", style=discord.ButtonStyle.secondary, custom_id="sh_supp", row=1)
    async def buy_supp(self, i, b): await self.process_purchase(i, 2000, ROLES["SUPPORTER"], "Supporter")
    
    @ui.button(label="קנה VIP 💎", style=discord.ButtonStyle.secondary, custom_id="sh_vip", row=1)
    async def buy_vip(self, i, b): await self.process_purchase(i, 5000, ROLES["VIP"], "VIP")
    
    @ui.button(label="🎁 פרס יומי (Daily)", style=discord.ButtonStyle.success, custom_id="sh_daily", row=2)
    async def claim_daily(self, i, b):
        now = datetime.now()
        last = daily_cooldown.get(i.user.id)
        if last and now < last + timedelta(days=1):
            diff = (last + timedelta(days=1)) - now
            hours, remainder = divmod(diff.seconds, 3600)
            minutes = remainder // 60
            return await i.response.send_message(f"❌ כבר אספת את הפרס היומי! חזור בעוד {hours} שעות ו-{minutes} דקות.", ephemeral=True)
        
        amt = random.randint(500, 1500)
        user_balances[i.user.id] = user_balances.get(i.user.id, 0) + amt
        daily_cooldown[i.user.id] = now
        await i.response.send_message(f"💰 אספת בהצלחה ₪{amt} לחשבון הבנק שלך!", ephemeral=True)

    async def process_purchase(self, i, price, role_id, role_name):
        bal = user_balances.get(i.user.id, 0)
        if bal < price: return await i.response.send_message(f"❌ חסר לך ₪{price - bal} בשביל לקנות את רול {role_name}!", ephemeral=True)
        role = i.guild.get_role(role_id)
        if role in i.user.roles: return await i.response.send_message("❌ כבר יש לך את הרול הזה!", ephemeral=True)
        user_balances[i.user.id] -= price
        await i.user.add_roles(role)
        await i.response.send_message(f"✅ הרכישה הצליחה! קיבלת את הרול {role_name}.", ephemeral=True)

class PoliceView(ui.View):
    def __init__(self, robber):
        super().__init__(timeout=10)
        self.robber = robber; self.called = False
    @ui.button(label="🚨 התקשר למשטרה! (10 שניות)", style=discord.ButtonStyle.danger, custom_id="p_call")
    async def call_police(self, i, b):
        self.called = True; self.stop()
        jail_list[self.robber.id] = datetime.now() + timedelta(hours=2)
        await i.response.send_message("📞 המשטרה בדרך! השודד נתפס וננעל בכלא לשעתיים.", ephemeral=True)
        try: await self.robber.send("🚨 נתפסת על חם! הקורבן קרא למשטרה והוכנסת לכלא לשעתיים.")
        except: pass

class HeistView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="👤 שדוד משתמש (Rob)", style=discord.ButtonStyle.secondary, custom_id="he_user")
    async def rob_user(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא, אי אפשר לבצע פשעים!", ephemeral=True)
        view = ui.View(); select = ui.UserSelect(placeholder="בחר את השחקן שברצונך לשדוד...")
        
        async def callback(inter):
            target = select.values[0]
            if target.id == inter.user.id: return await inter.response.send_message("❌ אתה לא יכול לשדוד את עצמך, טמבל.", ephemeral=True)
            if target.id in jail_list: return await inter.response.send_message("❌ הקורבן כבר נמצא בכלא!", ephemeral=True)
            
            p_view = PoliceView(inter.user)
            await inter.response.send_message(f"🔫 השוד התחיל! שלחנו הודעה חשאית ל-{target.name}. יש לו 10 שניות להזעיק משטרה!", ephemeral=True)
            try: await target.send(f"⚠️ **ניסיון שוד!** המשתמש {inter.user.name} מנסה לשדוד אותך כרגע! לחץ מהר על הכפתור:", view=p_view)
            except: return await inter.followup.send("❌ לא ניתן לשדוד משתמש זה (הודעות פרטיות חסומות).", ephemeral=True)
            
            await asyncio.sleep(10)
            if not p_view.called:
                target_bal = user_balances.get(target.id, 0)
                if target_bal <= 0: return await inter.followup.send(f"❌ השוד נכשל! הקורבן {target.name} תפרן ואין לו שקל.", ephemeral=True)
                loot = random.randint(1000, min(3000, target_bal))
                user_balances[inter.user.id] = user_balances.get(inter.user.id, 0) + loot
                user_balances[target.id] -= loot
                await inter.followup.send(f"💰 השוד הצליח! ברחת מהזירה וגנבת מ-{target.name} סכום של ₪{loot}!", ephemeral=True)
                try: await target.send(f"💸 השוד הצליח. {inter.user.name} שדד ממך ₪{loot}.")
                except: pass
        select.callback = callback; view.add_item(select)
        await i.response.send_message("בחר קורבן:", view=view, ephemeral=True)

    @ui.button(label="🏦 שוד בנק (Bank Heist)", style=discord.ButtonStyle.danger, custom_id="he_bank")
    async def rob_bank(self, i, b):
        if i.user.id in jail_list: return await i.response.send_message("❌ אתה בכלא!", ephemeral=True)
        await i.response.defer(ephemeral=True)
        await asyncio.sleep(2)
        if random.random() > 0.5:
            loot = random.randint(3000, 7000)
            user_balances[i.user.id] = user_balances.get(i.user.id, 0) + loot
            await i.followup.send(f"✅ השוד הצליח! פוצצת את הכספת וברחת עם ₪{loot}!", ephemeral=True)
        else:
            jail_list[i.user.id] = datetime.now() + timedelta(hours=2)
            await i.followup.send("❌ השוד נכשל! האזעקה השקטה הופעלה ונשלחת לכלא לשעתיים.", ephemeral=True)

    @ui.button(label="🔓 שחרור בערבות (₪5,000)", style=discord.ButtonStyle.success, custom_id="he_bail")
    async def bail_friend(self, i, b):
        if user_balances.get(i.user.id, 0) < 5000: return await i.response.send_message("❌ אין לך ₪5,000 בשביל לשלם ערבות!", ephemeral=True)
        view = ui.View(); select = ui.UserSelect(placeholder="בחר את החבר שתרצה לשחרר מהכלא...")
        async def callback(inter):
            friend = select.values[0]
            if friend.id in jail_list:
                del jail_list[friend.id]
                user_balances[i.user.id] -= 5000
                await inter.response.send_message(f"🔓 שילמת ₪5,000 ערבות! המשתמש {friend.mention} שוחרר מהכלא ברגע זה.")
            else: await inter.response.send_message("❌ השחקן הזה לא נמצא בכלא אחי.", ephemeral=True)
        select.callback = callback; view.add_item(select)
        await i.response.send_message("בחר חבר לשחרור:", view=view, ephemeral=True)

# --- 4. קלאס הבוט המרכזי ---
class CyberMasterBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def setup_hook(self):
        self.add_view(ShopView()); self.add_view(HeistView()); self.add_view(VerifyView())
        self.jail_loop.start(); self.lb_loop.start()
        await self.tree.sync()

    @tasks.loop(seconds=30)
    async def jail_loop(self):
        now = datetime.now()
        to_release = [uid for uid, release_time in jail_list.items() if now >= release_time]
        for uid in to_release: del jail_list[uid]

    @tasks.loop(minutes=5)
    async def lb_loop(self):
        if leaderboard_config["channel_id"] and leaderboard_config["message_id"]:
            ch = self.get_channel(leaderboard_config["channel_id"])
            if ch:
                try:
                    msg = await ch.fetch_message(leaderboard_config["message_id"])
                    emb = discord.Embed(title="🏆 טבלת עשירים - Cyber Economy", color=0xffd700, timestamp=datetime.now())
                    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
                    emb.description = "\n".join([f"**#{idx+1}** <@{uid}>  get ₪{bal:,}" for idx, (uid, bal) in enumerate(sorted_users)]) if sorted_users else "אין מידע עדיין."
                    await msg.edit(embed=emb)
                except: pass

bot = CyberMasterBot()

# --- 5. פקודות הסטאפ החדשות והמאוחדות ---
@bot.tree.command(name="setup_shop", description="[אונר בלבד] מקים את פאנל החנות הכולל בדיקת יתרה, עבודה ורולים.")
async def s_shop(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    emb = discord.Embed(title="═💠 CYBER-STORE MARKET 💠═", description="נהל את הבנק שלך, צא לעבוד ורכוש הטבות ייחודיות ורולים מיוחדים!", color=0x2b2d31)
    await i.channel.send(embed=emb, view=ShopView())
    await i.response.send_message("✅ פאנל חנות משודרג הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_leaderboard", description="[אונר בלבד] מקים את טבלת העשירים המתעדכנת במיקום זה כל 5 דקות.")
async def s_leaderboard(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    emb = discord.Embed(title="🏆 טבלת עשירים - Cyber Economy", description="הטבלה בטעינה, תתעדכן אוטומטית בעוד מספר רגעים...", color=0xffd700, timestamp=datetime.now())
    msg = await i.channel.send(embed=emb)
    leaderboard_config["channel_id"] = i.channel.id
    leaderboard_config["message_id"] = msg.id
    await i.response.send_message("✅ פאנל ליידרבורד הוקם ויועבר לעדכון אוטומטי כל 5 דקות!", ephemeral=True)

@bot.tree.command(name="setup_heist", description="[אונר בלבד] מקים את פאנל השודים, עולם הפשע והערבות.")
async def s_heist(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    emb = discord.Embed(title="🔫 עולם הפשע והחוק - Heist Panel", description="בצע שודים, פוצץ את כספות הבנק או שחרר חברים מהכלא בערבות כספית!", color=0x000000)
    await i.channel.send(embed=emb, view=HeistView())
    await i.response.send_message("✅ פאנל שודים הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_tickets", description="[אונר בלבד] מקים פאנל מאוחד להגשת דיווחים והצעות לשיפור השרת.")
async def s_tickets(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    v = ui.View(timeout=None)
    b_rep = ui.Button(label="🚨 דווח על שחקן", style=discord.ButtonStyle.danger, custom_id="tk_rep")
    b_sug = ui.Button(label="💡 שלח הצעה לשיפור", style=discord.ButtonStyle.secondary, custom_id="tk_sug")
    
    b_rep.callback = lambda inter: inter.response.send_modal(ReportModal())
    b_sug.callback = lambda inter: inter.response.send_modal(SuggestionModal())
    v.add_item(b_rep); v.add_item(b_sug)
    
    await i.channel.send("📩 **מרכז פניות ודיווחים - Tickets & Suggestions**\nלחצו על הכפתור המתאים למטה כדי לפתוח טופס פנייה ישירות לצוות המנהלים.", view=v)
    await i.response.send_message("✅ פאנל דיווחים והצעות מאוחד הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_feedback", description="[אונר בלבד] מקים את פאנל שליחת הפידבקים של השרת.")
async def s_feedback(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    v = ui.View(timeout=None); b = ui.Button(label="📩 שלח פידבק", style=discord.ButtonStyle.primary, custom_id="f_open")
    b.callback = lambda inter: inter.response.send_modal(FeedbackModal()); v.add_item(b)
    await i.channel.send("📩 **פאנל פידבקים רשמי**\nלחצו על הכפתור למטה כדי להביע את דעתכם על השרת! ניתן לשלוח כאנונימי.", view=v)
    await i.response.send_message("✅ פאנל פידבקים הוקם בהצלחה!", ephemeral=True)

@bot.tree.command(name="setup_verify", description="[אונר בלבד] מקים את פאנל מערכת האימות (Verify) בכניסה לשרת.")
async def s_verify(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ פקודה זו חסומה עבורך.", ephemeral=True)
    emb = discord.Embed(title="🛡️ מערכת אימות הגנה - Verify", description="על מנת לקבל גישה לשאר ערוצי השרת ולמנוע כניסת בוטים, לחצו על הכפתור הירוק למטה.", color=0x00ff00)
    await i.channel.send(embed=emb, view=VerifyView())
    await i.response.send_message("✅ פאנל אימות הוקם בהצלחה!", ephemeral=True)

# --- 6. פקודת כלכלה ציבורית בצ'אט ---
@bot.tree.command(name="pay", description="[כללי] העבר סכום כסף מחשבונך האישי ישירות לחשבון של חבר.")
async def pay(i, to: discord.Member, amount: int):
    if amount <= 0: return await i.response.send_message("❌ נא להזין סכום תקין הגבוה מ-0 שקלים.", ephemeral=True)
    my_bal = user_balances.get(i.user.id, 0)
    if my_bal < amount: return await i.response.send_message(f"❌ העברה נכשלה! חסר לך ₪{amount - my_bal} בחשבון הנוכחי.", ephemeral=True)
    
    user_balances[i.user.id] -= amount
    user_balances[to.id] = user_balances.get(to.id, 0) + amount
    await i.response.send_message(f"💸 העברת בהצלחה סכום של **₪{amount:,}** לחשבון של {to.mention}!")

# --- 7. פקודות מודרציה וניהול ---
@bot.tree.command(name="jail_add", description="[צוות כלא / אונר] שולח משתמש לכלא באופן ידני ומיידי למשך שעתיים.")
async def jail_add(i, member: discord.Member):
    if not is_owner_or_jail_staff(i): return await i.response.send_message("❌ שגיאה: פקודה זו חסומה עבורך.", ephemeral=True)
    jail_list[member.id] = datetime.now() + timedelta(hours=2)
    await i.response.send_message(f"✅ הפקודה בוצעה בהצלחה! 🔒 המשתמש {member.mention} ננעל בתוך הכלא למשך שעתיים.")

@bot.tree.command(name="jail_remove", description="[צוות כלא / אונר] משחרר משתמש מהכלא באופן ידני ומיידי.")
async def jail_remove(i, member: discord.Member):
    if not is_owner_or_jail_staff(i): return await i.response.send_message("❌ שגיאה: פקודה זו חסומה עבורך.", ephemeral=True)
    if member.id in jail_list:
        del jail_list[member.id]
        await i.response.send_message(f"✅ הפקודה בוצעה בהצלחה! 🔓 המשתמש {member.mention} שוחרר מהכלא על ידי צוות המערכת.")
    else: await i.response.send_message("❌ הפקודה נכשלה: המשתמש אינו נמצא ברשימת האסורים בכלא.", ephemeral=True)

@bot.tree.command(name="warn", description="[אונר בלבד] נותן אזהרה רשמית למשתמש. באזהרה השלישית הוא מקבל מיוט.")
async def warn(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    count = user_warns[member.id]
    log = i.guild.get_channel(CHANNELS["WARNS_LOG"])
    
    await log.send(f"⚠️ **אזהרה רשמית** | {member.mention} הוזהר על ידי {i.user.mention}.\nסיבה: `{reason}`\nמצב אזהרות: `{count}/3`")
    if count >= 3:
        await member.add_roles(i.guild.get_role(ROLES["MUTE"]))
        await log.send(f"🚫 המשתמש {member.mention} הגיע ל-3 אזהרות והושתק (Mute) אוטומטית על ידי המערכת.")
    await i.response.send_message(f"✅ האזהרה נרשמה בהצלחה למשתמש (אזהרה מספר {count}/3).", ephemeral=True)

@bot.tree.command(name="unwarn", description="[אונר בלבד] מוריד אזהרה אחת למשתמש שחטא.")
async def unwarn(i, member: discord.Member):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    current = user_warns.get(member.id, 0)
    if current <= 0: return await i.response.send_message("❌ למשתמש זה אין אף אזהרה פעילה בשרת.", ephemeral=True)
    user_warns[member.id] -= 1
    await i.response.send_message(f"✅ הורדה אזהרה בהצלחה. מצבו הנוכחי: `{user_warns[member.id]}/3` אזהרות.", ephemeral=True)

@bot.tree.command(name="mute", description="[אונר בלבד] מקצה באופן ידני רול השתקה (Mute) למשתמש.")
async def mute(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    await member.add_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message(f"🚫 המשתמש {member.mention} הושתק בהצלחה מהצ'אטים. סיבה: `{reason}`")

@bot.tree.command(name="unmute", description="[אונר בלבד] מסיר את רול ההשתקה (Mute) ומשחרר את המשתמש לצ'אט.")
async def unmute(i, member: discord.Member):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    await member.remove_roles(i.guild.get_role(ROLES["MUTE"]))
    await i.response.send_message(f"🔊 המשתמש {member.mention} שוחרר מההשתקה ויכול לדבר.")

@bot.tree.command(name="kick", description="[אונר בלבד] מגרש ומעיף משתמש מהשרת לצמיתות.")
async def kick(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    await member.kick(reason=reason)
    await i.response.send_message(f"👞 המשתמש `{member.name}` הועף מהשרת בהצלחה. סיבה: `{reason}`")

@bot.tree.command(name="ban", description="[אונר בלבד] חוסם משתמש מהשרת באופן מוחלט (Ban) שלא יוכל לחזור.")
async def ban(i, member: discord.Member, reason: str):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    await member.ban(reason=reason)
    await i.response.send_message(f"🚫 המשתמש `{member.name}` נחסם מהשרת בהצלחה ובאופן מוחלט. סיבה: `{reason}`")

@bot.tree.command(name="clear", description="[אונר בלבד] מוחק כמות מסוימת של הודעות מהערוץ הנוכחי כדי לנקות ספאם.")
async def clear(i, amount: int):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    if amount <= 0: return await i.response.send_message("❌ נא להזין מספר הודעות הגבוה מ-0.", ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.response.send_message(f"🗑️ הערוץ נוקה בהצלחה! נמחקו `{amount}` הודעות אחרונות.", ephemeral=True)

@bot.tree.command(name="slowmode", description="[אונר בלבד] קובע דיליי ואיטיות (Slowmode) בשניות בערוץ הנוכחי.")
async def slowmode(i, seconds: int):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(f"⏱️ הוגדר מצב איטי לערוץ זה בהצלחה. דיליי: `{seconds}` שניות בין הודעה להודעה.")

@bot.tree.command(name="add_money", description="[אונר בלבד] מוסיף שקלים ומטבעות לחשבונו של משתמש כלשהו בשרת.")
async def add_money(i, member: discord.Member, amount: int):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    user_balances[member.id] = user_balances.get(member.id, 0) + amount
    await i.response.send_message(f"💰 הדפסת בהצלחה **₪{amount:,}** והפקדת אותם לחשבון של {member.mention}!", ephemeral=True)

@bot.tree.command(name="remove_money", description="[אונר בלבד] מוריד ומאפס שקלים מחשבונו של משתמש כלשהו בשרת.")
async def remove_money(i, member: discord.Member, amount: int):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    user_balances[member.id] = max(0, user_balances.get(member.id, 0) - amount)
    await i.response.send_message(f"📉 קנס רשמי: הורדת בהצלחה **₪{amount:,}** מהחשבון של {member.mention}.", ephemeral=True)

@bot.tree.command(name="user_info", description="[אונר בלבד] מציג מידע ונתונים מפורטים אודות משתמש בשרת.")
async def user_info(i, member: discord.Member):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    emb = discord.Embed(title=f"👤 מידע על: {member.name}", color=0x5865f2)
    emb.add_field(name="מזהה (ID):", value=member.id, inline=True)
    emb.add_field(name="יתרת בנק:", value=f"₪{user_balances.get(member.id, 0):,}", inline=True)
    emb.add_field(name="כמות אזהרות:", value=f"{user_warns.get(member.id, 0)}/3", inline=True)
    emb.add_field(name="האם בכלא?", value="כן" if member.id in jail_list else "לא", inline=True)
    emb.add_field(name="הצטרף לשרת:", value=member.joined_at.strftime("%d/%m/%Y"), inline=False)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="server_info", description="[אונר בלבד] מציג נתונים טכניים וסטטיסטיקות אודות שרת הדיסקורד.")
async def server_info(i):
    if i.user.id != MY_USER_ID: return await i.response.send_message("❌ שגיאה: פקודה זו מוגדרת לאונר בלבד!", ephemeral=True)
    g = i.guild
    emb = discord.Embed(title=f"📊 סטטיסטיקת השרת: {g.name}", color=0x5865f2)
    emb.add_field(name="סך הכל חברים:", value=g.member_count, inline=True)
    emb.add_field(name="כמות רולים:", value=len(g.roles), inline=True)
    emb.add_field(name="כמות ערוצים:", value=len(g.channels), inline=True)
    emb.set_thumbnail(url=g.icon.url if g.icon else None)
    await i.response.send_message(embed=emb)

# --- 8. מערכות אוטומטיות ואירועים (Events) ---
@bot.event
async def on_member_join(member):
    welcome_ch = member.guild.get_channel(CHANNELS["WELCOME"])
    if welcome_ch: await welcome_ch.send(f"👋 ברוך הבא לשרת {member.mention}! נא לבצע אימות בערוץ המתאים.")
    
    now = datetime.utcnow()
    creation_diff = now - member.created_at
    if creation_diff.days < 14:
        anti_alt_ch = member.guild.get_channel(CHANNELS["ANTI_ALT"])
        if anti_alt_ch:
            emb = discord.Embed(title="⚠️ התראת אנטי-אלט! (חשבון חשוד)", color=0xffa500, timestamp=datetime.now())
            emb.add_field(name="שם משתמש:", value=member.mention)
            emb.add_field(name="גיל החשבון:", value=f"{creation_diff.days} ימים בלבד!")
            
            v = ui.View(timeout=None)
            b_kick = ui.Button(label="👞 תעיף מהשרת", style=discord.ButtonStyle.danger)
            b_ok = ui.Button(label="✅ תשאיר אותו", style=discord.ButtonStyle.success)
            
            b_kick.callback = lambda inter: [member.kick(reason="Anti-Alt System"), inter.response.send_message("👞 המשתמש הועף.", ephemeral=True)]
            b_ok.callback = lambda inter: inter.response.send_message("✅ המשתמש אושר בשרת.", ephemeral=True)
            
            v.add_item(b_kick); v.add_item(b_ok)
            await anti_alt_ch.send(embed=emb, view=v)

@bot.event
async def on_app_command_completion(i, cmd):
    log_ch = i.guild.get_channel(CHANNELS["OWNER_LOGS"])
    if log_ch:
        emb = discord.Embed(title="🛠️ לוג פקודות מערכת אוטומטי", color=0x5865f2, timestamp=datetime.now())
        emb.add_field(name="מפעיל הפקודה:", value=i.user.mention, inline=True)
        emb.add_field(name="הפקודה שהורצה:", value=f"`/{cmd.name}`", inline=True)
        emb.add_field(name="הסבר פקודה:", value=cmd.description, inline=False)
        await log_ch.send(embed=emb)

bot.run(TOKEN)
