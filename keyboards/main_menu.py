from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """Asosiy menyu klaviaturasini qaytaradi."""
    kb = [
        [KeyboardButton(text="🔍 Kino qidirish"), KeyboardButton(text="🔍 Anime qidirish")],
        [KeyboardButton(text="🔥 Yangi kinolar"), KeyboardButton(text="⭐️ Top kinolar")],
        [KeyboardButton(text="📂 Bo'limlar"), KeyboardButton(text="🆘 Yordam")],
        [KeyboardButton(text="👨‍💻 Adminga murojaat")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_search_kb():
    """Qidiruv bo'limi uchun klaviatura."""
    kb = [
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
