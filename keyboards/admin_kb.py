from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📋 История заявок", callback_data="admin_history")
    builder.button(text="⚙️ Управление направлениями", callback_data="admin_rates")
    builder.button(text="🔍 Поиск юзера", callback_data="admin_find_user")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="💾 Выгрузить базу (.txt)", callback_data="admin_export")
    builder.button(text="🎁 Реф. процент", callback_data="admin_set_ref_percent")
    builder.adjust(2, 1, 2, 1) # Идеальная сетка для премиум вида
    return builder.as_markup()

def get_order_decision_kb(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"order_approve_{order_id}_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"order_reject_{order_id}_{user_id}")
    builder.adjust(2)
    return builder.as_markup()