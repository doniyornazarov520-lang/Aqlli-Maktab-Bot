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
            f"Salom, <b>{message.from_user.first_name}</b>! 🏫\n\n'297-Maktabning Aqlli' botiga xush kelibsiz. Kerakli bo'limni tanlang:",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "🏫 <b>'297-Maktabning Aqlli' botiga xush kelibsiz!</b>\n\nRo'yxatdan o'tish uchun <b>Ism va Familiyangizni</b> kiriting:",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    user_id = message.from_user.id
    user_data[user_id] = {'full_name': message.text.strip()}
    msg = bot.send_message(message.chat.id, "Sinfingizni kiriting (Masalan: <code>9-A</code>):", parse_mode="HTML")
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
        "✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"👤 <b>Yangi o'quvchi ro'yxatdan o'tdi:</b>\n\n📌 <b>Ism:</b> {full_name}\n🏫 <b>Sinf:</b> {grade}\n📞 <b>Tel:</b> <code>{phone}</code>\n🆔 <b>ID:</b> <code>{user_id}</code>",
            parse_mode="HTML"
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
        f"✅ <b>Arizangiz qabul qilindi!</b>\n\n<code>{subject}</code> bo'yicha etarli o'quvchilar yig'ilgach, sizga xabar beramiz.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )

    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"📥 <b>Yangi to'garak arizasi!</b>\n\n📚 <b>Fan:</b> {subject}\n👤 <b>O'quvchi:</b> {user.first_name}\n🆔 <b>ID:</b> <code>{user.id}</code>\n\n🔍 <i>Ma'lumotlarini ko'rish:</i> <code>/info {user.id}</code>",
            parse_mode="HTML"
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

    bot.send_message(message.chat.id, "💡 <b>Ajoyib taklif uchun rahmat!</b> G'oyangiz ko'rib chiqiladi.", parse_mode="HTML")

    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"💡 <b>Yangi taklif:</b>\n\n👤 <b>Kimdan:</b> {user.first_name}\n🆔 <b>ID:</b> <code>{user.id}</code>\n\n💬 {idea_text}",
            parse_mode="HTML"
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

    bot.send_message(message.chat.id, "❓ <b>Savolingiz yuborildi.</b> Tez orada javob olasiz!", parse_mode="HTML")

    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"❓ <b>Yangi savol:</b>\n\n👤 <b>Kimdan:</b> {user.first_name}\n🆔 <b>ID:</b> <code>{user.id}</code>\n💬 {q_text}\n\n📩 <i>Javob berish:</i> <code>/reply {user.id} Javob</code>",
            parse_mode="HTML"
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
        "🚀 <b>IT-Klub va Liderlar jamoasiga xush kelibsiz!</b>\n\nArizangiz qabul qilindi. Tez orada siz bilan bog'lanamiz!",
        parse_mode="HTML"
    )
    if ADMIN_ID != 0:
        bot.send_message(
            ADMIN_ID,
            f"🚀 <b>IT-Klubga yangi nomzod!</b>\n\n👤 <b>Nomzod:</b> {user.first_name}\n🆔 <b>ID:</b> <code>{user.id}</code>\n🔍 <code>/info {user.id}</code>",
            parse_mode="HTML"
        )

# --- ADMIN PANEL BUYRUQLARI ---

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(
        message.chat.id,
        "👨‍💻 <b>Admin Panelga xush kelibsiz!</b>\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
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
        f"📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👤 Ro'yxatdan o'tganlar: <code>{users_count}</code> ta\n"
        f"📚 To'garak arizalari: <code>{clubs_count}</code> ta\n"
        f"💡 Taklif va g'oyalar: <code>{ideas_count}</code> ta\n"
        f"❓ Savollar: <code>{questions_count}</code> ta\n"
        f"🚀 IT-Klub nomzodlari: <code>{it_count}</code> ta"
    )
    bot.send_message(message.chat.id, msg_text, parse_mode="HTML")

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
        student_info = f"{name or 'Noma`lum'} ({grade or 'Sinf yo`q'}) - ID: <code>{uid}</code>"
        clubs_dict[subject].append(student_info)

    res_text = "📚 <b>TO'GARAKLAR BO'YICHA O'QUVCHILAR:</b>\n\n"
    for subject, students in clubs_dict.items():
        res_text += f"🔹 <b>{subject}</b> ({len(students)} kishi):\n"
        for st in students:
            res_text += f"   • {st}\n"
        res_text += "\n"

    bot.send_message(message.chat.id, res_text, parse_mode="HTML")

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

    res_text = "👥 <b>RO'YXATDAN O'TGAN O'QUVCHILAR:</b>\n\n"
    for name, grade, uid in rows:
        res_text += f"👤 <b>{name}</b> ({grade}) ➡️ ID: <code>{uid}</code>\n"

    res_text += "\n💡 <i>Ma'lumotlarini ko'rish uchun:</i> <code>/info ID</code>"
    bot.send_message(message.chat.id, res_text, parse_mode="HTML")

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
        bot.send_message(message.chat.id, "IT-Klubga hali a me'yorida a'zolar yo'q.")
        return

    res_text = "🚀 <b>IT-KLUB NOMZODLARI:</b>\n\n"
    for name, grade, uid in rows:
        res_text += f"👤 {name} ({grade}) - ID: <code>{uid}</code>\n"

    bot.send_message(message.chat.id, res_text, parse_mode="HTML")

# 🔍 Foydalanuvchi ma'lumotlarini chiqarish (/info USER_ID)
@bot.message_handler(commands=["info"])
def info_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    raw_text = message.text.replace("/info", "").strip()
    
    if raw_text.startswith("@"):
        parts = raw_text.split(maxsplit=1)
        raw_text = parts[1] if len(parts) > 1 else ""

    if not raw_text.isdigit():
        bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: <code>/info 8216291475</code>", parse_mode="HTML")
        return

    target_id = int(raw_text)
    
    try:
        info = get_user_info(target_id)
        if info:
            name, grade, phone, username = info
            username_str = f"@{username}" if (username and username != "Mavjud emas") else "Mavjud emas"
            
            msg = (
                f"👤 <b>O'QUVCHI MA'LUMOTLARI:</b>\n\n"
                f"📌 <b>Ism-Familiya:</b> {name}\n"
                f"🏫 <b>Sinf:</b> {grade}\n"
                f"📞 <b>Tel:</b> <code>{phone}</code>\n"
                f"🌐 <b>Username:</b> {username_str}\n"
                f"🆔 <b>ID:</b> <code>{target_id}</code>"
            )
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, f"❌ <code>{target_id}</code> ID'ga ega foydalanuvchi bazadan topilmadi.", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: <code>{e}</code>", parse_mode="HTML")

# 📩 Javob yuborish (/reply USER_ID Javob)
@bot.message_handler(commands=["reply"])
def reply_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            bot.send_message(message.chat.id, "⚠️ Buyruqdan foydalanish: <code>/reply 8216291475 Javobingiz</code>", parse_mode="HTML")
            return

        target_id = int(parts[1])
        reply_msg = parts[2]

        bot.send_message(target_id, f"📩 <b>Maktab Adminidan javob:</b>\n\n{reply_msg}", parse_mode="HTML")
        bot.send_message(message.chat.id, "✅ Javob yuborildi!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: <code>{e}</code>", parse_mode="HTML")

# --- MAIN RUN ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Aqliy Maktab Bot ishga tushdi...")
    while True:
        try:
            bot.polling(non_stop=True, interval=1, timeout=30)
        except Exception as e:
            time.sleep(5)
