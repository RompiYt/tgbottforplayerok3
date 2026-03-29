import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import database as db
import handlers as handlers

async def main():
    db.init_db()

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    dp.include_router(handlers.router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    asyncio.run(main())
