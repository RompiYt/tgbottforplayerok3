from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus

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
            "Вы получили: +2500 GALL\n\n"
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
        "├ Баланс — чекнуть счёт\n"
        "├ Профиль — всё о твоём статусе\n"
        "└ /history — логи твоих побед и трат\n\n"
        "💸 Переводы и бонусы:\n"
        "├ /п [сумма] — скинуть кэш (ответом)\n"
        "├ /п [ID] [сумма] — перевод по ID\n"
        "├ /промо [код] — забрать халяву\n"
        "└ /top — заглянуть в список Forbes\n\n"
        "🚀 Для владельцев групп:\n"
        "├ /games — ⚙️ настройка игр (вкл/выкл)\n"
        "├ /казна [сумма] — пополнить общий фонд\n"
        "├ /казна — проверить баланс фонда группы\n"
        "└ /награда [сумма] — выдать бонус из казны"
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

@router.message(Command("help"))
async def help_command(message: Message):
    text = (
        "💎 Полный список команд GALL\n\n"
        "💳 Твой кошелек:\n"
        "├ Баланс — чекнуть счёт\n"
        "├ Профиль — всё о твоём статусе\n"
        "└ /history — логи твоих побед и трат\n\n"
        "💸 Переводы и бонусы:\n"
        "├ п [сумма] — скинуть кэш (ответом)\n"
        "├ п [ID] [сумма] — перевод по ID\n"
        "├ промо [код] — забрать халяву\n"
        "└ /top — заглянуть в список Forbes\n\n"
        "🚀 Для владельцев групп:\n"
        "Хочешь привлечь игроков в свой чат? Используй казну!\n"
        "├ /games — ⚙️ настройка игр (вкл/выкл)\n"
        "├ казна — проверить баланс фонда группы\n"
        "├ награда [сумма] — выдать бонус из казны\n"
        "├ /deposit [сумма] — пополнить казну\n"
        "└ /set_reward [сумма] — установить награду за приглашение"
    )
    await message.answer(text)

# /game
@router.message(Command("game"))
async def game_command(message: Message):
    # Перенаправляем в игровой зал
    await games_button(message)

# /history
@router.message(Command("history"))
async def history_command(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT amount, reason, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.answer("История пуста.")
        return
    text = "📜 Последние операции:\n\n"
    for amount, reason, ts in rows:
        sign = "+" if amount > 0 else ""
        text += f"{ts[:19]} | {sign}{amount} GALL | {reason}\n"
    await message.answer(text[:4000])  # ограничение Telegram

# /top
@router.message(Command("top"))
async def top_command(message: Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.answer("Нет пользователей.")
        return
    text = "🏆 Топ-10 игроков по балансу:\n\n"
    for i, (username, balance) in enumerate(rows, 1):
        text += f"{i}. {username or 'Аноним'} — {balance} GALL\n"
    await message.answer(text)

# Перевод: п [сумма] (ответом) или п [ID] [сумма]
@router.message(Command("п"))
async def transfer_command(message: Message):
    args = message.text.split()
    if len(args) == 2:
        # Перевод по ответу
        if not message.reply_to_message:
            await message.answer("Чтобы перевести, ответьте на сообщение пользователя.")
            return
        try:
            amount = int(args[1])
            if amount <= 0:
                await message.answer("Сумма должна быть положительной.")
                return
            sender_id = message.from_user.id
            receiver_id = message.reply_to_message.from_user.id
            if sender_id == receiver_id:
                await message.answer("Нельзя перевести самому себе.")
                return
            sender_balance = db.get_balance(sender_id)
            if sender_balance < amount:
                await message.answer(f"Недостаточно средств. Ваш баланс: {sender_balance} GALL.")
                return
            db.update_balance(sender_id, -amount, f"Перевод пользователю {receiver_id}")
            db.update_balance(receiver_id, amount, f"Перевод от {sender_id}")
            await message.answer(f"✅ Переведено {amount} GALL пользователю {message.reply_to_message.from_user.full_name}.")
        except ValueError:
            await message.answer("Неверная сумма.")
    elif len(args) == 3:
        # Перевод по ID
        try:
            receiver_id = int(args[1])
            amount = int(args[2])
            if amount <= 0:
                await message.answer("Сумма должна быть положительной.")
                return
            sender_id = message.from_user.id
            if sender_id == receiver_id:
                await message.answer("Нельзя перевести самому себе.")
                return
            receiver = db.get_user(receiver_id)
            if not receiver:
                await message.answer("Пользователь с таким ID не найден.")
                return
            sender_balance = db.get_balance(sender_id)
            if sender_balance < amount:
                await message.answer(f"Недостаточно средств. Ваш баланс: {sender_balance} GALL.")
                return
            db.update_balance(sender_id, -amount, f"Перевод пользователю {receiver_id}")
            db.update_balance(receiver_id, amount, f"Перевод от {sender_id}")
            await message.answer(f"✅ Переведено {amount} GALL пользователю {receiver[1] or receiver_id}.")
        except ValueError:
            await message.answer("Неверный ID или сумма.")
    else:
        await message.answer("Использование: п [сумма] (ответом) или п [ID] [сумма]")

# промо [код]
@router.message(Command("промо"))
async def promo_command(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: промо [код]")
        return
    code = args[1].strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT reward FROM promocodes WHERE code=? AND used_by IS NULL", (code,))
    row = c.fetchone()
    if not row:
        await message.answer("Неверный или уже использованный промокод.")
        conn.close()
        return
    reward = row[0]
    c.execute("UPDATE promocodes SET used_by=? WHERE code=?", (message.from_user.id, code))
    conn.commit()
    conn.close()
    db.update_balance(message.from_user.id, reward, f"Активация промокода {code}")
    await message.answer(f"🎉 Промокод активирован! Получено +{reward} GALL.")

# /games (настройка игр в группе)
@router.message(Command("games"))
async def games_config(message: Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return
    # Проверка прав админа
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer("Только администраторы могут настраивать игры.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT games_enabled FROM groups WHERE group_id=?", (message.chat.id,))
    row = c.fetchone()
    if row:
        new_state = 1 - row[0]
        c.execute("UPDATE groups SET games_enabled=? WHERE group_id=?", (new_state, message.chat.id))
    else:
        new_state = 0
        c.execute("INSERT INTO groups (group_id, games_enabled) VALUES (?, ?)", (message.chat.id, new_state))
    conn.commit()
    conn.close()
    status = "включены" if new_state else "отключены"
    await message.answer(f"Игры в группе {status}.")

# казна (проверка баланса)
@router.message(Command("казна"))
async def treasury_info(message: Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return
    treasury = db.get_group_treasury(message.chat.id)
    text = (f"🏦 Казна чата:\n"
            f"Баланс: {treasury['balance']} GALL\n"
            f"Награда за приглашение: {treasury['reward']} GALL\n\n"
            f"Чтобы пополнить: /deposit [сумма]\n"
            f"Изменить награду: /set_reward [сумма]")
    await message.answer(text)

# награда [сумма] (выдать из казны пользователю)
@router.message(Command("награда"))
async def give_reward(message: Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return
    # Проверка прав админа
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer("Только администраторы могут выдавать награды.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: награда [сумма] (ответом на сообщение пользователя)")
        return
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя, которому хотите выдать награду.")
        return
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.answer("Сумма должна быть положительной.")
            return
        treasury = db.get_group_treasury(message.chat.id)
        if treasury['balance'] < amount:
            await message.answer(f"Недостаточно средств в казне. Доступно: {treasury['balance']} GALL.")
            return
        # Выдаем награду
        db.update_balance(message.reply_to_message.from_user.id, amount, f"Награда из казны группы {message.chat.id}")
        db.subtract_from_treasury(message.chat.id, amount)
        await message.answer(f"✅ Выдано {amount} GALL пользователю {message.reply_to_message.from_user.full_name}.")
    except ValueError:
        await message.answer("Неверная сумма.")

@router.message(Command("deposit"))
async def deposit_treasury(message: Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return
    # Убираем проверку на админа — любой может пополнить
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /deposit [сумма]")
        return
    try:
        amount = int(args[1])
        if amount <= 0:
            await message.answer("Сумма должна быть положительной.")
            return
        user_balance = db.get_balance(message.from_user.id)
        if user_balance < amount:
            await message.answer(f"Недостаточно средств. Ваш баланс: {user_balance} GALL.")
            return
        # Списываем у пользователя
        db.update_balance(message.from_user.id, -amount, f"Пополнение казны группы {message.chat.id}")
        # Добавляем в казну
        db.add_to_treasury(message.chat.id, amount)
        new_balance = db.get_group_treasury(message.chat.id)['balance']
        await message.answer(f"✅ Казна пополнена на {amount} GALL. Новый баланс казны: {new_balance} GALL.")
    except ValueError:
        await message.answer("Неверная сумма.")

# /set_reward [сумма] (установка награды за приглашение)
@router.message(Command("set_reward"))
async def set_reward_command(message: Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer("Только администраторы могут менять награду.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /set_reward [сумма]")
        return
    try:
        reward = int(args[1])
        if reward < 0:
            await message.answer("Награда не может быть отрицательной.")
            return
        db.set_reward(message.chat.id, reward)
        await message.answer(f"✅ Награда за приглашение установлена: {reward} GALL.")
    except ValueError:
        await message.answer("Неверная сумма.")

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


