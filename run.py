import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import config
from database.engine import init_db
from utils.api_parser import get_actual_rate, CG_MAPPING  # Импортируем парсер

from handlers.user_menu import router as menu_router
from handlers.user_exchange import router as exchange_router
from handlers.user_profile import router as profile_router
from handlers.admin import router as admin_router

# Глобальный словарь для хранения курсов в оперативной памяти
CURRENT_RATES = {}

async def update_rates_task():
    """Фоновая задача: обновляет курсы каждые 10 минут"""
    while True:
        logging.info("Начато обновление курсов криптовалют...")
        for symbol in CG_MAPPING.keys():
            rate = await get_actual_rate(symbol)
            if rate > 0:
                CURRENT_RATES[symbol] = rate
        logging.info(f"Курсы обновлены: {len(CURRENT_RATES)} монет.")
        await asyncio.sleep(600)  # 600 секунд = 10 минут

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Инициализация БД
    await init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Запускаем фоновую задачу парсинга перед стартом бота
    asyncio.create_task(update_rates_task())

    # Подключение роутеров
    dp.include_router(menu_router)
    dp.include_router(exchange_router)
    dp.include_router(profile_router)
    dp.include_router(admin_router)

    logging.info("Bot is starting...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")