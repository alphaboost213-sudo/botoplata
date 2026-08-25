import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from database import requests as rq
from database.engine import async_session
from database.models import User, Direction, Order

router = Router()

# Независимые состояния внутри файла админки
class AdminStates(StatesGroup):
    editing_ref_percent = State()
    editing_margin = State()
    editing_rate = State()
    editing_min = State()
    editing_max = State()
    editing_reqs = State()
    # Новые состояния для 4 колонок
    adding_dir_type_from = State()
    adding_dir_valute_from = State()
    adding_dir_type_to = State()
    adding_dir_valute_to = State()
    adding_dir_rate = State()
    adding_dir_min = State()
    adding_dir_reqs = State()
    
    waiting_for_search_id = State()
    waiting_for_balance_val = State()
    waiting_for_broadcast_msg = State()
    waiting_for_user_msg = State()

class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in config.ADMIN_IDS

def get_admin_main_kb():
    """Жестко встроенная клавиатура для защиты от багов импорта"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="⚙️ Направления", callback_data="admin_rates")
    builder.button(text="📋 История заявок", callback_data="admin_history")
    builder.button(text="🔍 Поиск юзера", callback_data="admin_find_user")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="💾 Выгрузка БД", callback_data="admin_export")
    builder.button(text="🎁 Реферальный процент", callback_data="admin_set_ref_percent")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_dashboard_text():
    return (
        f"👑 <b>Админ Панель</b> 👑\n"
        f"➖➖➖➖➖➖➖➖➖\n"
        f"🟢 Статус системы: <b>Stable</b>\n"
        f"🕒 Сервер: <b>{datetime.datetime.now().strftime('%H:%M')}</b>\n\n"
        f"Выберите необходимый модуль управления:"
    )

@router.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_main", IsAdmin())
async def admin_main_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_kyc_"))
async def admin_toggle_kyc(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    updated_user = await rq.toggle_user_kyc(user_id)
    
    if updated_user:
        status_text = "Верифицирован" if updated_user.is_verified else "Анонимен"
        await call.answer(f"Статус KYC изменен на: {status_text}", show_alert=False)
        await render_user_card(call, updated_user)
    else:
        await call.answer("Пользователь не найден!", show_alert=True)

# === СТАТИСТИКА И ИСТОРИЯ ===
@router.callback_query(F.data == "admin_stats", IsAdmin())
async def show_stats(call: CallbackQuery):
    stats = await rq.get_project_stats()
    text = (
        "📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей в базе: <b>{stats['users']}</b>\n"
        f"📋 Успешных заявок: <b>{stats['orders']}</b>\n"
        f"💵 Общий оборот системы: <b>{stats['volume']:,.2f} $</b>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "admin_set_ref_percent", IsAdmin())
async def set_ref_percent_start(call: CallbackQuery, state: FSMContext):
    current = await rq.get_referral_percent()
    await call.message.edit_text(f"🎁 <b>Текущий процент рефералки: {current}%</b>\nВведите новый процент:", parse_mode="HTML")
    await state.set_state(AdminStates.editing_ref_percent)

@router.message(AdminStates.editing_ref_percent, IsAdmin())
async def set_ref_percent_save(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").strip())
        await rq.set_referral_percent(val)
        await message.answer(f"✅ Процент успешно изменен на {val}%")
    except ValueError:
        await message.answer("❌ Введите число.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_history", IsAdmin())
async def show_history(call: CallbackQuery):
    orders = await rq.get_latest_orders(limit=5)
    if not orders:
        text = "📋 <b>История заявок пуста.</b>"
    else:
        text = "📋 <b>ПОСЛЕДНИЕ 5 ЗАЯВОК:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for o in orders:
            st = "🟢 Выполнена" if o.status == "completed" else "🔴 Отклонена" if o.status == "cancelled" else "🟡 В обработке"
            text += f"ID <b>#{o.id}</b> | Юзер: <code>{o.user_id}</code>\n🔄 {o.amount_give} ➔ {o.amount_receive}\nСтатус: {st}\n\n"
            
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "admin_export", IsAdmin())
async def export_users(call: CallbackQuery):
    async with async_session() as session:
        from sqlalchemy import select
        users = list((await session.scalars(select(User))).all())
    export_data = "ID | Username | Баланс | Объем торгов | Заблокирован\n" + "-"*60 + "\n"
    for u in users:
        export_data += f"{u.tg_id} | @{u.username or 'none'} | {u.balance} RUB | {u.total_volume} | {u.is_banned}\n"
    file = BufferedInputFile(export_data.encode("utf-8"), filename="users.txt")
    await call.message.answer_document(document=file, caption="💾 Выгрузка завершена.")
    await call.answer()

# === ПОИСК И УПРАВЛЕНИЕ ЮЗЕРОМ ===
@router.callback_query(F.data == "admin_find_user", IsAdmin())
async def ask_user_id(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🔍 <b>Введите ID пользователя:</b>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_search_id)

async def render_user_card(message_or_call, user: User):
    st_ban = "🔴 ЗАБЛОКИРОВАН" if user.is_banned else "🟢 АКТИВЕН"
    st_kyc = "✅ ВЕРИФИЦИРОВАН" if getattr(user, 'is_verified', False) else "⚠️ АНОНИМЕН"

    text = (
        f"👤 <b>КАРТОЧКА КЛИЕНТА</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
        f"🗣 <b>Username:</b> @{user.username or 'нет'}\n"
        f"🔐 <b>KYC Статус:</b> {st_kyc}\n"
        f"🚦 <b>Аккаунт:</b> {st_ban}\n\n"
        f"💳 <b>Баланс:</b> <b>{user.balance:,.2f} RUB</b>\n"
        f"📊 <b>Обменов:</b> <b>{user.total_exchanges}</b>\n"
        f"└ <b>Объем:</b> <b>{user.total_volume:,.2f} $</b>\n"
    )

    builder = InlineKeyboardBuilder()
    
    btn_kyc_text = "❌ Аннулировать KYC" if getattr(user, 'is_verified', False) else "🛡 Подтвердить KYC"
    builder.button(text=btn_kyc_text, callback_data=f"adm_kyc_{user.tg_id}")
    
    builder.button(text="💰 Изменить баланс", callback_data=f"adm_edit_bal_{user.tg_id}")
    builder.button(text="✉️ Сообщение", callback_data=f"adm_msg_{user.tg_id}")
    
    btn_ban_text = "🟢 Разблокировать" if user.is_banned else "🔴 Заблокировать"
    builder.button(text=btn_ban_text, callback_data=f"adm_ban_{user.tg_id}")
    
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    builder.adjust(1, 2, 1, 1)
    
    if isinstance(message_or_call, Message):
        await message_or_call.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message_or_call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message(AdminStates.waiting_for_search_id, IsAdmin())
async def search_user_result(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        user = await rq.get_user(uid)
        if not user:
            await message.answer("❌ Пользователь отсутствует в базе данных.")
            await state.clear()
            return
        await render_user_card(message, user)
        await state.clear()
    except ValueError:
        await message.answer("Введите числовой ID.")

@router.callback_query(F.data.startswith("adm_ban_"), IsAdmin())
async def ban_user_btn(call: CallbackQuery):
    uid = int(call.data.split("_")[2])
    user = await rq.get_user(uid)
    new_status = not user.is_banned
    await rq.toggle_user_ban(uid, new_status)
    await call.answer(f"Пользователь {'заблокирован' if new_status else 'разблокирован'}")
    updated_user = await rq.get_user(uid)
    await render_user_card(call, updated_user)

@router.callback_query(F.data.startswith("adm_msg_"), IsAdmin())
async def ask_msg_to_user(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split("_")[2])
    await state.update_data(msg_user_id=uid)
    await call.message.edit_text(f"✉️ <b>Отправьте сообщение (текст/фото), которое получит юзер <code>{uid}</code>:</b>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_user_msg)

@router.message(AdminStates.waiting_for_user_msg, IsAdmin())
async def send_msg_to_user(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data['msg_user_id']
    try:
        await message.copy_to(uid)
        await message.answer("✅ <b>Сообщение успешно доставлено пользователю!</b>", parse_mode="HTML")
    except Exception:
        await message.answer("❌ <b>Ошибка:</b> пользователь заблокировал бота или удалил диалог.", parse_mode="HTML")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_edit_bal_"), IsAdmin())
async def edit_user_balance_start(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split("_")[3])
    await state.update_data(edit_bal_user_id=uid)
    await call.message.edit_text(f"✍️ Введите новый баланс для <code>{uid}</code>:")
    await state.set_state(AdminStates.waiting_for_balance_val)

@router.message(AdminStates.waiting_for_balance_val, IsAdmin())
async def edit_user_balance_finish(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").strip())
        data = await state.get_data()
        from sqlalchemy import update
        async with async_session() as session:
            await session.execute(update(User).where(User.tg_id == data['edit_bal_user_id']).values(balance=val))
            await session.commit()
        await message.answer("✅ Баланс успешно изменен.")
    except ValueError:
        await message.answer("Введите число.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

# === УПРАВЛЕНИЕ НАПРАВЛЕНИЯМИ ===
@router.callback_query(F.data == "admin_rates", IsAdmin())
async def admin_rates_list(call: CallbackQuery):
    async with async_session() as session:
        from sqlalchemy import select
        directions = list((await session.scalars(select(Direction))).all())
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ СОЗДАТЬ НАПРАВЛЕНИЕ", callback_data="dir_add_new")
    for d in directions:
        st = "🟢" if d.is_active else "🔴"
        # Выводим откуда -> куда
        builder.button(text=f"{st} {d.valute_from} ➔ {d.valute_to}", callback_data=f"adm_dir_{d.id}")
    builder.button(text="⬅️ Главное меню", callback_data="admin_main")
    builder.adjust(1)
    await call.message.edit_text("⚙️ <b>УПРАВЛЕНИЕ НАПРАВЛЕНИЯМИ</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_dir_"), IsAdmin())
async def admin_manage_direction(call: CallbackQuery, state: FSMContext):
    if call.data and call.data.startswith("adm_dir_"):
        dir_id = int(call.data.split("_")[2])
        await state.update_data(editing_dir_id=dir_id)
    else:
        data = await state.get_data()
        dir_id = data.get('editing_dir_id')
        
    direction = await rq.get_direction(dir_id)
    if not direction:
        await call.answer("Направление не найдено.")
        return
        
    st_str = "🟢 Включено" if direction.is_active else "🔴 Выключено"
    auto_str = "🤖 АВТОПАРСИНГ" if direction.is_auto_rate else "✍️ РУЧНОЙ КУРС"
    current_final_rate = await rq.get_final_rate(dir_id)
    
    text = (
        f"⚙️ <b>НАСТРОЙКА: {direction.valute_from} ➔ {direction.valute_to}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Тип: Отдает <b>{direction.type_from}</b> ➔ Получает <b>{direction.type_to}</b>\n\n"
        f"Режим цен: <b>{auto_str}</b>\n"
        f"Итоговый курс для клиентов: <b>{current_final_rate}</b>\n\n"
        f"📊 Наценка/Маржа: <b>{direction.margin_percent}%</b>\n"
        f"📈 Базовый ручной курс: <b>{direction.rate}</b>\n"
        f"📉 Лимиты: {direction.min_amount} - {direction.max_amount}\n"
        f"💳 Реквизиты: <code>{direction.admin_requisites}</code>\n"
        f"Статус: {st_str}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Переключить Режим (Авто/Ручной)", callback_data="dir_toggle_auto")
    builder.button(text="📊 Изменить маржу (%)", callback_data="dir_edit_margin")
    builder.button(text="💰 Изменить ручной курс", callback_data="dir_edit_rate")
    builder.button(text="📉 Мин. лимит", callback_data="dir_edit_min")
    builder.button(text="📈 Макс. лимит", callback_data="dir_edit_max")
    builder.button(text="💳 Изменить реквизиты", callback_data="dir_edit_reqs")
    builder.button(text="🟢/🔴 Вкл/Выкл направление", callback_data="dir_toggle_status")
    builder.button(text="🗑 Удалить направление", callback_data="dir_delete")
    builder.button(text="⬅️ Назад", callback_data="admin_rates")
    
    builder.adjust(1, 1, 1, 2, 1, 1, 1, 1)
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "dir_delete", IsAdmin())
async def delete_dir_btn(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dir_id = data.get('editing_dir_id')
    await rq.delete_direction(dir_id)
    await call.answer("🗑 Направление успешно удалено!", show_alert=True)
    await admin_rates_list(call)

@router.callback_query(F.data == "dir_toggle_auto", IsAdmin())
async def toggle_auto_rate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    d = await rq.get_direction(data['editing_dir_id'])
    await rq.update_direction_setting(d.id, "is_auto_rate", not d.is_auto_rate)
    await admin_manage_direction(call, state)

@router.callback_query(F.data == "dir_toggle_status", IsAdmin())
async def toggle_dir_status(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    d = await rq.get_direction(data['editing_dir_id'])
    await rq.update_direction_setting(d.id, "is_active", not d.is_active)
    await admin_manage_direction(call, state)

@router.callback_query(F.data.startswith("dir_edit_"), IsAdmin())
async def trigger_direction_edit(call: CallbackQuery, state: FSMContext):
    action = call.data.split("_")[2]
    if action == "margin":
        await call.message.edit_text("📊 <b>Введите маржу в % (например 2.5 или -1.2):</b>", parse_mode="HTML")
        await state.set_state(AdminStates.editing_margin)
    elif action == "rate":
        await call.message.edit_text("✍️ <b>Введите ручной курс (число):</b>", parse_mode="HTML")
        await state.set_state(AdminStates.editing_rate)
    elif action == "min":
        await call.message.edit_text("📉 <b>Введите минимальный лимит:</b>", parse_mode="HTML")
        await state.set_state(AdminStates.editing_min)
    elif action == "max":
        await call.message.edit_text("📈 <b>Введите максимальный лимит:</b>", parse_mode="HTML")
        await state.set_state(AdminStates.editing_max)
    elif action == "reqs":
        await call.message.edit_text("💳 <b>Отправьте новые реквизиты приема платежей:</b>", parse_mode="HTML")
        await state.set_state(AdminStates.editing_reqs)

@router.message(AdminStates.editing_margin, IsAdmin())
async def save_margin(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").replace("+", "").strip())
        data = await state.get_data()
        await rq.update_direction_setting(data['editing_dir_id'], "margin_percent", val)
        await message.answer("✅ Маржа сохранена.")
    except ValueError:
        await message.answer("❌ Ошибка ввода.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.message(AdminStates.editing_rate, IsAdmin())
async def save_rate(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").strip())
        data = await state.get_data()
        await rq.update_direction_setting(data['editing_dir_id'], "rate", val)
        await message.answer("✅ Ручной курс сохранен.")
    except ValueError:
        await message.answer("❌ Ошибка ввода.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.message(AdminStates.editing_min, IsAdmin())
async def save_min(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").strip())
        data = await state.get_data()
        await rq.update_direction_setting(data['editing_dir_id'], "min_amount", val)
        await message.answer("✅ Минимальный лимит сохранен.")
    except ValueError:
        await message.answer("❌ Ошибка ввода.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.message(AdminStates.editing_max, IsAdmin())
async def save_max(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", ".").strip())
        data = await state.get_data()
        await rq.update_direction_setting(data['editing_dir_id'], "max_amount", val)
        await message.answer("✅ Максимальный лимит сохранен.")
    except ValueError:
        await message.answer("❌ Ошибка ввода.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

@router.message(AdminStates.editing_reqs, IsAdmin())
async def save_reqs(message: Message, state: FSMContext):
    data = await state.get_data()
    await rq.update_direction_setting(data['editing_dir_id'], "admin_requisites", message.text.strip())
    await message.answer("✅ Реквизиты сохранены.")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

# === СОЗДАНИЕ НАПРАВЛЕНИЙ (ОБНОВЛЕНО ПОД 4 КОЛОНКИ) ===
@router.callback_query(F.data == "dir_add_new", IsAdmin())
async def add_dir_start(call: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="Криптовалюта (crypto)", callback_data="newdir_typefrom_crypto")
    builder.button(text="Фиат/Банк (fiat)", callback_data="newdir_typefrom_fiat")
    builder.button(text="❌ Отмена", callback_data="admin_rates")
    builder.adjust(1)
    await call.message.edit_text("🛠 <b>ШАГ 1/7:</b> Что ОТДАЁТ клиент?", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.adding_dir_type_from)

@router.callback_query(AdminStates.adding_dir_type_from, F.data.startswith("newdir_typefrom_"))
async def add_dir_type_from(call: CallbackQuery, state: FSMContext):
    t_from = call.data.split("_")[2]
    await state.update_data(type_from=t_from)
    await call.message.edit_text("🛠 <b>ШАГ 2/7:</b> Введите название валюты, которую отдает клиент (например: <b>BTC</b> или <b>Сбербанк</b>):", parse_mode="HTML")
    await state.set_state(AdminStates.adding_dir_valute_from)

@router.message(AdminStates.adding_dir_valute_from, IsAdmin())
async def add_dir_valute_from(message: Message, state: FSMContext):
    await state.update_data(valute_from=message.text.strip())
    builder = InlineKeyboardBuilder()
    builder.button(text="Криптовалюта (crypto)", callback_data="newdir_typeto_crypto")
    builder.button(text="Фиат/Банк (fiat)", callback_data="newdir_typeto_fiat")
    builder.adjust(1)
    await message.answer("🛠 <b>ШАГ 3/7:</b> Что ПОЛУЧАЕТ клиент?", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.adding_dir_type_to)

@router.callback_query(AdminStates.adding_dir_type_to, F.data.startswith("newdir_typeto_"))
async def add_dir_type_to(call: CallbackQuery, state: FSMContext):
    t_to = call.data.split("_")[2]
    await state.update_data(type_to=t_to)
    await call.message.edit_text("🛠 <b>ШАГ 4/7:</b> Введите название валюты, которую получает клиент (например: <b>USDT</b> или <b>Т-Банк</b>):", parse_mode="HTML")
    await state.set_state(AdminStates.adding_dir_valute_to)

@router.message(AdminStates.adding_dir_valute_to, IsAdmin())
async def add_dir_valute_to(message: Message, state: FSMContext):
    await state.update_data(valute_to=message.text.strip())
    await message.answer("🛠 <b>ШАГ 5/7:</b> Введите базовый ручной курс обмена (число, например 95.50):", parse_mode="HTML")
    await state.set_state(AdminStates.adding_dir_rate)

@router.message(AdminStates.adding_dir_rate, IsAdmin())
async def add_dir_rate_step(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", ".").strip())
        await state.update_data(new_rate=rate)
        await message.answer("🛠 <b>ШАГ 6/7:</b> Укажите лимиты МИН и МАКС через пробел (например <code>1000 500000</code>):", parse_mode="HTML")
        await state.set_state(AdminStates.adding_dir_min)
    except ValueError:
        await message.answer("❌ Введите число.")

@router.message(AdminStates.adding_dir_min, IsAdmin())
async def add_dir_limits_step(message: Message, state: FSMContext):
    try:
        arr = message.text.strip().split()
        await state.update_data(new_min=float(arr[0]), new_max=float(arr[1]))
        await message.answer("🛠 <b>ШАГ 7/7:</b> Введите реквизиты приема платежей для этого направления:", parse_mode="HTML")
        await state.set_state(AdminStates.adding_dir_reqs)
    except Exception:
        await message.answer("❌ Ошибка формата. Пример: 1000 500000")

@router.message(AdminStates.adding_dir_reqs, IsAdmin())
async def add_dir_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Передаем 8 аргументов в rq.add_new_direction (valute_from, type_from, valute_to, type_to, rate, min, max, reqs)
    await rq.add_new_direction(
        data['valute_from'], data['type_from'],
        data['valute_to'], data['type_to'],
        data['new_rate'], data['new_min'], data['new_max'], 
        message.text.strip()
    )
    
    await message.answer("✅ <b>Направление успешно создано!</b>", parse_mode="HTML")
    await state.clear()
    await message.answer(get_dashboard_text(), reply_markup=get_admin_main_kb(), parse_mode="HTML")

# === МАССОВАЯ РАССЫЛКА ===
@router.callback_query(F.data == "admin_broadcast", IsAdmin())
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📢 <b>Отправьте сообщение для рассылки (текст/фото):</b>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_broadcast_msg)

@router.message(AdminStates.waiting_for_broadcast_msg, IsAdmin())
async def broadcast_send(message: Message, state: FSMContext):
    async with async_session() as session:
        from sqlalchemy import select
        users = list((await session.scalars(select(User))).all())
    await message.answer("⏳ Массовая рассылка запущена...")
    ok, err = 0, 0
    for u in users:
        try:
            await message.copy_to(u.tg_id)
            ok += 1
        except Exception:
            err += 1
    await message.answer(f"✅ Рассылка завершена.\nУспешно отправлено: {ok}\nОшибок (бан бота): {err}")
    await state.clear()

# === ОБРАБОТКА ЗАЯВОК ===
@router.callback_query(F.data.startswith("order_approve_"), IsAdmin())
async def approve_order(call: CallbackQuery, bot: Bot):
    _, _, oid, uid = call.data.split("_")
    oid, uid = int(oid), int(uid)
    
    order = await rq.get_order(oid)
    direction = await rq.get_direction(order.direction_id)
    
    await rq.update_order_status(oid, "completed")
    await rq.process_referral_reward(uid, order.amount_receive, direction.margin_percent)
    
    user = await rq.get_user(uid)
    from sqlalchemy import update
    async with async_session() as session:
        await session.execute(update(User).where(User.tg_id == uid).values(
            total_exchanges=user.total_exchanges + 1, 
            total_volume=user.total_volume + order.amount_receive
        ))
        await session.commit()
        
    if call.message.caption:
        await call.message.edit_caption(caption=f"{call.message.caption}\n➖➖➖➖➖➖➖➖➖\n✅ <b>Заявка Одобрена</b>", parse_mode="HTML")
    else:
        await call.message.edit_text(text=f"{call.message.text}\n➖➖➖➖➖➖➖➖➖\n✅ <b>Заявка Одобрена</b>", parse_mode="HTML")
    
    try:
        await bot.send_message(
            chat_id=uid,
            text=(
                f"✅ <b>ОПЕРАЦИЯ №{oid} ИСПОЛНЕНА</b>\n"
                f"➖➖➖➖➖➖➖➖➖\n\n"
                f"💳 <b>Статус:</b> Средства отправлены на ваши реквизиты.\n"
                f"📈 <b>Результат:</b> Заявка выполнена в полном объеме.\n\n"
                f"<i>Благодарим за выбор нашего сервиса. "
                f"Мы будем рады видеть вас снова.</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления юзеру {uid}: {e}")

@router.callback_query(F.data.startswith("order_reject_"), IsAdmin())
async def reject_order(call: CallbackQuery, bot: Bot):
    _, _, oid, uid = call.data.split("_")
    await rq.update_order_status(int(oid), "cancelled")
    
    if call.message.caption:
        await call.message.edit_caption(caption=f"{call.message.caption}\n➖➖➖➖➖➖➖➖➖\n❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>", parse_mode="HTML")
    else:
        await call.message.edit_text(text=f"{call.message.text}\n➖➖➖➖➖➖➖➖➖\n❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>", parse_mode="HTML")
    
    try:
        await bot.send_message(
            chat_id=uid,
            text=(
                f"❌ <b>ЗАЯВКА №{oid} ОТКЛОНЕНА</b>\n"
                f"➖➖➖➖➖➖➖➖➖\n\n"
                f"⚠️ <b>Статус:</b> Операция отменена администратором.\n"
                f"ℹ️ <b>Причина:</b> Некорректные данные или нарушение условий сервиса.\n\n"
                f"<i>Для уточнения деталей и возврата средств, пожалуйста, "
                f"обратитесь в нашу службу поддержки.</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления юзеру {uid}: {e}")