from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_worker_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Карта", callback_data="method_bank_card")
    builder.button(text="📲 СБП", callback_data="method_sbp")
    builder.button(text="📋 Мои заявки", callback_data="my_orders")
    builder.button(text="💰 Баланс", callback_data="my_balance")
    builder.adjust(2, 2)
    return builder.as_markup()

def get_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()
