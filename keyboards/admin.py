from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu():
    """Admin asosiy menyusi."""
    kb = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Reklama")],
        [KeyboardButton(text="🔙 Foydalanuvchi menyusi")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_broadcast_confirm():
    """Reklamani tasdiqlash uchun inline tugmalar."""
    kb = [
        [InlineKeyboardButton(text="✅ Yuborish", callback_data="confirm_broadcast"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
