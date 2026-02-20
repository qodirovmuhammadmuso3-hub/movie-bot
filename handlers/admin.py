import asyncio
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID
import database
from keyboards.admin import get_admin_menu, get_broadcast_confirm
from keyboards.main_menu import get_main_menu

router = Router()

class BroadcastState(StatesGroup):
    waiting_for_message = State()
    confirm_broadcast = State()

@router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel_handler(message: types.Message):
    await message.answer(
        "<b>👋 Admin panelga xush kelibsiz!</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔙 Foydalanuvchi menyusi", F.from_user.id == ADMIN_ID)
async def back_to_user_menu(message: types.Message):
    await message.answer("Siz foydalanuvchi menyusiga qaytdingiz.", reply_markup=get_main_menu())

@router.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def stats_handler(message: types.Message):
    users_count, movies_count = await database.get_stats()
    text = (
        "<b>📈 Bot statistikasi:</b>\n\n"
        f"👥 Foydalanuvchilar: <code>{users_count} ta</code>\n"
        f"🎬 Kinolar: <code>{movies_count} ta</code>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📢 Reklama", F.from_user.id == ADMIN_ID)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📣 Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring (rasm, video, matn bo'lishi mumkin):")
    await state.set_state(BroadcastState.waiting_for_message)

@router.message(BroadcastState.waiting_for_message, F.from_user.id == ADMIN_ID)
async def get_broadcast_message(message: types.Message, state: FSMContext):
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    await message.reply("Ushbu xabar barcha foydalanuvchilarga yuborilsinmi?", reply_markup=get_broadcast_confirm())
    await state.set_state(BroadcastState.confirm_broadcast)

@router.callback_query(F.data == "confirm_broadcast", F.from_user.id == ADMIN_ID)
async def confirm_broadcast_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data.get('msg_id')
    chat_id = data.get('chat_id')
    
    users = await database.get_all_users()
    await callback.message.edit_text(f"🚀 Reklama yuborish boshlandi... (Jami: {len(users)})")
    
    count = 0
    for user in users:
        try:
            await bot.copy_message(
                chat_id=user['user_id'],
                from_chat_id=chat_id,
                message_id=msg_id
            )
            count += 1
            await asyncio.sleep(0.05) # Telegram limitlaridan qochish uchun
        except Exception:
            continue
    
    await callback.message.answer(f"✅ Reklama yuborish yakunlandi. {count} ta foydalanuvchiga yuborildi.")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_broadcast", F.from_user.id == ADMIN_ID)
async def cancel_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Reklama bekor qilindi.")
    await callback.answer()
