import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from states.fsm import ExchangeFSM
from database import requests as rq
from utils.api_parser import get_exchange_rate
from keyboards.user_kb import get_cancel_kb, get_order_confirmation_kb, get_main_menu_kb
from keyboards.admin_kb import get_order_decision_kb

router = Router()

@router.callback_query(F.data.in_(["buy_crypto", "sell_crypto"]))
async def start_exchange(call: CallbackQuery, state: FSMContext):
    operation = call.data
    await state.update_data(operation=operation)
    
    all_directions = await rq.get_all_active_directions()
    valutes_from = list(set(d.valute_from for d in all_directions))
    
    builder = InlineKeyboardBuilder()
    for v in valutes_from:
        builder.button(text=f"🔹 {v}", callback_data=f"choose_vfrom_{v}")
    builder.button(text="❌ Отмена", callback_data="cancel_exchange")
    builder.adjust(2, 1)

    text = "💱 <b>Оформление обмена</b>\n\nВыберите валюту, которую вы <b>ОТДАЁТЕ</b>:"
    await call.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(ExchangeFSM.choosing_crypto)

@router.callback_query(ExchangeFSM.choosing_crypto, F.data.startswith("choose_vfrom_"))
async def process_vfrom(call: CallbackQuery, state: FSMContext):
    v_from = call.data.split("_", 2)[2]
    await state.update_data(valute_from=v_from)
    
    all_directions = await rq.get_all_active_directions()
    possible_targets = [d for d in all_directions if d.valute_from == v_from]
    
    builder = InlineKeyboardBuilder()
    for d in possible_targets:
        builder.button(text=f"🔸 {d.valute_to}", callback_data=f"choose_dir_{d.id}")
    builder.button(text="❌ Отмена", callback_data="cancel_exchange")
    builder.adjust(2, 1)
    
    text = f"💱 Вы отдаете: <b>{v_from}</b>\n\nВыберите валюту, которую вы <b>ПОЛУЧАЕТЕ</b>:"
    await call.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(ExchangeFSM.choosing_bank)

@router.callback_query(ExchangeFSM.choosing_bank, F.data.startswith("choose_dir_"))
async def process_direction(call: CallbackQuery, state: FSMContext):
    dir_id = int(call.data.split("_")[2])
    direction = await rq.get_direction(dir_id)
    
    # Пытаемся получить актуальный курс
    actual_rate = await get_exchange_rate(direction.valute_from, direction.valute_to)
    
    # Если API вернуло None или 0, используем ручной курс из БД
    if not actual_rate or actual_rate == 0:
        rate_to_use = direction.rate
    else:
        rate_to_use = actual_rate

    # Расчет курса с учетом маржи (используем margin_percent, как в вашей админке)
    margin_multiplier = 1 - (direction.margin_percent / 100)
    final_rate = rate_to_use * margin_multiplier
    
    # Сохраняем данные в FSM (используем rate_to_use для расчетов)
    await state.update_data(
        direction_id=direction.id,
        min_amt=direction.min_amount,
        max_amt=direction.max_amount,
        rate=rate_to_use,            # Чистый курс
        margin=direction.margin_percent # Маржа из БД
    )
    
    text = (
        f"💳 <b>Укажите сумму обмена</b>\n\n"
        f"🔄 Направление: <b>{direction.valute_from} ➔ {direction.valute_to}</b>\n"
        f"📊 Курс: 1 {direction.valute_from} ≈ {final_rate:.6f} {direction.valute_to}\n\n"
        f"📉 Мин: {direction.min_amount} {direction.valute_from}\n"
        f"📈 Макс: {direction.max_amount} {direction.valute_from}\n\n"
        f"✍️ <i>Введите сумму ({direction.valute_from}), которую вы отдаете:</i>"
    )
    
    await call.message.delete()
    msg = await call.message.answer_photo(
        photo=config.BANNER_EXCHANGE,
        caption=text,
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(ExchangeFSM.entering_amount)

@router.message(ExchangeFSM.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    direction = await rq.get_direction(data['direction_id'])
    
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount < data['min_amt'] or amount > data['max_amt']:
            await message.answer(f"❌ Сумма должна быть от {data['min_amt']} до {data['max_amt']}")
            return
    except ValueError:
        return 

# Расчет с маржой
    margin_multiplier = 1 - (data['margin'] / 100)
    receive_amount = round((amount * data['rate']) * margin_multiplier, 6)
    
    # Вычисляем финальный курс для фиксации
    final_rate = round(data['rate'] * margin_multiplier, 6)
    
    # Обновляем данные в состоянии
    await state.update_data(
        amount_give=amount, 
        amount_receive=receive_amount,
        final_rate_fixed=final_rate
    )
    
    text = (
        f"📝 <b>Ввод реквизитов</b>\n\n"
        f"Вы отдаете: <b>{rq.format_amount(amount, direction.valute_from, direction.type_from)}</b>\n"
        f"Вы получаете: <b>{rq.format_amount(receive_amount, direction.valute_to, direction.type_to)}</b>\n\n"
        f"✍️ <i>Отправьте реквизиты для получения:</i>"
    )
    
    await message.bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data['last_msg_id'],
        caption=text,
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )
    await state.set_state(ExchangeFSM.entering_requisites)

@router.message(ExchangeFSM.entering_requisites)
async def process_requisites(message: Message, state: FSMContext):
    user_reqs = message.text.strip()
    await message.delete()
    
    data = await state.get_data()
    direction = await rq.get_direction(data['direction_id'])
    
    # Берем зафиксированный курс из данных состояния
    fixed_rate = data.get('final_rate_fixed', 0)
    
    order_id = int(datetime.datetime.now().timestamp() % 1000000)
    valid_until = datetime.datetime.now() + datetime.timedelta(minutes=15)
    
    text = (
        f"🧾 <b>Заявка №{order_id} сформирована</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        f"🔄 <b>Направление:</b> {direction.valute_from} ➔ {direction.valute_to}\n"
        f"📊 <b>Фиксированный Курс:</b> 1 {direction.valute_from} = {fixed_rate:.6f} {direction.valute_to}\n\n"
        f"📤 <b>Отдаете:</b> <b>{rq.format_amount(data['amount_give'], direction.valute_from, direction.type_from)}</b>\n"
        f"📥 <b>Получаете:</b> <b>{rq.format_amount(data['amount_receive'], direction.valute_to, direction.type_to)}</b>\n"
        f"💳 <b>Ваши реквизиты:</b> <code>{user_reqs}</code>\n\n"
        f"⏳ <b>Время на оплату до:</b> <i>{valid_until.strftime('%H:%M')}</i>\n\n"
        f"ℹ️ <b>Инструкция:</b>\n"
        f"Переведите сумму по реквизитам:\n"
        f"➡️ <code>{direction.admin_requisites}</code>\n\n"
        f"Нажмите <b>«✅ Оплатил»</b> после перевода."
    )
    
    await state.update_data(user_requisites=user_reqs, order_id=order_id)
    
    await message.bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data['last_msg_id'],
        caption=text,
        reply_markup=get_order_confirmation_kb(),
        parse_mode="HTML"
    )
    await state.set_state(ExchangeFSM.confirming_order)

@router.callback_query(F.data == "order_paid", ExchangeFSM.confirming_order)
async def order_paid(call: CallbackQuery, state: FSMContext):
    text = (
        "📸 <b>Подтверждение платежа</b>\n\n"
        "Отправьте скриншот чека об оплате (как фото) или скопируйте текст/ссылку на транзакцию:"
    )
    await call.message.edit_caption(caption=text, reply_markup=get_cancel_kb(), parse_mode="HTML")
    await state.set_state(ExchangeFSM.waiting_for_receipt)

@router.message(ExchangeFSM.waiting_for_receipt)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    current_state = await state.get_state()
    if current_state != ExchangeFSM.waiting_for_receipt:
        return
    
    data = await state.get_data()
    await state.clear()
    
    direction = await rq.get_direction(data['direction_id'])
    receipt_id = message.photo[-1].file_id if message.photo else message.text
    await message.delete()
    
    dir_name = f"{direction.valute_from} ➔ {direction.valute_to}"
    
    order_id = await rq.create_order(
        user_id=message.from_user.id,
        dir_id=direction.id,
        give=data['amount_give'],
        receive=data['amount_receive'],
        rate=data['rate'],
        reqs=data['user_requisites'],
        receipt=receipt_id
    )
    
    admin_text = (
        f"🔔 <b>НОВАЯ ЗАЯВКА НА ОБМЕН №{order_id}</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        f"👤 <b>КЛИЕНТ</b>\n"
        f"├ ID: <code>{message.from_user.id}</code>\n"
        f"└ Username: @{message.from_user.username or 'отсутствует'}\n\n"
        f"🔄 <b>ТРАНЗАКЦИЯ</b>\n"
        f"├ Направление: <b>{dir_name}</b>\n"
        f"├ Отдает: <code>{data['amount_give']}</code>\n"
        f"└ Получает: <code>{data['amount_receive']}</code>\n\n"
        f"💳 <b>РЕКВИЗИТЫ ПОЛЬЗОВАТЕЛЯ</b>\n"
        f"└ <code>{data['user_requisites']}</code>\n"
    )
    
    for admin_id in set(config.ADMIN_IDS):
        try:
            if message.photo:
                await bot.send_photo(admin_id, photo=receipt_id, caption=admin_text, 
                                     reply_markup=get_order_decision_kb(order_id, message.from_user.id), parse_mode="HTML")
            else:
                await bot.send_message(admin_id, text=f"{admin_text}\n\n📄 Чек/Транзакция: {receipt_id}", 
                                       reply_markup=get_order_decision_kb(order_id, message.from_user.id), parse_mode="HTML")
        except Exception:
            pass

    await bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data['last_msg_id'],
        caption=(
            f"✅ <b>ЗАЯВКА ОФОРМЛЕНА</b>\n"
            f"➖➖➖➖➖➖➖➖➖\n\n"
            f"📄 <b>Номер операции:</b> <code>#{order_id}</code>\n"
            f"⏳ <b>Текущий статус:</b> Проверка оператором\n\n"
            f"ℹ️ <i>Ожидайте обработки в течение 5-15 минут. "
            f"Результат будет направлен в этот чат.</i>\n\n"
            f"➖➖➖➖➖➖➖➖➖\n"
            f"<i>Благодарим за доверие.</i>"
        ),
        reply_markup=None,
        parse_mode="HTML"
    )
    
    await message.answer_photo(
        photo=config.BANNER_MAIN, caption="🏛 <b>Главное меню:</b>", reply_markup=get_main_menu_kb(), parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel_exchange")
async def cancel_exchange(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    
    await call.message.answer_photo(
        photo=config.BANNER_MAIN, 
        caption="🏛 <b>Главное меню:</b>", 
        reply_markup=get_main_menu_kb(), 
        parse_mode="HTML"
    )
    await call.answer("❌ Операция отменена.")