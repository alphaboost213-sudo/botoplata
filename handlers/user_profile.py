from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import config
from database import requests as rq
from keyboards.user_kb import get_main_menu_kb

router = Router()

@router.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery):
    user = await rq.get_user(call.from_user.id)
    
    # Премиум система рангов
    if user.total_volume < 100:
        rank = "🌱 Новичок"
    elif user.total_volume < 1000:
        rank = "🌟 Продвинутый"
    elif user.total_volume < 5000:
        rank = "💼 Опытный"
    else:
        rank = "👑 VIP Клиент"

    kyc = "✅ Верифицирован" if user.kyc_status else "❌ Анонимен"
    
    text = (
        f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Профиль:</b> <code>{user.tg_id}</code>\n"
        f"🛡 <b>Статус:</b> {kyc}\n"
        f"🏆 <b>Уровень:</b> {rank}\n\n"
        f"💳 <b>Ваш баланс:</b>\n"
        f"└ <b>{rq.format_amount(user.balance, 'RUB', 'fiat')}</b>\n\n"
        f"📊 <b>Статистика обменов:</b>\n"
        f"├ Успешных сделок: <b>{user.total_exchanges}</b>\n"
        f"└ Общий объем: <b>{rq.format_amount(user.total_volume, 'USD', 'crypto')}</b>\n\n"
    )
    
    await call.message.edit_media(
        media={
            "type": "photo", 
            "media": config.BANNER_PROFILE, 
            "caption": text, 
            "parse_mode": "HTML"
        },
        reply_markup=get_main_menu_kb()
    )
    await call.answer()