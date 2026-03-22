from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
import database as db
import keyboards as kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        db.create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "Привет 👋 Я GALL! 💎\n\n"
        "💥 Скоротай время в мире азарта и крутых игр. Прокачивай свой скилл, соревнуйся с друзьями или просто испытай удачу — скучно точно не будет! ⚡️\n\n"
        "🤔 Итак, с чего начнем?\n"
        "• Жми 🎲 Игры, чтобы сорвать куш\n"
        "• Либо просто пиши /game и врывайся в топ! 🏆\n\n"
        "❓ Остались вопросы? — 👉 /help 😏",
        reply_markup=kb.main_menu
    )

@router.message(F.text == "Чаты")
async def chats_button(message: Message):
    await message.answer(
        "🔗 Наши официальные ресурсы\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "📢 Новостной канал:\n└ Здесь публикуются обновления и важные новости проекта.\n\n"
        "💬 Официальный чат:\n└ Общение, торговля и поддержка игроков.\n\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Новостной канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Официальный чат", url=CHAT_LINK)]
        ])
    )

@router.message(F.text == "Бонус")
async def bonus_button(message: Message):
    user_id = message.from_user.id
    last = db.get_last_bonus(user_id)
    now = datetime.datetime.now()
    if last and (now - last).total_seconds() < 12*3600:
        wait = (last + datetime.timedelta(hours=12) - now)
        hours, remainder = divmod(wait.seconds, 3600)
        minutes = remainder // 60
        await message.answer(f"🎁 Бонус уже получен! Следующий через {hours} ч {minutes} мин.")
    else:
        db.update_balance(user_id, 2500, "Ежедневный бонус")
        db.set_last_bonus(user_id)
        await message.answer(
            "🎁 Ежедневная награда получена!\n━━━━━━━━━━━━━━━━━━━━\n"
            "Вы получили: +10 000 GALL\n\n"
            "Следующий бонус будет доступен ровно через 12 часов.\n━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Пойти играть", callback_data="go_play")]
            ])
        )

@router.message(F.text == "Профиль")
async def profile_button(message: Message):
    user = db.get_user(message.from_user.id)
    if user:
        balance = user[2]
        text = (f"👤 Личный кабинет\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Игрок: {message.from_user.full_name}\n"
                f"ID: {message.from_user.id}\n"
                f"Баланс: {balance} GALL\n\n"
                f"💰 Ваша валюта GALL надежно защищена.\n━━━━━━━━━━━━━━━━━━━━")
        await message.answer(text)
    else:
        await message.answer("Профиль не найден. Напишите /start.")

@router.message(F.text == "Команды")
async def commands_button(message: Message):
    await message.answer(
        "💎 Полный список команд HARD\n\n"
        "💳 Твой кошелек:\n"
        "├ баланс (или б) — чекнуть счёт\n"
        "├ /профиль — всё о твоём статусе\n"
        "└ /history — логи твоих побед и трат\n\n"
        "💸 Переводы и бонусы:\n"
        "├ п [сумма] — скинуть кэш (ответом)\n"
        "├ п [ID] [сумма] — перевод по ID\n"
        "├ чеки — создать чек на валюту\n"
        "├ промо [код] — забрать халяву\n"
        "└ /top — заглянуть в список Forbes\n\n"
        "🚀 Для владельцев групп:\n"
        "├ /games — ⚙️ настройка игр (вкл/выкл)\n"
        "├ казна [сумма] — пополнить общий фонд\n"
        "├ казна — проверить баланс фонда группы\n"
        "└ награда [сумма] — выдать бонус из казны"
    )

@router.message(F.text == "Игры")
async def games_button(message: Message):
    await message.answer(
        "🎰 Игровой зал GALL\n━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в элитный клуб! Выбирай свой стиль игры и начинай побеждать.\n\n"
        "👇 Выбери категорию:",
        reply_markup=kb.games_category_menu
    )

@router.callback_query(F.data == "cat_dynamic")
async def cat_dynamic(callback: CallbackQuery):
    await callback.message.edit_text("🎲 Динамические игры:\nЗдесь важен каждый ход.\nВыберите игру:", reply_markup=kb.dynamic_games_menu)
    await callback.answer()

@router.callback_query(F.data == "cat_static")
async def cat_static(callback: CallbackQuery):
    await callback.message.edit_text("🎲 Статические игры:\nИспытай удачу в один клик.\nВыберите игру:", reply_markup=kb.static_games_menu)
    await callback.answer()

@router.message(F.text == "Донат")
async def donate_button(message: Message):
    text = (
        "⭐ Пополнение баланса GALL\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Вы можете мгновенно приобрести валюту через Telegram Stars.\n"
        "Это самый быстрый и безопасный способ стать богаче в игре!\n\n"
        "💎 Что дают GALL?\n"
        "├ Возможность играть по крупным ставкам\n"
        "├ Создание собственных чеков для друзей\n"
        "└ Попадание в глобальный топ игроков\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⬇️ Нажмите кнопку ниже, чтобы перейти к покупке:"
    )
    buy_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить GALL", callback_data="show_donation_plans")]
    ])
    await message.answer(text, reply_markup=buy_button)

@router.callback_query(F.data == "show_donation_plans")
async def show_donation_plans(callback: CallbackQuery):
    text = "💎 Выберите сумму пополнения:\n\n"
    for stars, info in DONATION_PLANS.items():
        text += f"⭐ {stars} Stars → +{info['gall']} GALL"
        if info['bonus']:
            text += f" (+{info['bonus']}% бонус)"
        text += "\n"
    await callback.message.edit_text(text)
    await callback.answer()

# Обработчик для кнопки "Пойти играть" после бонуса
@router.callback_query(F.data == "go_play")
async def go_play(callback: CallbackQuery):
    await callback.message.answer(
        "🎰 Игровой зал GALL\n━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в элитный клуб! Выбирай свой стиль игры и начинай побеждать.\n\n"
        "👇 Выбери категорию:",
        reply_markup=kb.games_category_menu
    )
    await callback.answer()

# Кнопка "Назад" из игровых меню
@router.callback_query(F.data == "back_to_games")
async def back_to_games(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎰 Игровой зал GALL\n━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в элитный клуб! Выбирай свой стиль игры и начинай побеждать.\n\n"
        "👇 Выбери категорию:",
        reply_markup=kb.games_category_menu
    )
    await callback.answer()

# Заглушки для всех игр
@router.callback_query(F.data == "game_slot")
async def game_slot(callback: CallbackQuery):
    await callback.answer("Слот-машина в разработке!", show_alert=True)

@router.callback_query(F.data == "game_dice")
async def game_dice(callback: CallbackQuery):
    await callback.answer("Кости в разработке!", show_alert=True)

@router.callback_query(F.data == "game_darts")
async def game_darts(callback: CallbackQuery):
    await callback.answer("Дартс в разработке!", show_alert=True)

@router.callback_query(F.data == "game_basket")
async def game_basket(callback: CallbackQuery):
    await callback.answer("Баскетбол в разработке!", show_alert=True)

@router.callback_query(F.data == "game_football")
async def game_football(callback: CallbackQuery):
    await callback.answer("Футбол в разработке!", show_alert=True)

@router.callback_query(F.data == "game_roulette")
async def game_roulette(callback: CallbackQuery):
    await callback.answer("Рулетка в разработке!", show_alert=True)

@router.callback_query(F.data == "game_mines")
async def game_mines(callback: CallbackQuery):
    await callback.answer("Мины в разработке!", show_alert=True)


