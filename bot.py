import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Union, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging


API_TOKEN = '8685749642:AAEV_g48v9b8wWBPycQPii3Mq9lvh-2UxKA'  
BONUS_AMOUNT = 2500
BONUS_COOLDOWN = 24 
START_BALANCE = 0

# Пересчитанные цены: 10 звезд = 750,000 Gall
DONATION_PLANS = {
    10: {"gall": 750000, "bonus": 0},
    50: {"gall": 3750000, "bonus": 0},      # 750,000 * 5
    100: {"gall": 7500000, "bonus": 5},     # 750,000 * 10 + 5%
    200: {"gall": 15000000, "bonus": 10},   # 750,000 * 20 + 10%
    500: {"gall": 37500000, "bonus": 25},   # 750,000 * 50 + 25%
    1000: {"gall": 75000000, "bonus": 50}   # 750,000 * 100 + 50%
}
MAX_STARS_PER_INVOICE = 2500  


MINES_GRID_SIZE = 25
MINES_COUNT = 5
MINES_MULTIPLIERS = {
    1: 1.3, 2: 1.8, 3: 2.3, 4: 3.0, 5: 4.0,
    6: 6.5, 7: 9.0, 8: 12.0, 9: 19.0, 10: 25.0,
    11: 40.0, 12: 50.0, 13: 70.0, 14: 125.0, 15: 300.0,
    16: 700.0, 17: 1200.0, 18: 3500.0, 19: 7000.0, 20: 20000.0
}

ROULETTE_NUMBERS = list(range(0, 37))
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
ZERO = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect('game_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    total_donated INTEGER DEFAULT 0,
    last_bonus TIMESTAMP,
    chat_id INTEGER,
    invited_by INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS chat_treasury (
    chat_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    invite_reward INTEGER DEFAULT 1000
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    stars_amount INTEGER,
    gall_received INTEGER,
    bonus_percent INTEGER,
    telegram_payment_charge_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

class GameStates(StatesGroup):
    basketball_bet = State()
    darts_bet = State()
    mines_game = State()
    roulette_bet = State()

class TreasuryStates(StatesGroup):
    waiting_reward_amount = State()

def get_user(user_id: int, username: str = None, chat_id: int = None, invited_by: int = None):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, balance, total_donated, last_bonus, chat_id, invited_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, START_BALANCE, 0, None, chat_id, invited_by))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    return user

def update_balance(user_id: int, amount: int):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def get_balance(user_id: int) -> int:
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def get_chat_treasury(chat_id: int):
    cursor.execute('SELECT * FROM chat_treasury WHERE chat_id = ?', (chat_id,))
    treasury = cursor.fetchone()
    if not treasury:
        cursor.execute('INSERT INTO chat_treasury (chat_id) VALUES (?)', (chat_id,))
        conn.commit()
        cursor.execute('SELECT * FROM chat_treasury WHERE chat_id = ?', (chat_id,))
        treasury = cursor.fetchone()
    return treasury


@dp.message(Command('donate'))
async def cmd_donate(message: Message):
    """Показать меню донатов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ 10 звёзд - {DONATION_PLANS[10]['gall']:,} Gall".replace(',', ' '), 
                              callback_data="donate_10")],
        [InlineKeyboardButton(text=f"⭐ 50 звёзд - {DONATION_PLANS[50]['gall']:,} Gall".replace(',', ' '), 
                              callback_data="donate_50")],
        [InlineKeyboardButton(text=f"⭐ 100 звёзд - {DONATION_PLANS[100]['gall']:,} Gall +5%".replace(',', ' '), 
                              callback_data="donate_100")],
        [InlineKeyboardButton(text=f"⭐ 200 звёзд - {DONATION_PLANS[200]['gall']:,} Gall +10%".replace(',', ' '), 
                              callback_data="donate_200")],
        [InlineKeyboardButton(text=f"⭐ 500 звёзд - {DONATION_PLANS[500]['gall']:,} Gall +25%".replace(',', ' '), 
                              callback_data="donate_500")],
        [InlineKeyboardButton(text=f"⭐ 1000 звёзд - {DONATION_PLANS[1000]['gall']:,} Gall +50%".replace(',', ' '), 
                              callback_data="donate_1000")],
        [InlineKeyboardButton(text="❓ Помощь по донатам", callback_data="donate_help")]
    ])
    
    await message.reply(
        "✨ Поддержите проект звёздами Telegram!\n\n"
        "За каждое пожертвование вы получаете Gall на игровой счёт.\n"
        "Чем больше сумма - тем выше бонус к курсу!\n\n"
        "Выберите пакет:", 
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('donate_'))
async def process_donate_callback(callback: CallbackQuery):
    if callback.data == "donate_help":
        await callback.message.edit_text(
            "❓ Как это работает:\n\n"
            "1. Вы выбираете пакет и оплачиваете звёздами Telegram\n"
            "2. Звёзды списываются с вашего аккаунта\n"
            "3. На игровой счёт начисляются Gall с бонусом\n\n"
            "Бонусы за пакеты:\n"
            "• 10 ⭐ → 750,000 Gall (без бонуса)\n"
            "• 50 ⭐ → 3,750,000 Gall (без бонуса)\n"
            "• 100 ⭐ → 7,500,000 Gall +5% (7,875,000 Gall)\n"
            "• 200 ⭐ → 15,000,000 Gall +10% (16,500,000 Gall)\n"
            "• 500 ⭐ → 37,500,000 Gall +25% (46,875,000 Gall)\n"
            "• 1000 ⭐ → 75,000,000 Gall +50% (112,500,000 Gall)\n\n"
            "После оплаты средства зачисляются автоматически!"
        )
        await callback.answer()
        return
    
    stars = int(callback.data.split('_')[1])
    plan = DONATION_PLANS[stars]
    
    base_gall = plan["gall"]
    bonus_percent = plan["bonus"]
    total_gall = base_gall * (100 + bonus_percent) // 100
    
    prices = [LabeledPrice(label="XTR", amount=stars)]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Оплатить {stars} звёзд", pay=True)],
        [InlineKeyboardButton(text="◀ Назад", callback_data="donate_back")]
    ])
    
    await callback.message.answer_invoice(
        title=f"Пополнение счёта на {stars} ⭐",
        description=(
            f"Пакет: {stars} звёзд\n"
            f"База: {base_gall:,} Gall\n".replace(',', ' ') +
            (f"Бонус: +{bonus_percent}% ({total_gall - base_gall:,} Gall)\n".replace(',', ' ') if bonus_percent > 0 else "") +
            f"ИТОГО: {total_gall:,} Gall".replace(',', ' ')
        ),
        prices=prices,
        provider_token="", 
        payload=f"donate_{stars}_{total_gall}", 
        currency="XTR",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "donate_back")
async def donate_back(callback: CallbackQuery):
    await cmd_donate(callback.message)
    await callback.answer()

@dp.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    if payload.startswith("donate_"):
        try:
            _, stars_str, gall_str = payload.split('_')
            stars = int(stars_str)
            total_gall = int(gall_str)
        except ValueError:
            await message.reply("Ошибка обработки платежа. Обратитесь к администратору.")
            return
        
        user_id = message.from_user.id
        username = message.from_user.username
        plan = DONATION_PLANS.get(stars, {"bonus": 0})
        bonus_percent = plan["bonus"]
        
        update_balance(user_id, total_gall)
        cursor.execute('UPDATE users SET total_donated = total_donated + ? WHERE user_id = ?', 
                      (stars, user_id))
        cursor.execute('''
            INSERT INTO donations (user_id, stars_amount, gall_received, bonus_percent, telegram_payment_charge_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, stars, total_gall, bonus_percent, payment.telegram_payment_charge_id))
        conn.commit()
        
        balance = get_balance(user_id)
        await message.reply(
            f"✅ Оплата прошла успешно!\n\n"
            f"⭐ Звёзд: {stars}\n"
            f"🎁 Получено Gall: {total_gall:,}\n".replace(',', ' ') +
            (f"📈 Бонус: +{bonus_percent}%\n" if bonus_percent > 0 else "") +
            f"💰 Текущий баланс: {balance:,} Gall".replace(',', ' ')
        )

@dp.message(Command('mydonations'))
async def cmd_my_donations(message: Message):
    user_id = message.from_user.id
    
    cursor.execute('''
        SELECT stars_amount, gall_received, bonus_percent, timestamp 
        FROM donations 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (user_id,))
    
    donations = cursor.fetchall()
    
    if not donations:
        await message.reply("У вас пока нет донатов. Используйте /donate чтобы поддержать проект!")
        return

    cursor.execute('''
        SELECT SUM(stars_amount), SUM(gall_received) FROM donations WHERE user_id = ?
    ''', (user_id,))
    total_stats = cursor.fetchone()
    total_stars = total_stats[0] or 0
    total_gall = total_stats[1] or 0
    
    text = f"📊 Ваши донаты (всего: {total_stars} ⭐ → {total_gall:,} Gall)\n\n".replace(',', ' ')
    text += "Последние 10 операций:\n"
    
    for stars, gall, bonus, timestamp in donations:
        date = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y")
        bonus_text = f" (+{bonus}%)" if bonus > 0 else ""
        text += f"• {date}: {stars} ⭐ → {gall:,} Gall{bonus_text}\n".replace(',', ' ')
    
    await message.reply(text)


@dp.message(Command('start'))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    
    args = message.text.split()
    invited_by = None
    if len(args) > 1 and args[1].isdigit():
        invited_by = int(args[1])
        if invited_by != user_id:
            update_balance(invited_by, 500)
            await bot.send_message(invited_by, f"🎉 По вашей ссылке зарегистрировался новый игрок! Вам начислено 500 Gall")
    
    get_user(user_id, username, chat_id, invited_by)
    
    await message.reply(
        "🎮 Добро пожаловать в игрового бота!\n\n"
        "Доступные команды:\n"
        "/balance или б - проверить баланс\n"
        "/bonus или бонус - получить ежедневный бонус\n"
        "/top или топ - топ игроков чата\n"
        "/treasury или казна - информация о казне чата\n"
        "/donate - пополнить баланс звёздами Telegram\n"
        "/mydonations - история донатов\n"
        "Подключить казну - создать казну в этом чате\n\n"
        "🎲 Игры:\n"
        "/basketball - Баскетбол\n"
        "/darts - Дартс\n"
        "/mines - Мины\n"
        "/roulette - Рулетка"
    )

@dp.message(F.text.lower().in_(['б', '/balance', 'баланс']))
async def cmd_balance(message: Message):
    user = get_user(message.from_user.id)
    balance = user[2]
    total_donated = user[4]  
    
    text = f"💰 Ваш баланс: {balance} Gall"
    if total_donated > 0:
        text += f"\n⭐ Всего задоначено: {total_donated} звёзд"
    
    await message.reply(text)

@dp.message(Command(commands=['bonus', 'бонус']))
async def cmd_bonus(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    last_bonus = user[3]
    if last_bonus:
        last_bonus_time = datetime.fromisoformat(last_bonus)
        next_bonus_time = last_bonus_time + timedelta(hours=BONUS_COOLDOWN)
        if datetime.now() < next_bonus_time:
            remaining = next_bonus_time - datetime.now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await message.reply(f"⏳ Бонус будет доступен через {hours}ч {minutes}м")
            return
    
    # Обновляем баланс и время последнего бонуса
    cursor.execute('UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?',
                   (BONUS_AMOUNT, datetime.now().isoformat(), user_id))
    conn.commit()
    
    await message.reply(f"🎁 Вы получили бонус {BONUS_AMOUNT} Gall!")

@dp.message(F.text.lower().in_(['топ', '/top']))
async def cmd_top(message: Message):
    chat_id = message.chat.id
    cursor.execute('''
        SELECT username, balance FROM users 
        WHERE chat_id = ? 
        ORDER BY balance DESC 
        LIMIT 10
    ''', (chat_id,))
    top_users = cursor.fetchall()
    
    if not top_users:
        await message.reply("В этом чате пока нет игроков")
        return
    
    text = "🏆 ТОП-10 игроков чата:\n\n"
    for i, (username, balance) in enumerate(top_users, 1):
        name = username if username else f"Игрок{i}"
        text += f"{i}. @{name} - {balance} Gall\n"
    
    await message.reply(text)

@dp.message(F.text.lower() == 'подключить казну')
async def cmd_connect_treasury(message: Message):
    chat_id = message.chat.id
    if message.chat.type == 'private':
        await message.reply("Казну можно подключить только в групповом чате!")
        return
    
    get_chat_treasury(chat_id)
    await message.reply(
        "✅ Казна успешно подключена!\n\n"
        "Команды для казны:\n"
        "/treasury - информация о казне\n"
        "/deposit [сумма] - пополнить казну\n"
        "/set_reward [сумма] - установить награду за приглашение (1000-5000)"
    )

@dp.message(F.text.lower().in_(['казна', '/treasury']))
async def cmd_treasury(message: Message):
    chat_id = message.chat.id
    treasury = get_chat_treasury(chat_id)
    
    text = f"🏦 Казна чата:\n"
    text += f"Баланс: {treasury[1]} Gall\n"
    text += f"Награда за приглашение: {treasury[2]} Gall\n\n"
    text += "Чтобы пополнить: /deposit [сумма]\n"
    text += "Изменить награду: /set_reward [сумма]"
    
    await message.reply(text)

@dp.message(Command('deposit'))
async def cmd_deposit(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply("Использование: /deposit [сумма]")
        return
    
    amount = int(args[1])
    if amount <= 0:
        await message.reply("Сумма должна быть положительной")
        return
    
    user_balance = get_balance(user_id)
    if user_balance < amount:
        await message.reply("Недостаточно средств!")
        return
    
    update_balance(user_id, -amount)
    
    cursor.execute('UPDATE chat_treasury SET balance = balance + ? WHERE chat_id = ?', (amount, chat_id))
    conn.commit()
    
    await message.reply(f"✅ Вы пополнили казну на {amount} Gall")

@dp.message(Command('set_reward'))
async def cmd_set_reward(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    chat_member = await bot.get_chat_member(chat_id, user_id)
    if chat_member.status not in ('creator', 'administrator'):
        await message.reply("Только администраторы могут изменять награду")
        return
    
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply("Использование: /set_reward [сумма от 1000 до 5000]")
        return
    
    amount = int(args[1])
    if amount < 1000 or amount > 5000:
        await message.reply("Сумма должна быть от 1000 до 5000 Gall")
        return
    
    cursor.execute('UPDATE chat_treasury SET invite_reward = ? WHERE chat_id = ?', (amount, chat_id))
    conn.commit()
    
    await message.reply(f"✅ Награда за приглашение установлена: {amount} Gall")

# ==================== Баскетбол ====================
@dp.message(Command('basketball'))
async def cmd_basketball(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if balance < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏀 Обычный (x2 если попадание)", callback_data="bb_normal")],
        [InlineKeyboardButton(text="💦 Сплеш (x3 если чистое попадание)", callback_data="bb_splash")],
        [InlineKeyboardButton(text="🎯 Мимо (x2 если промах)", callback_data="bb_miss")]
    ])
    
    await message.reply("Выберите тип ставки:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('bb_'))
async def process_basketball_bet(callback: CallbackQuery, state: FSMContext):
    bet_type = callback.data
    await state.update_data(bet_type=bet_type)
    await state.set_state(GameStates.basketball_bet)
    
    try:
        await callback.message.edit_text(
            "Введите сумму ставки (минимум 10 Gall):\n"
            "Или отправьте 0 для отмены"
        )
    except Exception:
        pass
    await callback.answer()

@dp.message(GameStates.basketball_bet)
async def process_basketball_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("Пожалуйста, введите число")
        return
    
    amount = int(message.text)
    if amount == 0:
        await state.clear()
        await message.reply("Игра отменена")
        return
    
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if amount < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    if amount > balance:
        await message.reply("Недостаточно средств!")
        return
    
    data = await state.get_data()
    bet_type = data['bet_type']
    
    update_balance(user_id, -amount)

    outcomes = {
        'bb_normal': {  
            'win': random.random() < 0.5,
            'multiplier': 2
        },
        'bb_splash': {  
            'win': random.random() < 0.3,  
            'multiplier': 3
        },
        'bb_miss': {
            'win': random.random() < 0.5,  
            'multiplier': 2,
            'invert': True 
        }
    }
    
    outcome = outcomes[bet_type]
    
    if 'invert' in outcome:
        win = not outcome['win']
    else:
        win = outcome['win']
    
    if win:
        winnings = amount * outcome['multiplier']
        update_balance(user_id, winnings)
        result_text = f"✅ Вы выиграли {winnings} Gall!"
    else:
        result_text = f"❌ Вы проиграли {amount} Gall"
    
    balance = get_balance(user_id)
    result_text += f"\n💰 Текущий баланс: {balance} Gall"
    
    await state.clear()
    await message.reply(result_text)

# ==================== Дартс ====================
@dp.message(Command('darts'))
async def cmd_darts(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if balance < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 В центр (x5)", callback_data="darts_center")],
        [InlineKeyboardButton(text="🎯 Рядом с центром (x2)", callback_data="darts_near")],
        [InlineKeyboardButton(text="🎯 Мимо (x2 если мимо)", callback_data="darts_miss")]
    ])
    
    await message.reply("Выберите тип ставки:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('darts_'))
async def process_darts_bet(callback: CallbackQuery, state: FSMContext):
    bet_type = callback.data
    await state.update_data(bet_type=bet_type)
    await state.set_state(GameStates.darts_bet)
    
    try:
        await callback.message.edit_text(
            "Введите сумму ставки (минимум 10 Gall):\n"
            "Или отправьте 0 для отмены"
        )
    except Exception:
        pass
    await callback.answer()

@dp.message(GameStates.darts_bet)
async def process_darts_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("Пожалуйста, введите число")
        return
    
    amount = int(message.text)
    if amount == 0:
        await state.clear()
        await message.reply("Игра отменена")
        return
    
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if amount < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    if amount > balance:
        await message.reply("Недостаточно средств!")
        return
    
    data = await state.get_data()
    bet_type = data['bet_type']
    
    update_balance(user_id, -amount)
    
    hit = random.random()

    if bet_type == 'darts_center':  
        if hit < 0.1:  
            multiplier = 5
            win = True
        elif hit < 0.3:  
            multiplier = 2
            win = True
        else:
            win = False
            multiplier = 0
    
    elif bet_type == 'darts_near':  
        if hit < 0.2:
            multiplier = 5
            win = True
        elif hit < 0.5:
            multiplier = 2
            win = True
        else:
            win = False
            multiplier = 0
    
    else:  # darts_miss
        if hit >= 0.5:
            multiplier = 2
            win = True
        else:
            win = False
            multiplier = 0
    
    if win:
        winnings = amount * multiplier
        update_balance(user_id, winnings)
        result_text = f"✅ Вы выиграли {winnings} Gall!"
    else:
        result_text = f"❌ Вы проиграли {amount} Gall"
    
    balance = get_balance(user_id)
    result_text += f"\n💰 Текущий баланс: {balance} Gall"
    
    await state.clear()
    await message.reply(result_text)

# ==================== Мины ====================
@dp.message(Command('mines'))
async def cmd_mines(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if balance < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    await message.reply(
        "Игра Мины\n"
        "Поле 5x5, 5 бомб\n"
        "Введите сумму ставки:"
    )
    await state.set_state(GameStates.mines_game)
    await state.update_data(opened_cells=[], mines=None, bet_amount=0)

@dp.message(GameStates.mines_game)
async def process_mines_start(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("Введите число")
        return
    
    amount = int(message.text)
    if amount <= 0:
        await state.clear()
        await message.reply("Игра отменена")
        return
    
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if amount < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    if amount > balance:
        await message.reply("Недостаточно средств!")
        return
    
    update_balance(user_id, -amount)
    
    all_cells = list(range(MINES_GRID_SIZE))
    mines = random.sample(all_cells, MINES_COUNT)
    
    await state.update_data(mines=mines, bet_amount=amount, opened_cells=[])
    
    await show_mines_field(message, state)

async def show_mines_field(message: Message, state: FSMContext):
    data = await state.get_data()
    opened_cells = data['opened_cells']
    mines = data['mines']
    bet_amount = data['bet_amount']
    
    keyboard = []
    for i in range(0, MINES_GRID_SIZE, 5):
        row = []
        for j in range(5):
            cell_num = i + j
            if cell_num in opened_cells:
                if cell_num in mines:
                    text = "💣"
                else:
                    text = "✅"
            else:
                text = "⬜"
            row.append(InlineKeyboardButton(text=text, callback_data=f"mine_{cell_num}"))
        keyboard.append(row)
    
    if opened_cells:
        current_mult = MINES_MULTIPLIERS[len(opened_cells)]
        keyboard.append([InlineKeyboardButton(
            text=f"💰 Забрать {int(bet_amount * current_mult)} Gall",
            callback_data="mine_cashout"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Выйти", callback_data="mine_exit")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    current_mult = MINES_MULTIPLIERS[len(opened_cells)] if opened_cells else 1
    text = f"Мины | Ставка: {bet_amount} Gall\n"
    text += f"Открыто ячеек: {len(opened_cells)} | Множитель: x{current_mult}\n"
    text += f"Потенциальный выигрыш: {int(bet_amount * current_mult)} Gall\n\n"
    text += "Выбирайте ячейки:"
    
    await message.reply(text, reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith('mine_'))
async def process_mines_click(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    
    if action == "exit":
        await state.clear()
        try:
            await callback.message.edit_text("Игра завершена")
        except Exception:
            pass
        await callback.answer()
        return
    
    if action == "cashout":
        data = await state.get_data()
        opened_cells = data['opened_cells']
        bet_amount = data['bet_amount']
        
        if not opened_cells:
            await callback.answer("Нельзя забрать, не открыв ни одной ячейки!")
            return
        
        multiplier = MINES_MULTIPLIERS[len(opened_cells)]
        winnings = int(bet_amount * multiplier)
        
        user_id = callback.from_user.id
        update_balance(user_id, winnings)
        
        balance = get_balance(user_id)
        try:
            await callback.message.edit_text(
                f"✅ Вы забрали {winnings} Gall!\n"
                f"💰 Текущий баланс: {balance} Gall"
            )
        except Exception:
            pass
        await state.clear()
        await callback.answer()
        return
    
    try:
        cell = int(action)
    except:
        await callback.answer("Ошибка")
        return
    
    data = await state.get_data()
    opened_cells = data['opened_cells']
    mines = data['mines']
    bet_amount = data['bet_amount']
    
    if cell in opened_cells:
        await callback.answer("Эта ячейка уже открыта!")
        return
    
    opened_cells.append(cell)
    await state.update_data(opened_cells=opened_cells)
    
    if cell in mines:
        try:
            await callback.message.edit_text(
                f"💥 БАБАХ! Вы наступили на мину!\n"
                f"Вы проиграли {bet_amount} Gall"
            )
        except Exception:
            pass
        await state.clear()
        await callback.answer()
        return
    
    if len(opened_cells) >= 20:
        multiplier = MINES_MULTIPLIERS[len(opened_cells)]
        winnings = int(bet_amount * multiplier)
        
        user_id = callback.from_user.id
        update_balance(user_id, winnings)
        
        balance = get_balance(user_id)
        try:
            await callback.message.edit_text(
                f"🎉 ПОБЕДА! Вы открыли все безопасные ячейки!\n"
                f"Выигрыш: {winnings} Gall\n"
                f"💰 Текущий баланс: {balance} Gall"
            )
        except Exception:
            pass
        await state.clear()
        await callback.answer()
        return
    
    await show_mines_field(callback.message, state)
    await callback.answer()

# ==================== Рулетка ====================
@dp.message(Command('roulette'))
async def cmd_roulette(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if balance < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    await state.set_state(GameStates.roulette_bet)
    await message.reply(
        "🎰 Рулетка\n\n"
        "Вы можете ставить на:\n"
        "- Одно число (x36)\n"
        "- Диапазон (например 10-17) (x18 за 2 числа)\n"
        "- Чет/нечет (x2)\n"
        "- Красное/черное (x2)\n"
        "- Несколько чисел через пробел\n\n"
        "Введите ставку в формате:\n"
        "[сумма] [ставка]\n"
        "Пример: 100 17\n"
        "Пример: 50 красное\n"
        "Пример: 25 10-17\n"
        "Пример: 30 1 5 7 10-15\n\n"
        "Или отправьте 0 для отмены"
    )

@dp.message(GameStates.roulette_bet)
async def process_roulette_bet(message: Message, state: FSMContext):
    text = message.text.strip()
    
    if text == '0':
        await state.clear()
        await message.reply("Игра отменена")
        return
    
    parts = text.split()
    if len(parts) < 2:
        await message.reply("Неверный формат. Пример: 100 17")
        return
    
    if not parts[0].isdigit():
        await message.reply("Сумма должна быть числом")
        return
    
    amount = int(parts[0])
    if amount < 10:
        await message.reply("Минимальная ставка 10 Gall")
        return
    
    user_id = message.from_user.id
    balance = get_balance(user_id)
    
    if amount > balance:
        await message.reply("Недостаточно средств!")
        return
    
    bet_types = ' '.join(parts[1:]).lower()
    
    multiplier = 0
    bet_numbers = []
    bet_parity = None
    bet_color = None
    
    if bet_types in ['чет', 'четное', 'even']:
        multiplier = 2
        bet_parity = 'even'
    elif bet_types in ['нечет', 'нечетное', 'odd']:
        multiplier = 2
        bet_parity = 'odd'
    elif bet_types in ['красное', 'red']:
        multiplier = 2
        bet_color = 'red'
    elif bet_types in ['черное', 'black']:
        multiplier = 2
        bet_color = 'black'
    else:
        items = bet_types.split()
        numbers = set()
        
        for item in items:
            if '-' in item:
                try:
                    start, end = map(int, item.split('-'))
                    if start < 0 or end > 36 or start > end:
                        raise ValueError
                    for num in range(start, end + 1):
                        numbers.add(num)
                except:
                    await message.reply(f"Неверный диапазон: {item}")
                    return
            else:
                try:
                    num = int(item)
                    if num < 0 or num > 36:
                        await message.reply(f"Число {num} вне диапазона 0-36")
                        return
                    numbers.add(num)
                except:
                    await message.reply(f"Неверное число: {item}")
                    return
        
        if not numbers:
            await message.reply("Не указаны числа для ставки")
            return
        
        bet_numbers = list(numbers)
        multiplier = 36 // len(bet_numbers)
    
    update_balance(user_id, -amount)
    
    result_number = random.choice(ROULETTE_NUMBERS)
    result_color = 'green' if result_number == 0 else ('red' if result_number in RED_NUMBERS else 'black')
    result_parity = 'even' if result_number != 0 and result_number % 2 == 0 else ('odd' if result_number != 0 else None)
    
    win = False
    
    if bet_numbers and result_number in bet_numbers:
        win = True
    elif bet_parity == 'even' and result_parity == 'even':
        win = True
    elif bet_parity == 'odd' and result_parity == 'odd':
        win = True
    elif bet_color == 'red' and result_color == 'red':
        win = True
    elif bet_color == 'black' and result_color == 'black':
        win = True
    
    result_text = f"🎲 Выпало: {result_number} "
    if result_color == 'red':
        result_text += "🔴"
    elif result_color == 'black':
        result_text += "⚫"
    else:
        result_text += "🟢"
    
    if win:
        winnings = amount * multiplier
        update_balance(user_id, winnings)
        result_text += f"\n✅ Вы выиграли {winnings} Gall!"
    else:
        result_text += f"\n❌ Вы проиграли {amount} Gall"
    
    balance = get_balance(user_id)
    result_text += f"\n💰 Текущий баланс: {balance} Gall"
    
    await state.clear()
    await message.reply(result_text)

# ==================== Приветствие новых участников ====================
@dp.message(F.new_chat_members)
async def handle_new_member(message: Message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.id:
            await message.reply("Спасибо за добавление! Используйте /start для начала")
            continue
        
        chat_id = message.chat.id
        treasury = get_chat_treasury(chat_id)
        
        if treasury[1] >= treasury[2]:
            cursor.execute('UPDATE chat_treasury SET balance = balance - ? WHERE chat_id = ?', (treasury[2], chat_id))
            conn.commit()
            get_user(new_member.id, new_member.username, chat_id)
            update_balance(new_member.id, treasury[2])
            
            await message.reply(
                f"🎉 Добро пожаловать, {new_member.full_name}!\n"
                f"Вам начислено {treasury[2]} Gall из казны чата!"
            )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
