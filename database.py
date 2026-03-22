import sqlite3
import datetime
import random
import string

DB_PATH = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    last_bonus TIMESTAMP
                )''')
    # Таблица транзакций
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    reason TEXT,
                    timestamp TIMESTAMP
                )''')
    # Таблица чеков
    c.execute('''CREATE TABLE IF NOT EXISTS checks (
                    code TEXT PRIMARY KEY,
                    amount INTEGER,
                    created_by INTEGER,
                    created_at TIMESTAMP,
                    claimed_by INTEGER
                )''')
    # Таблица промокодов
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
                    code TEXT PRIMARY KEY,
                    reward INTEGER,
                    used_by INTEGER
                )''')
    # Таблица настроек игр в группах
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    games_enabled INTEGER DEFAULT 1
                )''')
    # Таблица казны групп (баланс и награда за приглашение)
    c.execute('''CREATE TABLE IF NOT EXISTS group_treasury (
                    group_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    reward INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

# --- Функции для пользователей ---
def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, balance, last_bonus FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, balance, last_bonus) VALUES (?, ?, ?, ?)",
              (user_id, username, 0, None))  # важно: last_bonus = None
    conn.commit()
    conn.close()

def update_balance(user_id, delta, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))
    c.execute("INSERT INTO transactions (user_id, amount, reason, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, delta, reason, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    # вернуть новый баланс
    user = get_user(user_id)
    return user[2] if user else None

def get_balance(user_id):
    user = get_user(user_id)
    return user[2] if user else 0

def set_last_bonus(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    c.execute("UPDATE users SET last_bonus=? WHERE user_id=?", (now, user_id))
    conn.commit()
    conn.close()

def get_last_bonus(user_id):
    user = get_user(user_id)
    if user and user[3]:
        return datetime.datetime.fromisoformat(user[3])
    return None

# --- Функции для казны групп ---
def get_group_treasury(group_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance, reward FROM group_treasury WHERE group_id=?", (group_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"balance": row[0], "reward": row[1]}
    else:
        # Создаём запись по умолчанию
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO group_treasury (group_id, balance, reward) VALUES (?, ?, ?)",
                  (group_id, 0, 0))
        conn.commit()
        conn.close()
        return {"balance": 0, "reward": 0}

def update_group_treasury(group_id, delta_balance=0, delta_reward=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if delta_reward is not None:
        c.execute("UPDATE group_treasury SET reward = ? WHERE group_id=?", (delta_reward, group_id))
    if delta_balance != 0:
        c.execute("UPDATE group_treasury SET balance = balance + ? WHERE group_id=?", (delta_balance, group_id))
    conn.commit()
    conn.close()

def set_reward(group_id, reward):
    update_group_treasury(group_id, delta_reward=reward)

def add_to_treasury(group_id, amount):
    update_group_treasury(group_id, delta_balance=amount)

def subtract_from_treasury(group_id, amount):
    update_group_treasury(group_id, delta_balance=-amount)

# --- Функции для чеков ---
def generate_check_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def create_check(user_id, amount):
    code = generate_check_code()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    c.execute("INSERT INTO checks (code, amount, created_by, created_at, claimed_by) VALUES (?, ?, ?, ?, ?)",
              (code, amount, user_id, now, None))
    conn.commit()
    conn.close()
    return code

def use_check(code, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT amount, created_by, claimed_by FROM checks WHERE code=?", (code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, "Чек не найден"
    amount, created_by, claimed_by = row
    if claimed_by is not None:
        conn.close()
        return None, "Чек уже использован"
    if created_by == user_id:
        conn.close()
        return None, "Нельзя использовать свой чек"
    c.execute("UPDATE checks SET claimed_by=? WHERE code=?", (user_id, code))
    conn.commit()
    conn.close()
    # Начисляем сумму пользователю
    update_balance(user_id, amount, f"Активация чека {code}")
    return amount, None

# --- Функции для промокодов ---
def create_promo(code, reward):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO promocodes (code, reward, used_by) VALUES (?, ?, ?)", (code, reward, None))
    conn.commit()
    conn.close()

def use_promo(code, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT reward FROM promocodes WHERE code=? AND used_by IS NULL", (code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, "Неверный или уже использованный промокод"
    reward = row[0]
    c.execute("UPDATE promocodes SET used_by=? WHERE code=?", (user_id, code))
    conn.commit()
    conn.close()
    update_balance(user_id, reward, f"Промокод {code}")
    return reward, None

# --- Функции для топ-10 ---
def get_top_users(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Функции для истории ---
def get_user_history(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT amount, reason, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Функции для групп (игровые настройки) ---
def get_group_settings(group_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT games_enabled FROM groups WHERE group_id=?", (group_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    else:
        # По умолчанию игры включены
        return 1

def set_group_settings(group_id, enabled):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (group_id, games_enabled) VALUES (?, ?)", (group_id, enabled))
    conn.commit()
    conn.close()
