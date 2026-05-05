import json
from datetime import date
from langchain_core.tools import tool
from plsqlsync import get_connection, release_connection
from psycopg2.extras import RealDictCursor
from logging_system import server_logger


def get_db():
    return get_connection()


def init_tables():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS token_count (
                id SERIAL PRIMARY KEY,
                date DATE DEFAULT CURRENT_DATE UNIQUE,
                token_count BIGINT NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)


@tool(description="Add token count to today's total in the database")
def add_token(count: int) -> str:
    """Add token count to today's total in the database.
    
    Args:
        count: Number of tokens to add
    """
    server_logger.info(f"Adding {count} tokens to today's count")
    today = date.today().isoformat()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('BEGIN')
        cur.execute('SELECT token_count FROM token_count WHERE date = %s FOR UPDATE', (today,))
        row = cur.fetchone()
        if row:
            cur.execute('UPDATE token_count SET token_count = token_count + %s WHERE date = %s', (count, today))
        else:
            cur.execute('INSERT INTO token_count (date, token_count) VALUES (%s, %s)', (today, count))
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result (string confirmation message)",
        "result": f"Added {count} tokens to today's count"
    })


@tool(description="Get the total token count for today")
def get_todays_token_count() -> str:
    """Get the total token count for today. Returns number of tokens used today."""
    conn = get_db()
    today = date.today().isoformat()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT token_count FROM token_count WHERE date = %s', (today,))
        row = cur.fetchone()
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (integer token count for today)",
            "result": row['token_count'] if row else 0
        })
    finally:
        release_connection(conn)


@tool(description="Get the total token count across all days")
def get_total_token_count() -> str:
    """Get the total token count across all days."""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT SUM(token_count) AS total FROM token_count')
        row = cur.fetchone()
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (integer total token count across all days)",
            "result": row['total'] if row['total'] else 0
        })
    finally:
        release_connection(conn)


token_tools = [add_token, get_todays_token_count, get_total_token_count]
