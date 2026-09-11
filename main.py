import os
import sqlite3
import threading
import time
from flask import Flask
import telebot
from telebot import types

# --- ENVIRONMENT VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- DATABASE (SQLite) ---
def init_db():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            grade TEXT,
            phone TEXT,
            username TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            idea_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS it_club (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# --- YORDAMCHI FUNKSIYALAR ---
def save_user(user_id, full_name, grade, phone, username):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, full_name, grade, phone, username) VALUES (?, ?, ?, ?, ?)",
        (user_id, full_name, grade, phone, username)
    )
    conn.commit()
    conn.close()

def is_user_registered(user_id):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def get_user_info(user_id):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, grade, phone, username FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res

# --- RENDER WEB SERVER ---
@app.route("/")
def home():
    return "Aqliy Maktab Bot Is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- MENYULAR ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📚 To'garakka yozilish")
    btn2 = types.KeyboardButton("💡 Maktab uchun taklif/g'oya")
    btn3 = types.KeyboardButton("❓ Savol yuborish")
    btn4 = types.KeyboardButton("🚀 IT-Klubga qo'shilish")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📊 Statistika")
    btn2 = types.KeyboardButton("📚 To'garaklar ro'yxati")
    btn3 = types.KeyboardButton("👥 Barcha o'quvchilar")
    btn4 = types.KeyboardButton("🚀 IT-Klub a'zolari")
    btn5 = types.KeyboardButton("⬅️ Asosiy menyu")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def subjects_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    subjects = [
        "📐 Matematika", "🇬🇧 Ingliz tili", 
        "🔬 Fizika", "🧪 Kimyo", 
        "💻 Dasturlash (IT)", "📖 Ona tili va Adabiyot",
        "📜 Tarix", "🇷🇺 Rus tili"
    ]
    buttons = [types.InlineKeyboardButton(text=sub, callback_data=f"sub_{sub}") for sub in subjects]
    markup.add(*buttons)
    return markup

user_data = {}

# --- USER HANDLERS ---
@bot.message_handler(commands=["start"])
def start_cmd(message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        bot.send_message(
            message.chat.id,
            f"Salom, **{message.from_user.first_name}**! 🏫\n\n'Aqliy Maktab' botiga xush kelibsiz. Kerakli bo'limni tanlang:",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "🏫 **'Aqliy Maktab' botiga xush kelibsiz!**\n\nRo'yxatdan o'tish uchun **Ism va Familiyangizni** kiriting:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    user_id = message.from_user.id
    user_data[user_id] = {'full_name': message.text.strip()}
    msg = bot.send_message(message.chat.id, "Sinfingizni kiriting (Masalan: `9-A`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_grade_step)

def process_grade_step(message):
    user_id = message.from_user.id
    user_data[user_id]['grade'] = message.text.strip()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    markup.add(btn_phone)
    
    msg = bot.send_message(
        message.chat.id,
        "Telefon raqamingizni pastdagi tugma orqali yuboring:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_phone_step)

def process_phone_step(message):
    user_id = message.from_user.id
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    full_name = user_data[user_id]['full_name']
    grade = user_data[user_id]['grade']
    username = message.from_user.username or "Mavjud emas"

    save_user(user_id, full_name, grade, phone, username)
    if user_id in user_data:
        del user_data[user_id]

    bot.send_message(
        message.chat.id,
        "✅ **Muvaffaqiyatli ro'yxatdan o'tdingiz!**",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"👤 **Yangi o'quvchi ro'yxatdan o'tdi:**\n\n📌 **Ism:** {full_name}\n🏫 **Sinf:** {grade}\n📞 **Tel:** `{phone}`\n🆔 **ID:** `{user_id}`",
            parse_mode="Markdown"
        )

# 1. To'garak
@bot.message_handler(func=lambda msg: msg.text == "📚 To'garakka yozilish")
def club_request(message):
    bot.send_message(
        message.chat.id,
        "Qaysi fan bo'yicha to'garakka qatnashmoqchisiz? Quyidagi ro'yxatdan tanlang:",
        reply_markup=subjects_inline_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def callback_subject(call):
    subject = call.data.replace("sub_", "")
    user = call.from_user

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO club_requests (user_id, subject) VALUES (?, ?)", (user.id, subject))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, text="Arizangiz qabul qilindi!")
    bot.edit_message_text(
        f"✅ **Arizangiz qabul qilindi!**\n\n`{subject}` bo'yicha etarli o'quvchilar yig'ilgach, sizga xabar beramiz.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

    if ADMIN_ID != 0:
        user_link = f"[{user.first_name}](tg://user?id={user.id})"
        bot.send_message(
            ADMIN_ID,
            f"📥 **Yangi to'garak arizasi!**\n\n📚 **Fan:** {subject}\n👤 **O'quvchi:** {user_link}\n🆔 **ID:** `{user.id}`\n\n🔍 *Ma'lumotlarini ko'rish:* `/info {user.id}`",
            parse_mode="Markdown"
        )

# 2. Taklif
@bot.message_handler(func=lambda msg: msg.text == "💡 Maktab uchun taklif/g'oya")
def idea_request(message):
    msg = bot.send_message(message.chat.id, "Maktabimizni yanada rivojlantirish bo'yicha o'z g'oyangizni yozib qoldiring:")
    bot.register_next_step_handler(msg, process_idea)

def process_idea(message):
    idea_text = message.text.strip()
    user = message.from_user

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ideas (user_id, idea_text) VALUES (?, ?)", (user.id, idea_text))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "💡 **Ajoyib taklif uchun rahmat!** G'oyangiz ko'rib chiqiladi.")

    if ADMIN_ID != 0:
        user_link = f"[{user.first_name}](tg://user?id={user.id})"
        bot.send_message(
            ADMIN_ID,
            f"💡 **Yangi taklif:**\n\n👤 **Kimdan:** {user_link}\n🆔 **ID:** `{user.id}`\n\n💬 {idea_text}",
            parse_mode="Markdown"
        )

# 3. Savol
@bot.message_handler(func=lambda msg: msg.text == "❓ Savol yuborish")
def question_request(message):
    msg = bot.send_message(message.chat.id, "O'zingizni qiziqtirgan savolni yozing:")
    bot.register_next_step_handler(msg, process_question)

def process_question(message):
    q_text = message.text.strip()
    user = message.from_user

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO questions (user_id, question_text) VALUES (?, ?)", (user.id, q_text))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "❓ **Savolingiz yuborildi.** Tezbora javob olasiz!")

    if ADMIN_ID != 0:
        user_link = f"[{user.first_name}](tg://user?id={user.id})"
        bot.send_message(
            ADMIN_ID,
            f"❓ **Yangi savol:**\n\n👤 **Kimdan:** {user_link}\n🆔 **ID:** `{user.id}`\n💬 {q_text}\n\n📩 *Javob berish:* `/reply {user.id} Javob`",
            parse_mode="Markdown"
        )

# 4. IT-Klub
@bot.message_handler(func=lambda msg: msg.text == "🚀 IT-Klubga qo'shilish")
def it_club_request(message):
    user = message.from_user
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO it_club (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        "🚀 **IT-Klub va Liderlar jamoasiga xush kelibsiz!**\n\nArizangiz qabul qilindi. Tez orada siz bilan bog'lanamiz!",
        parse_mode="Markdown"
    )
    if ADMIN_ID != 0:
        user_link = f"[{user.first_name}](tg://user?id={user.id})"
        bot.send_message(
            ADMIN_ID,
            f"🚀 **IT-Klubga yangi nomzod!**\n\n👤 **Nomzod:** {user_link}\n🆔 **ID:** `{user.id}`\n🔍 `/info {user.id}`",
            parse_mode="Markdown"
        )

# --- ADMIN PANEL BUYRUQLARI ---

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(
        message.chat.id,
        "👨‍💻 **Admin Panelga xush kelibsiz!**\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Asosiy menyu" and msg.from_user.id == ADMIN_ID)
def back_to_main(message):
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu())

# 📊 Statistika
@bot.message_handler(func=lambda msg: msg.text == "📊 Statistika" and msg.from_user.id == ADMIN_ID)
def show_stats(message):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()

    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    clubs_count = cursor.execute("SELECT COUNT(*) FROM club_requests").fetchone()[0]
    ideas_count = cursor.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
    questions_count = cursor.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    it_count = cursor.execute("SELECT COUNT(*) FROM it_club").fetchone()[0]
    conn.close()

    msg_text = (
        f"📊 **BOT STATISTIKASI**\n\n"
        f"👤 Ro'yxatdan o'tganlar: `{users_count}` ta\n"
        f"📚 To'garak arizalari: `{clubs_count}` ta\n"
        f"💡 Taklif va g'oyalar: `{ideas_count}` ta\n"
        f"❓ Savollar: `{questions_count}` ta\n"
        f"🚀 IT-Klub nomzodlari: `{it_count}` ta"
    )
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")

# 📚 To'garaklar Ro'yxati
@bot.message_handler(func=lambda msg: msg.text == "📚 To'garaklar ro'yxati" and msg.from_user.id == ADMIN_ID)
def show_clubs_summary(message):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT club_requests.subject, users.full_name, users.grade, users.user_id 
        FROM club_requests 
        LEFT JOIN users ON club_requests.user_id = users.user_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "Hozircha to'garakka arizalar yo'q.")
        return

    clubs_dict = {}
    for subject, name, grade, uid in rows:
        if subject not in clubs_dict:
            clubs_dict[subject] = []
        student_info = f"{name or 'Noma`lum'} ({grade or 'Sinf yo`q'}) - ID: `{uid}`"
        clubs_dict[subject].append(student_info)

    res_text = "📚 **TO'GARAKLAR BO'YICHA O'QUVCHILAR:**\n\n"
    for subject, students in clubs_dict.items():
        res_text += f"🔹 **{subject}** ({len(students)} kishi):\n"
        for st in students:
            res_text += f"   • {st}\n"
        res_text += "\n"

    bot.send_message(message.chat.id, res_text, parse_mode="Markdown")

# 👥 Barcha O'quvchilar Ro'yxati
@bot.message_handler(func=lambda msg: msg.text == "👥 Barcha o'quvchilar" and msg.from_user.id == ADMIN_ID)
def show_all_users(message):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, grade, user_id FROM users")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "Hali hech kim ro'yxatdan o'tmagan.")
        return

    res_text = "👥 **RO'YXATDAN O'TGAN O'QUVCHILAR:**\n\n"
    for name, grade, uid in rows:
        res_text += f"👤 **{name}** ({grade}) ➡️ ID: `{uid}`\n"

    res_text += "\n💡 *Ma'lumotlarini ko'rish uchun:* `/info ID`"
    bot.send_message(message.chat.id, res_text, parse_mode="Markdown")

# 🚀 IT-Klub A'zolari
@bot.message_handler(func=lambda msg: msg.text == "🚀 IT-Klub a'zolari" and msg.from_user.id == ADMIN_ID)
def show_it_members(message):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.full_name, users.grade, users.user_id 
        FROM it_club 
        JOIN users ON it_club.user_id = users.user_id
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "IT-Klubga hali a'zolar yo'q.")
        return

    res_text = "🚀 **IT-KLUB NOMZODLARI:**\n\n"
    for name, grade, uid in rows:
        res_text += f"👤 {name} ({grade}) - ID: `{uid}`\n"

    bot.send_message(message.chat.id, res_text, parse_mode="Markdown")

# 🔍 Foydalanuvchi ma'lumotlarini chiqarish (/info USER_ID)
@bot.message_handler(commands=["info"])
def info_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: `/info 8216291475`", parse_mode="Markdown")
            return

        target_id = int(parts[1])
        info = get_user_info(target_id)
        if info:
            name, grade, phone, username = info
            username_str = f"@{username}" if username and username != "Mavjud emas" else "Mavjud emas"
            msg = (
                f"👤 **O'QUVCHI MA'LUMOTLARI:**\n\n"
                f"📌 **Ism-Familiya:** {name}\n"
                f"🏫 **Sinf:** {grade}\n"
                f"📞 **Tel:** `{phone}`\n"
                f"🌐 **Username:** {username_str}\n"
                f"🆔 **ID:** `{target_id}`"
            )
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Ushbu ID'ga ega foydalanuvchi topilmadi.")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: `/info 8216291475`", parse_mode="Markdown")

# 📩 Javob yuborish (/reply USER_ID Javob)
@bot.message_handler(commands=["reply"])
def reply_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: `/reply 8216291475 Javobingiz`", parse_mode="Markdown")
            return

        target_id = int(parts[1])
        reply_msg = parts[2]

        bot.send_message(target_id, f"📩 **Maktab Adminidan javob:**\n\n{reply_msg}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ Javob yuborildi!")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: `/reply 8216291475 Javobingiz`", parse_mode="Markdown")

# --- MAIN RUN ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Aqliy Maktab Bot ishga tushdi...")
    while True:
        try:
            bot.polling(non_stop=True, interval=1, timeout=30)
        except Exception as e:
            time.sleep(5)
