import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from config import config, WEBHOOK_HOST
from database.engine import init_db
from handlers.worker import router as worker_router
from handlers.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(worker_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if WEBHOOK_HOST:
        webhook_url = f"{WEBHOOK_HOST}/webhook"
        await bot.set_webhook(url=webhook_url)
        logging.info(f"✅ Webhook установлен: {webhook_url}")
    else:
        logging.warning("⚠️ WEBHOOK_HOST не задан — webhook не установлен!")
    yield
    await bot.session.close()

app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", config.PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
