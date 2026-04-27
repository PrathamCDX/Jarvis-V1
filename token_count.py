import sqlite3
from datetime import date

DB_PATH = 'todo.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tables():
    conn = get_db()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS token_count (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT CURRENT_DATE UNIQUE,
                token_count BIGINT NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()
        print('Table creation success')
    finally:
        conn.close()

def add_token(count: int):
    today = date.today().isoformat()
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO token_count (date, token_count)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET
                token_count = token_count + excluded.token_count
        ''', (today, count))
        conn.commit()
    finally:
        conn.close()

def get_todays_token():
    conn = get_db()
    today = date.today().isoformat()
    try:
        # Use .fetchone() to get the actual row data
        row = conn.execute(
            'SELECT token_count FROM token_count WHERE date = ?', 
            (today,)
        ).fetchone()
        
        # If a row exists, return the count; otherwise, return 0
        return row['token_count'] if row else 0
    finally:
        conn.close()


if __name__ == '__main__' :
    print(get_todays_token())
