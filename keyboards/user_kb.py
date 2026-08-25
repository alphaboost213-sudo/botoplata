from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📉 Купить", callback_data="buy_crypto")
    builder.button(text="📈 Продать", callback_data="sell_crypto")
    builder.button(text="💼 Личный кабинет", callback_data="profile")
    builder.button(text="👥 Реферальная система", callback_data="referrals")
    builder.button(text="ℹ️ О нас", callback_data="about")
    builder.button(text="❓ FAQ", callback_data="faq")
    builder.button(text="👨‍💻 Поддержка", callback_data="support")
    builder.adjust(2, 1, 1, 2, 1) # Красивая сетка кнопок
    return builder.as_markup()

def get_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="cancel_exchange")
    return builder.as_markup()

def get_crypto_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🪙 USDT (TRC20)", callback_data="crypto_usdt")
    builder.button(text="₿ BTC (Bitcoin)", callback_data="crypto_btc")
    builder.button(text="❌ Отмена", callback_data="cancel_exchange")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_bank_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Т-Банк", callback_data="bank_tbank")
    builder.button(text="🏦 Сбербанк", callback_data="bank_sber")
    builder.button(text="❌ Отмена", callback_data="cancel_exchange")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_order_confirmation_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оплатил", callback_data="order_paid")
    builder.button(text="❌ Отменить", callback_data="cancel_exchange")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_exchange")
    return builder.as_markup()