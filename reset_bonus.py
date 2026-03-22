import sqlite3

conn = sqlite3.connect("bot.db")
c = conn.cursor()
c.execute("UPDATE users SET last_bonus = NULL")
conn.commit()
conn.close()
print("Сброс выполнен")
