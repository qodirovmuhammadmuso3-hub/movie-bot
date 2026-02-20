from aiogram import Router, types, F
from aiogram.filters import Command
import re
from keyboards.subscription import get_subscription_kb
from keyboards.main_menu import get_main_menu
from config import REQUIRED_CHANNELS
import database

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    await database.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    # Deep link tekshirish (/start 1 kabi)
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        # Avval ixtiyoriy turdagisini qidiramiz (deep linklarda bu normal holat)
        movie = await database.get_movie_by_code(code)
        if movie:
            from handlers.movies import get_movie_text, show_movie_with_episodes
            text = get_movie_text(movie)
            reply_markup = await show_movie_with_episodes(movie)
            
            if movie.get('file_id'):
                media_type = movie.get('media_type', 'video')
                if media_type == 'photo':
                    await message.answer_photo(movie['file_id'], caption=text, parse_mode="HTML", reply_markup=reply_markup)
                elif media_type == 'document':
                    await message.answer_document(movie['file_id'], caption=text, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await message.answer_video(movie['file_id'], caption=text, parse_mode="HTML", reply_markup=reply_markup)
                return
    
    await message.answer(
        "<b>🎬 Salom! Kino qidiruv botiga xush kelibsiz!</b>\n\n"
        "Men sizga istalgan kinoni topishda va yuklab olishda yordam beraman. "
        "Boshlash uchun pastdagi menyudan foydalaning 👇",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "🆘 Yordam")
@router.message(Command("help"))
async def help_handler(message: types.Message):
    # Admin linkini configdan olish yoki foydalanuvchi ma'lumotlaridan
    # Hozircha oddiygina doimiy link yoki admin ID bilan t.me/user?id= qo'shish qiyinroq
    # Shuning uchun matn ichida yoki tugma sifatida beramiz
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✍️ Adminga murojaat", url=f"tg://user?id={database.ADMIN_ID}")]
    ])
    
    await message.answer(
        "<b>📚 Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1. <b>Kino kodi</b> orqali: Shunchaki raqamli kodni yuboring (masalan: <code>01</code>).\n"
        "2. <b>Nomi</b> orqali: Kino nomini yozing (masalan: <code>Joker</code>).\n"
        "3. <b>Anime</b> qidirish: Anime kodini (masalan: <code>1</code>) yoki nomini yuboring.\n\n"
        "<i>Agar bot ishlamasa yoki savollaringiz bo'lsa, adminga murojaat qiling!</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.message(F.text == "👨‍💻 Adminga murojaat")
async def admin_contact_handler(message: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✍️ Adminga yozish", url=f"tg://user?id={database.ADMIN_ID}")]
    ])
    await message.answer(
        "<b>👨‍💻 Admin bilan bog'lanish:</b>\n\n"
        "Savol va takliflaringiz bo'lsa, pastdagi tugma orqali adminga yozishingiz mumkin.",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.message(F.text == "📂 Bo'limlar")
@router.message(Command("channels"))
async def channels_handler(message: types.Message):
    await message.answer(
        "<b>📢 Botimiz faoliyati uchun majburiy bo'lgan kanallar:</b>",
        reply_markup=get_subscription_kb(),
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery, bot):
    user_id = callback.from_user.id
    all_subscribed = True
    for ch in REQUIRED_CHANNELS:
        try:
            # ch = {"id": "...", "link": "..."}
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                all_subscribed = False
                break
        except Exception:
            continue
    
    if all_subscribed:
        await callback.message.edit_text("✅ Obuna tasdiqlandi. Endi botdan foydalanishingiz mumkin.")
    else:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
