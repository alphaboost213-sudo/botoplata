import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Response
from aiogram import Bot

from config import config
from database import requests as rq

router = APIRouter()

@router.post("/tradercab/callback")
async def tradercab_callback(request: Request, bot: Bot):
    raw = await request.body()
    signature = request.headers.get("x-callback-signature", "")

    if config.WEBHOOK_SECRET:
        expected = hmac.new(
            config.WEBHOOK_SECRET.encode("utf-8"),
            raw,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return Response(status_code=401)

    event = json.loads(raw)
    order_id = event.get("orderId")
    status = event.get("status")
    merchant_ext_id = event.get("merchantExternalOrderId")
    finalized_at = event.get("finalizedAt")

    await rq.update_tradercab_order_status(order_id, status, finalized_at)
    order = await rq.get_tradercab_order_by_external(merchant_ext_id)
    if not order:
        return Response(status_code=200)

    tg_id = order.tg_id
    if status == "CONFIRMED":
        text = f"🟢 <b>ЗАЯВКА ОПЛАЧЕНА!</b>

🆔 Order ID: <code>{order_id}</code>
💰 Сумма: <b>{order.amount_rub:,.0f} ₽</b>
✅ Клиент перевёл деньги."
    elif status == "EXPIRED":
        text = f"🔴 <b>ЗАЯВКА ПРОСРОЧЕНА</b>

🆔 Order ID: <code>{order_id}</code>
💰 Сумма: <b>{order.amount_rub:,.0f} ₽</b>
⏰ Клиент не успел оплатить."
    elif status == "CANCELLED":
        text = f"⚫ <b>ЗАЯВКА ОТМЕНЕНА</b>

🆔 Order ID: <code>{order_id}</code>
💰 Сумма: <b>{order.amount_rub:,.0f} ₽</b>"
    else:
        return Response(status_code=200)

    try:
        await bot.send_message(tg_id, text, parse_mode="HTML")
    except Exception:
        pass
    return Response(status_code=200)
