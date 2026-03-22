import sqlite3
import datetime

DB_PATH = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    last_bonus TIMESTAMP
                )''')
    # История транзакций (для /history)
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    reason TEXT,
                    timestamp TIMESTAMP
                )''')
    # Чеки
    c.execute('''CREATE TABLE IF NOT EXISTS checks (
                    code TEXT PRIMARY KEY,
                    amount INTEGER,
                    created_by INTEGER,
                    created_at TIMESTAMP,
                    claimed_by INTEGER
                )''')
    # Промокоды
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
                    code TEXT PRIMARY KEY,
                    reward INTEGER,
                    used_by INTEGER
                )''')
    # Настройки групп
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    games_enabled INTEGER DEFAULT 1
                )''')
    # Казны групп
    c.execute('''CREATE TABLE IF NOT EXISTS group_treasury (
                    group_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

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
    now = datetime.datetime.now().isoformat()
    c.execute("INSERT INTO users (user_id, username, balance, last_bonus) VALUES (?, ?, ?, ?)",
              (user_id, username, 0, now))
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
    return get_user(user_id)[2] + delta if get_user(user_id) else delta

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
    return datetime.datetime.fromisoformat(user[3]) if user and user[3] else None

# Аналогично для других таблиц...