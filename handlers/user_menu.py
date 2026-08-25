from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext  # <--- Вот этот импорт отсутствовал
from config import config
from database import requests as rq
from keyboards.user_kb import get_main_menu_kb
from handlers.user_exchange import start_exchange

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    referrer_id = None
    if command.args and command.args.isdigit():
        referrer_id = int(command.args)
    
    await rq.set_user(message.from_user.id, message.from_user.username, referrer_id)
    
    text = (
        "🏛 <b>Добро пожаловать в Premium Exchange!</b>\n\n"
        "💼 Надежный сервис для обмена криптовалюты. Быстро, безопасно и полностью конфиденциально.\n\n"
        "Выберите необходимое действие в меню ниже:"
    )
    await message.answer_photo(
        photo=config.BANNER_MAIN,
        caption=text,
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "main_menu")
async def back_to_main(call: CallbackQuery):
    text = "🏛 <b>Главное меню:</b>\n\nВыберите необходимое действие:"
    await call.message.edit_media(
        media={"type": "photo", "media": config.BANNER_MAIN, "caption": text, "parse_mode": "HTML"},
        reply_markup=get_main_menu_kb()
    )
    await call.answer()

# === ЛИЧНЫЙ КАБИНЕТ ===
@router.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery):
    user = await rq.get_user(call.from_user.id)
    
    if user.total_volume < 100: rank = "🔵 Starter"
    elif user.total_volume < 1000: rank = "🟢 Pro Trader"
    elif user.total_volume < 5000: rank = "🟣 Premium"
    else: rank = "👑 VIP Клиент"

    kyc = "✅ Верифицирован" if user.is_verified else "❌ Анонимен"
    
    text = (
        f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        f"👤 <b>Аккаунт:</b> <code>{user.tg_id}</code>\n"
        f"🛡 <b>Статус:</b> <code>{kyc}</code>\n"
        f"🏆 <b>Уровень:</b> <code>{rank}</code>\n\n"
        f"💳 <b>Состояние баланса:</b>\n"
        f"└ <b>{rq.format_amount(user.balance, 'RUB', 'fiat')}</b>\n\n"
        f"📊 <b>История операций:</b>\n"
        f"├ Всего обменов: <b>{user.total_exchanges}</b>\n"
        f"└ Общий оборот: <b>{user.total_volume:,.2f} $</b>\n"
    )
    
    await call.message.edit_media(media={"type": "photo", "media": config.BANNER_PROFILE, "caption": text, "parse_mode": "HTML"}, reply_markup=get_main_menu_kb())
    await call.answer()

# === КНОПКИ ОБМЕНА (Используем логику из user_exchange) ===
@router.callback_query(F.data.in_(["buy", "sell"]))
async def start_exchange_entry(call: CallbackQuery, state: FSMContext):
    # Подменяем data для совместимости с логикой user_exchange
    # Если нажали buy -> передаем buy_crypto, если sell -> sell_crypto
    call.data = "buy_crypto" if call.data == "buy" else "sell_crypto"
    await start_exchange(call, state)

@router.callback_query(F.data == "referrals")
async def show_referrals(call: CallbackQuery):
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    
    user = await rq.get_user(call.from_user.id)
    ref_count = await rq.get_referrals_count(call.from_user.id)
    current = await rq.get_referral_percent()
    
    text = (
        f"💎 <b>ПАРТНЕРСКАЯ ПРОГРАММА</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        f"🗣 <b>Приглашайте партнеров</b> — получайте {current}% от каждого их обмена.\n\n"
        f"📊 <b>Ваш статус:</b> <code>{'👑 Elite' if ref_count > 50 else '💠 Premium' if ref_count > 20 else '🟢 Basic'}</code>\n"
        f"💵 <b>Ваш доход:</b> <code>{rq.format_amount(user.balance, 'RUB', 'fiat')}</code>\n"
        f"👤 <b>Приглашено:</b> <code>{ref_count} чел.</code>\n\n"
        f"🔗 <b>Ваша уникальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
    )
    
    await call.message.edit_caption(
        caption=text,
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "about")
async def show_about(call: CallbackQuery):
    text = (
        "ℹ️ <b>О сервисе</b>\n\n"
        "<b>Premium Exchange</b> — это современный сервис P2P обмена.\n"
        "Мы обеспечиваем максимальную скорость сделок, конфиденциальность "
        "и премиальный уровень поддержки для каждого клиента.\n\n"
        "🔒 Все сделки защищены системой гаранта."
    )
    await call.message.edit_caption(caption=text, reply_markup=get_main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "faq")
async def show_faq(call: CallbackQuery):
    text = (
        "❓ <b>Частые вопросы (FAQ)</b>\n\n"
        "<b>1. Как долго идет обмен?</b>\n"
        "— Обычно от 5 до 15 минут после получения вашей оплаты.\n\n"
        "<b>2. Зафиксирован ли курс?</b>\n"
        "— Да, курс фиксируется на 15 минут в момент создания заявки.\n\n"
        "<b>3. Нужна ли верификация?</b>\n"
        "— KYC запрашивается только в исключительных случаях."
    )
    await call.message.edit_caption(caption=text, reply_markup=get_main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "support")
async def show_support(call: CallbackQuery):
    text = (
        "👨‍💻 <b>Служба поддержки</b>\n\n"
        "Если у вас возникла проблема с заявкой или есть вопросы, "
        "пожалуйста, обратитесь к нашему оператору:\n\n"
        "✈️ <b>Telegram:</b> @YourSupportUsername"
    )
    await call.message.edit_caption(caption=text, reply_markup=get_main_menu_kb(), parse_mode="HTML")