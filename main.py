import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import database as db
import handlers as handlers

async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(handlers.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())