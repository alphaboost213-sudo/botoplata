import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config, CALLBACK_URL
from database import requests as rq
from states.worker_fsm import WorkerFSM
from keyboards.worker_kb import get_worker_main_kb, get_cancel_kb

router = Router()
BASE_URL = "https://trader-cab.com"


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in config.WORKER_IDS:
        return await message.answer("⛔ У вас нет доступа к этому боту.")
    await message.answer(
        "👋 Привет, работник!\n\nВыберите действие:",
        reply_markup=get_worker_main_kb()
    )


@router.callback_query(F.data == "main_menu")
async def back_to_menu(call: CallbackQuery):
    await call.message.edit_text(
        "👋 Главное меню. Выберите действие:",
        reply_markup=get_worker_main_kb()
    )


@router.callback_query(F.data.startswith("method_"))
async def choose_method(call: CallbackQuery, state: FSMContext):
    method = call.data.split("_")[1]
    await state.update_data(method=method)
    name = "💳 Карта" if method == "bank_card" else "📲 СБП"
    await call.message.edit_text(
        f"{name}\n\nВведите сумму в <b>RUB</b>, которую должен оплатить клиент:",
        reply_markup=get_cancel_kb(), parse_mode="HTML"
    )
    await state.set_state(WorkerFSM.waiting_amount)


@router.message(WorkerFSM.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("❌ Введите корректную сумму (например: 15000).")

    data = await state.get_data()
    method = data["method"]
    ext_id = f"wrk_{message.from_user.id}_{int(message.date.timestamp())}"

    payload = {
        "merchantExternalOrderId": ext_id,
        "flatAmount": str(amount),
        "flatCurrency": "RUB",
        "paymentMethodCode": method,
        "ttlSeconds": 900,
    }
    if CALLBACK_URL:
        payload["callbackUrl"] = CALLBACK_URL
    else:
        payload["callbackUrl"] = "https://httpbin.org/post"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/merchant/orders",
            headers={"Authorization": f"Bearer {config.TRADERCAB_MKEY}", "Content-Type": "application/json"},
            json=payload,
        ) as resp:
            status = resp.status
            result = await resp.json()

    if status != 200:
        err = result.get("error", "unknown")
        msg = result.get("message", "")
        return await message.answer(
            f"❌ Ошибка trader-cab: <code>{err}</code>\n{msg}\n\nПопробуйте позже.",
            parse_mode="HTML",
        )

    req = result.get("requisite", {}).get("fields", {})
    await rq.create_tradercab_order(
        tg_id=message.from_user.id,
        merchant_external_id=ext_id,
        tradercab_order_id=result["orderId"],
        amount_rub=amount,
        payment_method=method,
        status=result["status"],
        requisite_field=req.get("cardNumber") or req.get("phoneNumber") or req.get("qrUrl", ""),
        requisite_holder=req.get("holderName", ""),
        requisite_bank=req.get("bankName", ""),
        expires_at=result.get("expiresAt", ""),
    )

    if method == "bank_card":
        text = (
            f"✅ <b>Заявка создана!</b>\n\n"
            f"🆔 Order ID: <code>{result['orderId']}</code>\n"
            f"💰 Сумма: <b>{amount:,.0f} ₽</b>\n"
            f"💳 Номер карты: <code>{req.get('cardNumber', '—')}</code>\n"
            f"👤 Получатель: <b>{req.get('holderName', '—')}</b>\n"
            f"🏦 Банк: <b>{req.get('bankName', '—')}</b>\n\n"
            f"⏳ Активна до: <code>{result.get('expiresAt', '—')[:19].replace('T', ' ')}</code>\n\n"
            f"📋 <i>Скопируйте реквизиты и отправьте клиенту.</i>"
        )
    else:
        text = (
            f"✅ <b>Заявка создана!</b>\n\n"
            f"🆔 Order ID: <code>{result['orderId']}</code>\n"
            f"💰 Сумма: <b>{amount:,.0f} ₽</b>\n"
            f"📲 Телефон СБП: <code>{req.get('phoneNumber', '—')}</code>\n"
            f"👤 Получатель: <b>{req.get('holderName', '—')}</b>\n"
            f"🏦 Банк: <b>{req.get('bankName', '—')}</b>\n\n"
            f"⏳ Активна до: <code>{result.get('expiresAt', '—')[:19].replace('T', ' ')}</code>\n\n"
            f"📋 <i>Скопируйте реквизиты и отправьте клиенту.</i>"
        )

    await message.answer(text, reply_markup=get_worker_main_kb(), parse_mode="HTML")
    await state.clear()


@router.callback_query(F.data == "my_orders")
async def show_orders(call: CallbackQuery):
    orders = await rq.get_worker_orders(call.from_user.id, limit=10)
    if not orders:
        return await call.message.edit_text("📋 У вас пока нет заявок.", reply_markup=get_worker_main_kb())

    text = "📋 <b>Ваши последние заявки:</b>\n\n"
    for o in orders:
        status_emoji = {"PENDING": "🟡", "CONFIRMED": "🟢", "EXPIRED": "🔴", "CANCELLED": "⚫", "DISPUTED": "🟠"}.get(o.status, "⚪")
        method_name = "💳 Карта" if o.payment_method == "bank_card" else "📲 СБП"
        req = o.requisite_field or "—"
        text += f"{status_emoji} <b>#{o.tradercab_order_id[-8:]}</b> | {method_name}\n   Сумма: <b>{o.amount_rub:,.0f} ₽</b> | Статус: <b>{o.status}</b>\n   Реквизит: <code>{req}</code>\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить статусы", callback_data="refresh_all")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "refresh_all")
async def refresh_all_statuses(call: CallbackQuery):
    orders = await rq.get_worker_orders(call.from_user.id, limit=10)
    updated = 0
    for o in orders:
        if o.status in ("CONFIRMED", "EXPIRED", "CANCELLED"):
            continue
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/api/merchant/orders/{o.tradercab_order_id}",
                headers={"Authorization": f"Bearer {config.TRADERCAB_MKEY}"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    new_status = data.get("status", o.status)
                    if new_status != o.status:
                        await rq.update_tradercab_order_status(o.tradercab_order_id, new_status, data.get("finalizedAt"))
                        updated += 1
    await call.answer(f"Обновлено {updated} заявок", show_alert=False)
    await show_orders(call)


@router.callback_query(F.data == "my_balance")
async def show_balance(call: CallbackQuery):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/merchant/balance",
            headers={"Authorization": f"Bearer {config.TRADERCAB_MKEY}"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = (
                    f"💰 <b>Баланс в trader-cab</b>\n\n"
                    f"Доступно: <b>{data.get('availableBalance', '—')} USDT</b>\n"
                    f"Заморожено: <b>{data.get('reservedBalance', '—')} USDT</b>\n"
                    f"Итого: <b>{data.get('totalBalance', '—')} USDT</b>"
                )
            else:
                text = "❌ Не удалось получить баланс."
    await call.message.edit_text(text, reply_markup=get_worker_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Отменено.", reply_markup=get_worker_main_kb())
