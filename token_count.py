import sqlite3
from datetime import date
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('token_server')
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


@mcp.tool(description="""Add token count to today's total in the database.
    
    Args:
        count: Number of tokens to add
        
    Returns:
        Confirmation message with added count
    """)
def add_token(count: int) -> str:
    """Add token count to today's total in the database.
    
    Args:
        count: Number of tokens to add
        
    Returns:
        Confirmation message with added count
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
    return f"Added {count} tokens to today's count"


@mcp.tool(description="""Get the total token count for today.
    Returns:
        Number of tokens used today
    """)
def get_todays_token() -> int:
    """Get the total token count for today.
    
    Returns:
        Number of tokens used today
    """
    conn = get_db()
    today = date.today().isoformat()
    try:
        row = conn.execute(
            'SELECT token_count FROM token_count WHERE date = ?', 
            (today,)
        ).fetchone()
        
        return row['token_count'] if row else 0
    finally:
        conn.close()


@mcp.tool(description="""Get the total token count across all days.
    
    Returns:
        Total number of tokens used
    """)
def get_total_token_count() -> int:
    """Get the total token count across all days.
    
    Returns:
        Total number of tokens used
    """
    conn = get_db()
    try:
        row = conn.execute('SELECT SUM(token_count) AS total FROM token_count').fetchone()
        return row['total'] if row['total'] else 0
    finally:
        conn.close()


if __name__ == '__main__':
    mcp.run(transport='stdio')
