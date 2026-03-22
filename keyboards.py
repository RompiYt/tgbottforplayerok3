from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHAT_LINK

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Чаты"), KeyboardButton(text="Профиль")],
        [KeyboardButton(text="Команды"), KeyboardButton(text="Бонус")],
        [KeyboardButton(text="Игры"), KeyboardButton(text="Донат")]
    ],
    resize_keyboard=True
)

# Если нужна кнопка перехода в чат из раздела Игры, можно сделать так:
games_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Перейти в чат", url=CHAT_LINK)]
])