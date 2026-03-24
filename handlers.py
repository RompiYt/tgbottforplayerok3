from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus
import sqlite3
import asyncio
from aiogram.types import FSInputFile

from config import *
import database as db
import keyboards as kb

roulette_bets = {}  # chat_id: [ставки]
last_spin_time = {}  # chat_id: timestamp
roulette_history = {}  # chat_id: [результаты]
last_user_bets = {}  # user_id: (chat_id, bet_data)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    user_id = message.from_user.id

    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, message.from_user.username)
        # 🎯 ПРИГЛАШЕНИЕ
        if len(args) > 1:
            try:
                inviter_id = int(args[1])

                if inviter_id != user_id:
                    added = db.add_invite(user_id, inviter_id)

                    if added:
                        # начисляем награду
                        reward = 1000  # дефолт (можно из казны)

                        db.update_balance(inviter_id, reward, "Приглашение")

                        await message.answer(
                            f"🎉 Вас пригласил пользователь!\n"
                            f"Пригласивший получил {reward} GALL"
                        )

            except:
                pass

    await message.answer(
        "Привет 👋 Я GALL! 💎\n\n"
        "💥 Скоротай время в мире азарта и крутых игр. Прокачивай свой скилл, соревнуйся с друзьями или просто испытай удачу — скучно точно не будет! ⚡️\n\n"
        "🤔 Итак, с чего начнем?\n"
        "• Жми 🎲 Игры, чтобы сорвать куш\n"
        "• Либо просто пиши /game и врывайся в топ! 🏆\n\n"
        "❓ Остались вопросы? — 👉 /help 😏",
        reply_markup=kb.main_menu
    )
    
@router.message(F.text.lower() == "б")
async def balance_short(message: Message):
    balance = db.get_balance(message.from_user.id)
    await message.answer(f"💰 Ваш баланс: {balance} GALL")
    
@router.message(F.text == "чаты")
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

@router.message(F.text == "бонус")
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

@router.message(F.text == "профиль")
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

@router.message(F.text == "команды")
async def commands_button(message: Message):
    await message.answer(
        "💎 Полный список команд HARD\n\n"
        "💳 Твой кошелек:\n"
        "├ б — чекнуть счёт\n"
        "├ профиль — всё о твоём статусе\n"
        "└ история — логи твоих побед и трат\n\n"
        "💸 Переводы и бонусы:\n"
        "├ п [сумма] — скинуть кэш (ответом)\n"
        "├ п [ID] [сумма] — перевод по ID\n"
        "├ промо [код] — забрать халяву\n"
        "└ топ — заглянуть в список Forbes\n\n"
        "🚀 Для владельцев групп:\n"
        "├ /games — ⚙️ настройка игр (вкл/выкл)\n"
        "├ казна [сумма] — пополнить общий фонд\n"
        "├ казна — проверить баланс фонда группы\n"
        "├ награда [сумма] — выдать бонус из казны\n"
        "└ реф - реферальная ссылка"
    )

@router.message(F.text == "игры")
async def games_button(message: Message):
    await message.answer(
        "🎰 Игровой зал GALL\n━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в элитный клуб! Выбирай свой стиль игры и начинай побеждать.\n\n"
        "👇 Выбери категорию:",
        reply_markup=kb.games_category_menu
    )

@router.callback_query(F.data == "cat_dynamic")
async def cat_dynamic(callback: CallbackQuery):
    text = (
        "🎲 ДИНАМИЧЕСКИЕ ИГРЫ\n\n"
        "Здесь важен каждый ход. Просчитывай риски и забирай куш!\n\n"
        "🔴 Рулетка\n"
        "L Ставка: [сумма] [тип]\n"
        "L Команды: го, отмена, повторить, удвоить, лог\n\n"
        "⚫ Мины (Mines)\n"
        "L Команда: мин [ставка] [бомбы]\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "cat_static")
async def cat_static(callback: CallbackQuery):
    text = (
        "💎 СТАТИЧЕСКИЕ ИГРЫ\n\n"
        "Испытай удачу в один клик. Моментальный результат! 💎\n\n"
        "🔴 Слот-машина\n"
        "L Команда: спин [ставка]\n\n"
        "🟢 Кости (Dice)\n"
        "L Команда: кубик [ставка]\n\n"
        "🟣 Дартс\n"
        "L Команда: дартс [ставка]\n\n"
        "🟤 Баскетбол\n"
        "L Команда: баскет [ставка]\n\n"
        "🟥 Футбол\n"
        "L Команда: футбол [ставка] [режим]\n\n"
        "---\n\n"
        "Назад в меню"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
    ]))
    await callback.answer()

@router.message(F.text == "донат")
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
        "├ бонус — получить бонус\n"
        "├ профиль — всё о твоём статусе,наличии валюты\n"
        "└ история — логи твоих побед и трат\n\n"
        "💸 Переводы и бонусы:\n"
        "├ п [сумма] — скинуть кэш (ответом)\n"
        "├ п [ID] [сумма] — перевод по ID\n"
        "├ промо [код] — забрать халяву\n"
        "└ топ — заглянуть в список Forbes\n\n"
        "🚀 Для владельцев групп:\n"
        "Хочешь привлечь игроков в свой чат? Используй казну!\n"
        "├ /games — ⚙️ настройка игр (вкл/выкл)\n"
        "├ казна — проверить баланс фонда группы\n"
        "├ награда [сумма] — выдать бонус из казны\n"
        "├ депозит [сумма] — пополнить казну\n"
        "└ /set_reward [сумма] — установить награду за приглашение"
    )
    await message.answer(text)

# /game
@router.message(Command("game"))
async def game_command(message: Message):
    # Перенаправляем в игровой зал
    await games_button(message)

# /history
@router.message(F.text.lower() == "история")
async def history_text(message: Message):
    await history_command(message)
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
@router.message(F.text.lower() == "топ")
async def top_text(message: Message):
    await top_command(message)
    top_users = db.get_top_users(10)  # возвращает список (username, balance)
    if not top_users:
        await message.answer("Нет пользователей в рейтинге.")
        return
    text = "🏆 Топ-10 игроков по балансу:\n\n"
    for i, (username, balance) in enumerate(top_users, 1):
        name = username if username else "Аноним"
        text += f"{i}. {name} — {balance} GALL\n"
    await message.answer(text)
    
@router.message(F.text.lower().startswith("п "))
async def transfer_text(message: Message):
    await transfer_command(message)
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

@router.message(F.text.lower().startswith("промо"))
async def promo_text(message: Message):
    await promo_command(message)
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

@router.message(F.text.lower().startswith("казна"))
async def treasury_text(message: Message):
    await treasury_info(message)
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

@router.message(F.text.lower().startswith("награда"))
async def reward_text(message: Message):
    await give_reward(message)
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

@router.message(F.text.lower().startswith("депозит"))
async def deposit_text(message: Message):
    await deposit_treasury(message)
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


@router.message(F.text.startswith("кубик"))
async def dice_modes(message: Message):

    args = message.text.lower().split()

    # 👉 подсказка
    if len(args) == 1:
        return await message.answer(
            "🎲 Кубы\n\n"
            "Режимы:\n"
            "• чет / нечет (x2)\n"
            "• больше N\n"
            "• меньше N\n"
            "• числа (x5.5)\n\n"
            "Пример:\n"
            "кубы 1000 больше 3"
        )

    if len(args) < 3:
        return await message.answer("🎲 кубик [ставка] [режим]")

    bet = int(args[1])
    user_id = message.from_user.id

    if db.get_balance(user_id) < bet:
        return await message.answer("❌ Недостаточно средств")

    mode = args[2:]

    # 🚫 ограничения
    if mode[0] == "больше":
        num = int(mode[1])
        if num <= 0 or num >= 6:
            return await message.answer("❌ Можно писать больше только от 1 до 5")

    if mode[0] == "меньше":
        num = int(mode[1])
        if num <= 1 or num >= 7:
            return await message.answer("❌ Можно писать меньше только от 2 до 6")

    db.update_balance(user_id, -bet, "Кубик")

    msg = await message.answer_dice(emoji="🎲")
    value = msg.dice.value

    await asyncio.sleep(4)

    win = 0
    result_text = f"🎲 Выпало: {value}"

    # 🎯 ЧЕТ / НЕЧЕТ
    if mode[0] == "чет":
        result_text = "🔢 ЧЕТНОЕ" if value % 2 == 0 else "🔢 НЕЧЕТНОЕ"
        if value % 2 == 0:
            win = bet * 2

    elif mode[0] == "нечет":
        result_text = "🔢 НЕЧЕТНОЕ" if value % 2 == 1 else "🔢 ЧЕТНОЕ"
        if value % 2 == 1:
            win = bet * 2

    # 📈 БОЛЬШЕ
    elif mode[0] == "больше":
        num = int(mode[1])

        # особый x3
        if num == 5 and value == 6:
            win = bet * 3

        elif value > num:
            if num == 1:
                win = int(bet * 1.2)
            elif num == 2:
                win = int(bet * 1.4)
            elif num == 3:
                win = int(bet * 1.5)
            elif num == 4:
                win = int(bet * 1.3)
            elif num == 5:
                win = int(bet * 1.2)

    # 📉 МЕНЬШЕ
    elif mode[0] == "меньше":
        num = int(mode[1])

        # особый x3
        if num == 2 and value == 1:
            win = bet * 3

        elif value < num:
            if num == 6:
                win = int(bet * 1.2)
            elif num == 5:
                win = int(bet * 1.4)
            elif num == 4:
                win = int(bet * 1.5)
            elif num == 3:
                win = int(bet * 1.3)
            elif num == 2:
                win = int(bet * 1.2)

    # 🎯 ЧИСЛА
    else:
        numbers = list(map(int, mode))
        result_text = f"🎯 ЧИСЛО {value}"
        if value in numbers:
            coef = 5.5 / len(numbers)
            win = int(bet * coef)

    if win:
        db.update_balance(user_id, win, "Кубик выигрыш")

    await message.answer(
        f"{result_text}\n"
        f"{'✅ Выигрыш: ' + str(win) if win else '❌ Проигрыш'}"
    )

@router.message(F.text.startswith("дартс"))
async def darts_modes(message: Message):

    args = message.text.lower().split()

    # 👉 подсказка
    if len(args) == 1:
        return await message.answer(
            "🎯 Дартс\n\n"
            "Режимы:\n"
            "• центр\n"
            "• мимо\n"
            "• кр\n"
            "• бел\n"
            "• обычный\n\n"
            "Пример:\n"
            "дартс 1000\n"
            "дартс 1000 центр"
        )

    bet = int(args[1])
    mode = args[2] if len(args) > 2 else "обычный"
    user_id = message.from_user.id

    if db.get_balance(user_id) < bet:
        return await message.answer("❌ Недостаточно средств")

    db.update_balance(user_id, -bet, "Дартс")

    msg = await message.answer_dice(emoji="🎯")
    value = msg.dice.value

    await asyncio.sleep(4)

    win = 0

    # результат
    if value == 6:
        result = "🎯 ЦЕНТР"
    elif value >= 4:
        result = "🟡 РЯДОМ"
    elif value == 3:
        result = "⚪ ДАЛЕКО"
    else:
        result = "❌ МИМО"

    # 🎯 ОБЫЧНЫЙ РЕЖИМ
    if mode == "обычный":
        if value == 6:
            win = bet * 3
        elif value >= 4:
            win = bet * 2

    # 🎯 СТАРЫЕ РЕЖИМЫ
    elif mode == "центр" and value == 6:
        win = bet * 2

    elif mode == "мимо" and value <= 2:
        win = bet * 2

    elif mode == "кр" and value >= 4:
        win = bet * 2

    elif mode == "бел" and value == 3:
        win = bet * 2

    if win:
        db.update_balance(user_id, win, "Дартс выигрыш")

    await message.answer(
        f"{result}\n"
        f"💰 Ставка: {bet}\n"
        f"{'✅ Выигрыш: ' + str(win) if win else '❌ Проигрыш'}"
    )

@router.message(F.text.startswith("баскет"))
async def basket_modes(message: Message):

    args = message.text.lower().split()

    # 👉 если просто "баскет"
    if len(args) == 1:
        return await message.answer(
            "🏀 Баскет\n\n"
            "Режимы:\n"
            "• классика (x2 попадание, x3 чисто)\n"
            "• гол (x1.9)\n"
            "• чисто (x3.5)\n"
            "• мимо (x1.5)\n\n"
            "Пример:\n"
            "баскет 1000\n"
            "баскет 1000 чисто"
        )

    if len(args) < 2:
        return await message.answer("🏀 баскет [ставка] [режим]")

    bet = int(args[1])
    mode = args[2] if len(args) > 2 else "классика"
    user_id = message.from_user.id

    if db.get_balance(user_id) < bet:
        return await message.answer("❌ Недостаточно средств")

    # списываем ставку
    db.update_balance(user_id, -bet, "Баскет")

    # 🎲 анимация
    msg = await message.answer_dice(emoji="🏀")
    value = msg.dice.value

    await asyncio.sleep(4)

    win = 0

    # определяем результат
    if value == 6:
        result = "💦 ЧИСТО"
    elif value >= 4:
        result = "🏀 ПОПАЛ"
    else:
        result = "❌ МИМО"

    # 🎯 ЛОГИКА СТАВОК

    # классика
    if mode == "классика":
        if value == 6:
            win = bet * 3
        elif value >= 4:
            win = bet * 2

    # спец
    elif mode == "гол" and value >= 4:
        win = int(bet * 1.9)

    elif mode == "чисто" and value == 6:
        win = int(bet * 3.5)

    elif mode == "мимо" and value < 4:
        win = int(bet * 1.5)

    if win:
        db.update_balance(user_id, win, "Баскет выигрыш")

    await message.answer(
        f"{result}\n"
        f"💰 Ставка: {bet}\n"
        f"{'✅ Выигрыш: ' + str(win) if win else '❌ Проигрыш'}"
    )

@router.message(F.text.startswith("футбол"))
async def football_modes(message: Message):
    args = message.text.lower().split()

    # 👉 если просто "футбол"
    if len(args) == 1:
        return await message.answer(
            "⚽ Футбол\n\n"
            "Режимы:\n"
            "• девятка (x3)\n"
            "• гол (x2)\n"
            "• любой (x1.5)\n"
            "• промах (x2)\n\n"
            "Пример: футбол 1000 гол"
        )

    if len(args) < 3:
        return await message.answer("⚽ футбол [ставка] [режим]")

    bet = int(args[1])
    mode = args[2]
    user_id = message.from_user.id

    if db.get_balance(user_id) < bet:
        return await message.answer("❌ Недостаточно средств")

    db.update_balance(user_id, -bet, "Футбол")

    msg = await message.answer_dice(emoji="⚽")
    value = msg.dice.value

    await asyncio.sleep(4)

    win = 0

    # ЛОГИКА
    if value == 6:
        result = "🔥 ДЕВЯТКА"
        if mode == "девятка":
            win = bet * 3
        elif mode == "гол":
            win = bet * 2
        elif mode == "любой":
            win = int(bet * 1.5)

    elif value >= 4:
        result = "⚽ ГОЛ"
        if mode in ["гол", "любой"]:
            win = bet * 2 if mode == "гол" else int(bet * 1.5)

    else:
        result = "❌ ПРОМАХ"
        if mode == "промах":
            win = bet * 2

    if win:
        db.update_balance(user_id, win, "Футбол выигрыш")

    await message.answer(
        f"{result}\n"
        f"💰 Ставка: {bet}\n"
        f"{'✅ Выигрыш: ' + str(win) if win else '❌ Проигрыш'}"
    )
    
@router.message(F.text.lower() == "го")
async def spin_roulette(message: Message):
    import random
    import asyncio
    import time
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    chat_id = message.chat.id

    # ⏱ анти-спам (20 сек)
    now = time.time()
    if chat_id in last_spin_time and now - last_spin_time[chat_id] < 20:
        return await message.answer("⏳ Подожди немного перед следующим спином")

    last_spin_time[chat_id] = now

    # ❌ нет ставок
    if chat_id not in roulette_bets or not roulette_bets[chat_id]:
        return await message.answer("❌ Нет ставок")

    # 🎰 отправляем гиф
    video = FSInputFile("roulette.gif.mp4")
    await message.answer_video(video)

    # ⏳ задержка
    await asyncio.sleep(5)

    # 🎯 результат
    number = random.randint(0, 36)

    red_numbers = {
        1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36
    }

    if number == 0:
        color = "🟢"
        color_name = "zero"
    elif number in red_numbers:
        color = "🔴"
        color_name = "к"
    else:
        color = "⚫"
        color_name = "ч"

    result_text = f"🎰 Рулетка: {number} {color}\n\n"

    # 🎯 обработка всех ставок
    for bet_data in roulette_bets[chat_id]:
        user = bet_data["user"]
        user_id = bet_data["user_id"]
        bet = bet_data["bet"]
        items = bet_data["items"]

        total_win = 0

        for item in items:
            win = 0

            # 🎯 число
            if item.isdigit():
                if int(item) == number:
                    win = bet * 36

            # 🎯 диапазон
            elif "-" in item:
                try:
                    start, end = map(int, item.split("-"))
                    if start <= number <= end:
                        count = end - start + 1
                        coef = 36 / count
                        win = int(bet * coef)
                except:
                    pass

            # 🎯 чет / нечет
            elif item == "чет" and number != 0:
                if number % 2 == 0:
                    win = bet * 2

            elif item == "нечет" and number != 0:
                if number % 2 == 1:
                    win = bet * 2

            # 🎯 цвет
            elif item in ["к", "красный"]:
                if color_name == "к":
                    win = bet * 2

            elif item in ["ч", "черный"]:
                if color_name == "ч":
                    win = bet * 2

            total_win += win

        # 💰 начисление
        if total_win > 0:
            db.update_balance(user_id, total_win, "Рулетка выигрыш")
            result_text += f"✅ {user} выиграл {total_win}\n"
        else:
            result_text += f"❌ {user} проиграл\n"

    # 📊 сохраняем лог
    if chat_id not in roulette_history:
        roulette_history[chat_id] = []

    roulette_history[chat_id].append({
        "number": number,
        "color": color
    })

    roulette_history[chat_id] = roulette_history[chat_id][-7:]

    # 🔘 кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔁 Повторить", callback_data="repeat_bet"),
            InlineKeyboardButton(text="💥 Удвоить", callback_data="double_bet")
        ]
    ])

    # 🎰 итог
    await message.answer(result_text, reply_markup=keyboard)

    # 🧹 очистка ставок
    roulette_bets[chat_id] = []

@router.message(F.text.lower() == "реф")
async def ref_link(message: Message):
    bot_username = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={message.from_user.id}"

    await message.answer(
        f"🔗 Ваша реферальная ссылка:\n{link}\n\n"
        "👥 Приглашай друзей и получай GALL!"
    )

@router.message(F.text.lower() == "лог")
async def roulette_log(message: Message):
    chat_id = message.chat.id

    if chat_id not in roulette_history or not roulette_history[chat_id]:
        return await message.answer("❌ Пока нет результатов")

    text = "📊 Последние результаты:\n\n"

    for item in reversed(roulette_history[chat_id]):
        text += f"{item['color']} {item['number']}  "

    await message.answer(text)

@router.callback_query(F.data == "repeat_bet")
async def repeat_bet(callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in last_user_bets:
        return await callback.answer("❌ Нет предыдущей ставки", show_alert=True)

    data = last_user_bets[user_id]

    chat_id = data["chat_id"]
    bet = data["bet"]
    items = data["items"]

    if db.get_balance(user_id) < bet:
        return await callback.answer("❌ Недостаточно средств", show_alert=True)

    db.update_balance(user_id, -bet, "Рулетка повтор")

    roulette_bets.setdefault(chat_id, []).append({
        "user": callback.from_user.full_name,
        "user_id": user_id,
        "bet": bet,
        "items": items
    })

    await callback.answer("✅ Ставка повторена")

@router.message(F.text.regexp(r"^\d+"))
async def collect_bets(message: Message):

    text = message.text.lower().split()

    if not text or not text[0].isdigit():
        return

    bet = int(text[0])
    items = text[1:]

    if not items:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    if db.get_balance(user_id) < bet:
        return await message.answer("❌ Недостаточно средств")

    db.update_balance(user_id, -bet, "Рулетка ставка")

    if chat_id not in roulette_bets:
        roulette_bets[chat_id] = []

    roulette_bets[chat_id].append({
        "user": message.from_user.full_name,
        "user_id": user_id,
        "bet": bet,
        "items": items
    })

    # 🧾 вывод списка ставок
    text_out = "📊 Ставки:\n\n"

    for b in roulette_bets[chat_id]:
        text_out += f"{b['user']} — {b['bet']} на {' '.join(b['items'])}\n"

    await message.answer(text_out)


@router.callback_query(F.data == "double_bet")
async def double_bet(callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in last_user_bets:
        return await callback.answer("❌ Нет предыдущей ставки", show_alert=True)

    data = last_user_bets[user_id]

    chat_id = data["chat_id"]
    bet = data["bet"] * 2
    items = data["items"]

    if db.get_balance(user_id) < bet:
        return await callback.answer("❌ Недостаточно средств", show_alert=True)

    db.update_balance(user_id, -bet, "Рулетка удвоение")

    roulette_bets.setdefault(chat_id, []).append({
        "user": callback.from_user.full_name,
        "user_id": user_id,
        "bet": bet,
        "items": items
    })

    # обновляем сохранённую ставку
    last_user_bets[user_id]["bet"] = bet

    await callback.answer("💥 Ставка удвоена")
