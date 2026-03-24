import sqlite3
import datetime
import random
import string

DB_PATH = "bot.db"

# -------------------------
# Инициализация базы данных
# -------------------------
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
    
    # Транзакции
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
    
    # Казна групп
    c.execute('''CREATE TABLE IF NOT EXISTS group_treasury (
                    group_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    reward INTEGER DEFAULT 0
                )''')
    
    # Приглашения
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
                    user_id INTEGER PRIMARY KEY,
                    invited_by INTEGER
               )''')
    
    conn.commit()
    conn.close()


# -------------------------
# Пользователи
# -------------------------
def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, balance, last_bonus FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(user_id, username):
    if get_user(user_id):
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, balance, last_bonus) VALUES (?, ?, ?, ?)",
              (user_id, username, 0, None))
    conn.commit()
    conn.close()
    return True

def update_balance(user_id, delta, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))
    c.execute("INSERT INTO transactions (user_id, amount, reason, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, delta, reason, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
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


# -------------------------
# Казна групп
# -------------------------
def get_group_treasury(group_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance, reward FROM group_treasury WHERE group_id=?", (group_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO group_treasury (group_id, balance, reward) VALUES (?, ?, ?)", (group_id, 0, 0))
        conn.commit()
        row = (0, 0)
    conn.close()
    return {"balance": row[0], "reward": row[1]}

def update_group_treasury(group_id, delta_balance=0, delta_reward=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if delta_reward is not None:
        c.execute("UPDATE group_treasury SET reward=? WHERE group_id=?", (delta_reward, group_id))
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


# -------------------------
# Чеки
# -------------------------
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
    update_balance(user_id, amount, f"Активация чека {code}")
    return amount, None


# -------------------------
# Промокоды
# -------------------------
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


# -------------------------
# Топ пользователей
# -------------------------
def get_top_users(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_history(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT amount, reason, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


# -------------------------
# Настройки групп
# -------------------------
def get_group_settings(group_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT games_enabled FROM groups WHERE group_id=?", (group_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return 1

def set_group_settings(group_id, enabled):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (group_id, games_enabled) VALUES (?, ?)", (group_id, enabled))
    conn.commit()
    conn.close()


# -------------------------
# Приглашения
# -------------------------
def add_invite(user_id, inviter_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM invites WHERE user_id=?", (user_id,))
    if c.fetchone():
        conn.close()
        return False
    c.execute("INSERT INTO invites (user_id, invited_by) VALUES (?, ?)", (user_id, inviter_id))
    conn.commit()
    conn.close()
    return True

    c.execute("SELECT user_id FROM invites WHERE user_id=?", (user_id,))
    if c.fetchone():
        conn.close()
        return False

    c.execute("INSERT INTO invites (user_id, invited_by) VALUES (?, ?)", (user_id, inviter_id))
    conn.commit()
    conn.close()
    return True
