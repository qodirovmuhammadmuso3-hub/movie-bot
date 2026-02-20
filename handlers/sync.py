import re
import logging
from aiogram import Router, types, Bot
import database
from config import ADMIN_ID

router = Router()

def parse_episode(text, raw_title):
    """Matndan qism raqamini va sarlavhani ajratib oladi."""
    is_series = False
    episode_number = None
    title = raw_title
    
    # Masalan: "Naruto 1-qism" yoki "1-qism" yoki "Qism 1"
    ep_match = re.search(r'(\d+)\s*[- ]?qism', text, re.IGNORECASE)
    if ep_match:
        is_series = True
        episode_number = int(ep_match.group(1))
        # Nomdan qism qismini olib tashlash (guruhlash uchun)
        # Sarlavha oxiridagi chiziqcha, nuqta va bo'sh joylarni tozalaymiz
        title = re.sub(r'\d+\s*[- ]?qism.*', '', raw_title, flags=re.IGNORECASE)
        title = title.strip().rstrip('-._ ')
    
    return is_series, episode_number, title

@router.channel_post()
async def sync_movie_handler(post: types.Message, bot: Bot):
    from config import TRAILER_CHANNEL, ANIME_CHANNEL, MOVIE_CHANNEL
    
    # Kanalni aniqlash
    chat_id = str(post.chat.id)
    chat_username = f"@{post.chat.username}" if post.chat.username else None
    
    # DEBUG LOG: Kanalni aniqlashda muammo bo'lsa, bu yordam beradi
    logging.info(f"--- YANGI POST ({post.message_id}) ---")
    logging.info(f"Chat Info: ID={chat_id}, Username={chat_username}, Title={post.chat.title}")
    
    def check_channel(conf_val, c_id, c_un):
        if not conf_val: return False
        conf_str = str(conf_val).lower()
        res = bool(c_id == conf_str or (c_un and c_un.lower() == conf_str))
        return res

    is_trailer = check_channel(TRAILER_CHANNEL, chat_id, chat_username)
    is_movie = check_channel(MOVIE_CHANNEL, chat_id, chat_username)
    is_anime = check_channel(ANIME_CHANNEL, chat_id, chat_username)

    logging.info(f"Match results: is_movie={is_movie}, is_trailer={is_trailer}, is_anime={is_anime}")

    if not (is_trailer or is_movie or is_anime):
        logging.info("Bu kanal configda topilmadi. O'tkazib yuborildi.")
        return

    msg_text = post.caption or post.text or ""
    media = post.video or post.document or (post.photo[-1] if post.photo else None)
    
    media_type = "none"
    if post.video: media_type = "video"
    elif post.photo: media_type = "photo"
    elif post.document: media_type = "document"

    # 1. Matndan kodni qidirish
    temp_text = re.sub(r'\d+\s*[- ]?qism', '', msg_text, flags=re.IGNORECASE)
    code_match = re.search(r'\b\d+\b', temp_text)
    
    code = None
    if code_match:
        code = code_match.group(0)
        content_type = "anime" if is_anime else "movie"
        logging.info(f"Matndan kod topildi: {code} ({content_type})")
        
        # O'z turiga qarab qidiramiz
        movie = await database.get_movie_by_code(code)
        
        if movie:
            # Agar bazada bo'lsa, lekin file_id bo'lmasa yoki turlari to'g'ri kelsa, yangilaymiz
            if media and (not movie.get('file_id') or movie.get('content_type') == content_type):
                update_data = {
                    "file_id": media.file_id,
                    "media_type": media_type,
                    "content_type": content_type
                }
                # Agar sarlavha Noma'lum bo'lsa, yangilaymiz
                if movie.get('title') == "Noma'lum" or not movie.get('title'):
                    lines = msg_text.split('\n')
                    raw_title = lines[0][:50] if lines[0] else None
                    if raw_title:
                        is_ser, ep_num, new_title = parse_episode(msg_text, raw_title)
                        update_data["title"] = new_title or raw_title
                        update_data["is_series"] = is_ser
                        update_data["episode_number"] = ep_num

                await database.update_movie_field(code, update_data)
                logging.info(f"Mavjud kontent yangilandi (file_id qo'shildi): {code}")
                
                # Adminga xabar yuborish
                try:
                    admin_msg = (
                        f"✅ <b>Kontent yangilandi!</b>\n\n"
                        f"🆔 Kod: <code>{code}</code>\n"
                        f"🎬 Nomi: {movie.get('title')}\n"
                        f"📺 Tur: {content_type.capitalize()}\n"
                        f"📢 Kanal: {post.chat.title}"
                    )
                    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Adminga xabar yuborishda xato: {e}")

            me = await bot.get_me()
            url = f"https://t.me/{me.username}?start={code}"
            # Yangilangan ma'lumotlarni qayta o'qiymiz
            movie = await database.get_movie_by_code(code)
            btn_text = "🤖 Botga o'tish"
            kb = [[types.InlineKeyboardButton(text=btn_text, url=url)]]
            await bot.edit_message_reply_markup(
                chat_id=post.chat.id,
                message_id=post.message_id,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
            )
            logging.info(f"Tugma yangilandi: {code}")
            return
        
        # 1.2 Trevor kanali bo'lsa faqat tugma qo'yish (bazaga qo'shmasdan)
        if is_trailer and media:
            me = await bot.get_me()
            url = f"https://t.me/{me.username}?start={code}"
            kb = [[types.InlineKeyboardButton(text="🤖 Botga o'tish", url=url)]]
            try:
                await bot.edit_message_reply_markup(
                    chat_id=post.chat.id,
                    message_id=post.message_id,
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
                )
                logging.info(f"Treylerga tugma qo'shildi: {code}")
            except Exception as e:
                logging.error(f"Treylerga tugma qo'shishda xato: {e}")
            return

        # 1.3 Agar bazada bo'lmasa va Treyler bo'lmasa, yangi sifatida qo'shish
        if not is_trailer and media:
            lines = msg_text.split('\n')
            raw_title = lines[0][:50] if lines[0] else "Noma'lum"
            
            is_series, episode_number, title = parse_episode(msg_text, raw_title)
            if not title: title = "Anime Serial" if is_anime else "Serial"
            
            try:
                await database.add_movie(
                    movie_code=code, title=title, year=0, genre="Noma'lum",
                    duration="Noma'lum", file_id=media.file_id,
                    post_link=f"https://t.me/{post.chat.username}/{post.message_id}" if post.chat.username else None,
                    source_channel=chat_username or post.chat.title,
                    content_type=content_type, media_type=media_type,
                    is_series=is_series, episode_number=episode_number
                )
                me = await bot.get_me()
                url = f"https://t.me/{me.username}?start={code}"
                kb = [[types.InlineKeyboardButton(text="🤖 Botga o'tish", url=url)]]
                await bot.edit_message_reply_markup(
                    chat_id=post.chat.id,
                    message_id=post.message_id,
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
                )
                logging.info(f"Yangi {content_type} bazaga qo'shildi: {code}")

                # Adminga xabar yuborish
                try:
                    admin_msg = (
                        f"🆕 <b>Yangi kontent qo'shildi!</b>\n\n"
                        f"🆔 Kod: <code>{code}</code>\n"
                        f"🎬 Nomi: {title}\n"
                        f"📺 Tur: {content_type.capitalize()}\n"
                        f"📢 Kanal: {post.chat.title}"
                    )
                    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Adminga xabar yuborishda xato: {e}")
            except Exception as e:
                logging.error(f"Bazaga qo'shishda xato (ehtimol dublikat kod): {e}")
            return

    # 2. Hech qanday kod topilmadi, va bu Kino yoki Anime kanali bo'lsa (Avtomatik kod berish)
    if (is_movie or is_anime) and not is_trailer and media:
        content_type = "anime" if is_anime else "movie"
        code = await database.get_next_movie_code(content_type)
        logging.info(f"Matnda kod yo'q. Avtomatik kod berildi: {code} ({content_type})")
        
        lines = msg_text.split('\n')
        raw_title = lines[0][:50] if lines[0] else f"{content_type.capitalize()} {code}"
        
        is_series, episode_number, title = parse_episode(msg_text, raw_title)
        if not title: title = "Anime Serial" if is_anime else "Kino"

        try:
            await database.add_movie(
                movie_code=code, title=title, year=0, genre="Noma'lum",
                duration="Noma'lum", file_id=media.file_id,
                post_link=f"https://t.me/{post.chat.username}/{post.message_id}" if post.chat.username else None,
                source_channel=chat_username or post.chat.title,
                content_type=content_type, media_type=media_type,
                is_series=is_series, episode_number=episode_number
            )
            me = await bot.get_me()
            kb = [[types.InlineKeyboardButton(text="🤖 Botga o'tish", url=f"https://t.me/{me.username}?start={code}")]]
            await bot.edit_message_reply_markup(
                chat_id=post.chat.id, 
                message_id=post.message_id, 
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
            )
            logging.info(f"{content_type.capitalize()} avtomatik qo'shildi: {code}")

            # Adminga xabar yuborish
            try:
                admin_msg = (
                    f"🤖 <b>Avtomatik kod berildi!</b>\n\n"
                    f"🆔 Kod: <code>{code}</code>\n"
                    f"🎬 Nomi: {title}\n"
                    f"📺 Tur: {content_type.capitalize()}\n"
                    f"📢 Kanal: {post.chat.title}"
                )
                await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Adminga xabar yuborishda xato: {e}")
        except Exception as e:
            logging.error(f"Avtomatik qo'shish yoki tugma qo'yishda xato: {e}")

    return
