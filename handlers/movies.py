from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database
import logging

router = Router()

class SearchStates(StatesGroup):
    waiting_for_movie = State()
    waiting_for_anime = State()

def get_movie_text(movie):
    """Kino ma'lumotlarini HTML formatida chiroyli qilib qaytaradi."""
    text = (
        f"<b>🎬 Nomi:</b> {movie['title']}\n"
        f"<b>🆔 Kodi:</b> <code>{movie['movie_code']}</code>\n"
        f"<b>📅 Yili:</b> {movie['release_year']}\n"
        f"<b>🎭 Janri:</b> {movie['genre']}\n"
        f"<b>⏱ Davomiyligi:</b> {movie['duration']}\n"
        f"<b>📥 Manba:</b> {movie['source_channel']}"
    )
    if movie.get('is_series'):
        text += f"\n<b>🔢 Qism:</b> {movie['episode_number']}-qism"
    return text

@router.message(F.text == "🔥 Yangi kinolar")
@router.message(Command("new"))
async def new_movies_handler(message: types.Message):
    movies = await database.get_latest_movies()
    if not movies:
        await message.answer("<b>Bazada hali kinolar yo'q.</b>", parse_mode="HTML")
        return
    
    text = "<b>🆕 Oxirgi qo'shilgan kinolar:</b>\n\n"
    for title, code in movies:
        text += f"🎬 {title} — <code>{code}</code>\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⭐️ Top kinolar")
@router.message(Command("top"))
async def top_movies_handler(message: types.Message):
    movies = await database.get_top_movies()
    if not movies:
        await message.answer("<b>Hali trenddagi kinolar yo'q.</b>", parse_mode="HTML")
        return
    
    text = "<b>🔥 Eng ko'p so'ralgan kinolar:</b>\n\n"
    for title, code in movies:
        text += f"🎬 {title} — <code>{code}</code>\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🔍 Kino qidirish")
async def search_prompt_handler(message: types.Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_movie)
    await message.answer(
        "<b>🔍 Marhamat, kino nomini yoki kodini yuboring:</b>\n\n"
        "<i>Masalan: o'rgimchak odam yoki 01</i>",
        parse_mode="HTML"
    )

@router.message(F.text == "🔍 Anime qidirish")
async def anime_search_prompt_handler(message: types.Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_anime)
    await message.answer(
        "<b>🔍 Marhamat, anime nomini yoki kodini yuboring:</b>\n\n"
        "<i>Masalan: Naruto yoki 1</i>",
        parse_mode="HTML"
    )

@router.message(SearchStates.waiting_for_movie, F.text & ~F.text.startswith("/"))
async def movie_search_handler(message: types.Message, state: FSMContext):
    await process_search(message, state, content_type="movie")

@router.message(SearchStates.waiting_for_anime, F.text & ~F.text.startswith("/"))
async def anime_search_handler(message: types.Message, state: FSMContext):
    await process_search(message, state, content_type="anime")

@router.message(F.text & ~F.text.startswith("/"), StateFilter(None))
async def general_search_handler(message: types.Message, state: FSMContext):
    # Har qanday holatda ham (chatda) qidirish
    await process_search(message, state, content_type=None)

async def process_search(message: types.Message, state: FSMContext, content_type: str | None = None):
    query = message.text.strip()
    logging.info(f"Qidiruv so'rovi: {query}, Bo'lim: {content_type}")
    
    if query.isdigit():
        # 1. Avval o'z bo'limidan qidiramiz
        movie = await database.get_movie_by_code(query, content_type=content_type)
        if not movie and content_type:
            # 2. Agar topilmasa va bo'lim tanlangan bo'lsa, har qandayini qidiramiz
            movie = await database.get_movie_by_code(query)
        results = [movie] if movie else []
    else:
        results = await database.search_movies(query, content_type=content_type)
        if not results and content_type:
            results = await database.search_movies(query)
    
    if not results or not results[0]:
        msg = "<b>Uzr, bu kontent hali bazamizda yo'q 😔</b>"
        if content_type == "movie": msg = "<b>Uzr, bu kino hali bazamizda yo'q 😔</b>"
        elif content_type == "anime": msg = "<b>Uzr, bu anime hali bazamizda yo'q 😔</b>"
        
        await message.answer(
            f"{msg}\n<i>Yangi kontentlar muntazam ravishda qo'shib boriladi.</i>",
            parse_mode="HTML"
        )
        return

    movie = results[0]
    # movie_code string ekanligiga ishonch hosil qilamiz
    await database.increment_request_count(str(movie["movie_code"]))
    
    text = get_movie_text(movie)
    reply_markup = await show_movie_with_episodes(movie)

    from config import TRAILER_CH_DATA
    channel_link = TRAILER_CH_DATA["link"] or "https://t.me/search"
    channel_btn = types.InlineKeyboardButton(text="📢 Asosiy kanalimiz", url=channel_link)
    
    builder = InlineKeyboardBuilder()
    if reply_markup:
        builder = InlineKeyboardBuilder.from_markup(reply_markup)
    
    builder.row(channel_btn)
    reply_markup = builder.as_markup()

    if movie.get('file_id'):
        media_id = movie['file_id']
        media_type = movie.get('media_type', 'video')
        try:
            if media_type == 'photo':
                await message.answer_photo(media_id, caption=text, parse_mode="HTML", reply_markup=reply_markup)
            elif media_type == 'document':
                try:
                    await message.answer_document(media_id, caption=text, parse_mode="HTML", reply_markup=reply_markup)
                except Exception as e:
                    if "can't use" in str(e).lower():
                        await message.answer_video(media_id, caption=text, parse_mode="HTML", reply_markup=reply_markup)
                    else: raise e
            else: # video
                try:
                    await message.answer_video(media_id, caption=text, parse_mode="HTML", reply_markup=reply_markup)
                except Exception as e:
                    if "can't use" in str(e).lower():
                        # Agar video deb o'ylangan narsa aslida rasm yoki hujjat bo'lsa
                        await message.answer_photo(media_id, caption=text, parse_mode="HTML", reply_markup=reply_markup)
                    else: raise e
        except Exception as e:
            logging.error(f"Xabar yuborishda xato: {e}")
            await message.answer(f"{text}\n\n🔗 <a href='{movie.get('post_link') or '#'}'>Kino havolasi</a>", parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message.answer(f"{text}\n\n🔗 <a href='{movie.get('post_link') or '#'}'>Kino havolasi</a>", parse_mode="HTML", reply_markup=reply_markup)

async def show_movie_with_episodes(movie):
    """Kino uchun tugmalarni tayyorlab beradi."""
    if movie.get('is_series'):
        episodes = await database.get_episodes(movie['title'])
        # Serial bo'lsa, hatto bitta qism bo'lsa ham tugmalarni chiqaramiz
        if episodes:
            builder = InlineKeyboardBuilder()
            for ep in episodes:
                btn_text = f"{ep['episode_number']}-qism"
                builder.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"vid:{ep['movie_code']}"))
            builder.adjust(3)
            return builder.as_markup()
    return None

@router.callback_query(F.data.startswith("vid:"))
async def episode_callback_handler(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    movie = await database.get_movie_by_code(code)
    
    if not movie:
        await callback.answer("Kontent topilmadi!", show_alert=True)
        return
    
    text = get_movie_text(movie)
    reply_markup = None
    
    if movie.get('is_series'):
        episodes = await database.get_episodes(movie['title'])
        if episodes:
            builder = InlineKeyboardBuilder()
            for ep in episodes:
                btn_text = f"{ep['episode_number']}-qism"
                style_text = f"✅ {btn_text}" if str(ep['movie_code']) == str(code) else btn_text
                builder.add(types.InlineKeyboardButton(text=style_text, callback_data=f"vid:{ep['movie_code']}"))
            builder.adjust(3)
            # Kanal tugmasini ham qo'shamiz
            from config import TRAILER_CH_DATA
            channel_link = TRAILER_CH_DATA["link"] or "https://t.me/search"
            builder.row(types.InlineKeyboardButton(text="📢 Asosiy kanalimiz", url=channel_link))
            
            text += f"\n\n<b>📺 Barcha qismlar:</b>"
            reply_markup = builder.as_markup()

    if movie.get('file_id'):
        media_id = movie['file_id']
        media_type = movie.get('media_type', 'video')
        try:
            if media_type == 'photo':
                await callback.message.answer_photo(media_id, caption=text, reply_markup=reply_markup, parse_mode="HTML")
            elif media_type == 'document':
                try:
                    await callback.message.answer_document(media_id, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                except Exception as e:
                    if "can't use" in str(e).lower():
                        await callback.message.answer_video(media_id, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                    else: raise e
            else: # video
                try:
                    await callback.message.answer_video(media_id, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                except Exception as e:
                    if "can't use" in str(e).lower():
                        await callback.message.answer_photo(media_id, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                    else: raise e
        except Exception as e:
            logging.error(f"Callback xato: {e}")
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        
    await callback.answer()
