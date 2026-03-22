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

# Клавиатура выбора категории игр
games_category_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚡️Динамический", callback_data="cat_dynamic")],
    [InlineKeyboardButton(text="🎯Статический", callback_data="cat_static")],
    [InlineKeyboardButton(text="🎮Перейти в чат", url=CHAT_LINK)]
])

# Клавиатура для статических игр
static_games_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎰 Слот-машина", callback_data="game_slot")],
    [InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice")],
    [InlineKeyboardButton(text="🎯 Дартс", callback_data="game_darts")],
    [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="game_basket")],
    [InlineKeyboardButton(text="⚽ Футбол", callback_data="game_football")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
])

# Клавиатура для динамических игр
dynamic_games_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette")],
    [InlineKeyboardButton(text="💣 Мины", callback_data="game_mines")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
])
