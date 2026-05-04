import sqlite3
import json
from datetime import date
from langchain_core.tools import tool

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
    finally:
        conn.close()


@tool
def add_token(count: int) -> str:
    """Add token count to today's total in the database.
    
    Args:
        count: Number of tokens to add
    """
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
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result (string confirmation message)",
        "result": f"Added {count} tokens to today's count"
    })


@tool
def get_todays_token_count() -> str:
    """Get the total token count for today. Returns number of tokens used today."""
    conn = get_db()
    today = date.today().isoformat()
    try:
        row = conn.execute(
            'SELECT token_count FROM token_count WHERE date = ?',
            (today,)
        ).fetchone()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (integer token count for today)",
            "result": row['token_count'] if row else 0
        })
    finally:
        conn.close()


@tool
def get_total_token_count() -> str:
    """Get the total token count across all days."""
    conn = get_db()
    try:
        row = conn.execute('SELECT SUM(token_count) AS total FROM token_count').fetchone()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (integer total token count across all days)",
            "result": row['total'] if row['total'] else 0
        })
    finally:
        conn.close()


token_tools = [add_token, get_todays_token_count, get_total_token_count]
