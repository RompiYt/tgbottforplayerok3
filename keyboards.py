from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHAT_LINK

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="чаты"), KeyboardButton(text="профиль")],
        [KeyboardButton(text="команды"), KeyboardButton(text="бонус")],
        [KeyboardButton(text="игры"), KeyboardButton(text="донат")]
    ],
    resize_keyboard=True
)

games_category_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚡️Динамический", callback_data="cat_dynamic")],
    [InlineKeyboardButton(text="🎯Статический", callback_data="cat_static")],
    [InlineKeyboardButton(text="🎮Перейти в чат", url=CHAT_LINK)]
])
