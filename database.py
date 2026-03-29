import psycopg2
import datetime
import random
import string

DB_CONFIG = {
    "dbname": "bothost_db_ba81305b6da8",
    "user": "bothost_db_ba81305b6da8",
    "password": "oVNaiu_2B2IYMXotiuveax264qu6WPcfkcOii2ntTUg",
    "host": "node1.pghost.ru",
    "port": "32857"
}
def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# -------------------------
# Инициализация базы данных
# -------------------------
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    last_bonus TIMESTAMP,
                    stars INTEGER DEFAULT 0
                )''')

    # Транзакции
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount INTEGER,
                    reason TEXT,
                    timestamp TIMESTAMP
                )''')

    # Чеки
    c.execute('''CREATE TABLE IF NOT EXISTS checks (
                    code TEXT PRIMARY KEY,
                    amount INTEGER,
                    created_by BIGINT,
                    created_at TIMESTAMP,
                    claimed_by BIGINT
                )''')

    # Промокоды
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
                    code TEXT PRIMARY KEY,
                    reward INTEGER,
                    max_uses INTEGER,
                    uses INTEGER DEFAULT 0
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS promo_uses (
                    user_id BIGINT,
                    code TEXT,
                    PRIMARY KEY (user_id, code)
                )''')

    # Настройки групп
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
                    group_id BIGINT PRIMARY KEY,
                    games_enabled INTEGER DEFAULT 1
                )''')

    # Казна групп
    c.execute('''CREATE TABLE IF NOT EXISTS group_treasury (
                    group_id BIGINT PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    reward INTEGER DEFAULT 0
                )''')

    # Приглашения
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
                    user_id BIGINT PRIMARY KEY,
                    invited_by BIGINT
                )''')

    conn.commit()
    conn.close()


# -------------------------
# Пользователи
# -------------------------
def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, username, balance, last_bonus FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_top_users(limit=10):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT username, balance 
        FROM users 
        ORDER BY balance DESC 
        LIMIT %s
    """, (limit,))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

def create_user(user_id, username):
    if get_user(user_id):
        return False

    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, balance, last_bonus) VALUES (%s, %s, %s, %s)",
        (user_id, username, 0, None)
    )
    conn.commit()
    conn.close()
    return True


def update_balance(user_id, delta, reason):
    conn = get_conn()
    c = conn.cursor()

    c.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (delta, user_id))
    c.execute(
        "INSERT INTO transactions (user_id, amount, reason, timestamp) VALUES (%s, %s, %s, %s)",
        (user_id, delta, reason, datetime.datetime.now())
    )

    conn.commit()
    conn.close()

    user = get_user(user_id)
    return user[2] if user else None


def get_balance(user_id):
    user = get_user(user_id)
    return user[2] if user else 0


def set_last_bonus(user_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("UPDATE users SET last_bonus=%s WHERE user_id=%s", (now, user_id))
    conn.commit()
    conn.close()


def get_last_bonus(user_id):
    user = get_user(user_id)
    return user[3] if user and user[3] else None


# -------------------------
# Казна групп
# -------------------------
def get_group_treasury(group_id):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT balance, reward FROM group_treasury WHERE group_id=%s", (group_id,))
    row = c.fetchone()

    if not row:
        c.execute(
            "INSERT INTO group_treasury (group_id, balance, reward) VALUES (%s, %s, %s)",
            (group_id, 0, 0)
        )
        conn.commit()
        row = (0, 0)

    conn.close()
    return {"balance": row[0], "reward": row[1]}


def update_group_treasury(group_id, delta_balance=0, delta_reward=None):
    conn = get_conn()
    c = conn.cursor()

    if delta_reward is not None:
        c.execute("UPDATE group_treasury SET reward=%s WHERE group_id=%s", (delta_reward, group_id))

    if delta_balance != 0:
        c.execute(
            "UPDATE group_treasury SET balance = balance + %s WHERE group_id=%s",
            (delta_balance, group_id)
        )

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
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now()

    c.execute(
        "INSERT INTO checks (code, amount, created_by, created_at, claimed_by) VALUES (%s, %s, %s, %s, %s)",
        (code, amount, user_id, now, None)
    )

    conn.commit()
    conn.close()
    return code


def use_check(code, user_id):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT amount, created_by, claimed_by FROM checks WHERE code=%s", (code,))
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

    c.execute("UPDATE checks SET claimed_by=%s WHERE code=%s", (user_id, code))
    conn.commit()
    conn.close()

    update_balance(user_id, amount, f"Активация чека {code}")
    return amount, None


# -------------------------
# Промокоды
# -------------------------
def create_promo(code: str, reward: int, max_uses: int):
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "INSERT INTO promocodes (code, reward, max_uses, uses) VALUES (%s, %s, %s, 0)",
        (code.upper(), reward, max_uses)
    )

    conn.commit()
    conn.close()


def use_promo(code: str, user_id: int):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT 1 FROM promo_uses WHERE user_id=%s AND code=%s", (user_id, code))
    if c.fetchone():
        conn.close()
        return None, "❌ Ты уже использовал этот промокод"

    c.execute("SELECT reward, uses, max_uses FROM promocodes WHERE code=%s", (code,))
    row = c.fetchone()

    if not row:
        conn.close()
        return None, "❌ Промокод не найден"

    reward, uses, max_uses = row

    if uses >= max_uses:
        conn.close()
        return None, "❌ Промокод закончился"

    c.execute("INSERT INTO promo_uses (user_id, code) VALUES (%s, %s)", (user_id, code))
    c.execute("UPDATE promocodes SET uses = uses + 1 WHERE code=%s", (code,))

    conn.commit()
    conn.close()

    update_balance(user_id, reward, f"Промокод {code}")
    return reward, None
