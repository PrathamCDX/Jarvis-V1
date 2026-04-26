import sqlite3
from typing import Optional
from mcp.server.fastmcp import FastMCP

DB_PATH = 'todo.db'

mcp = FastMCP('todo_server')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tables():
    conn = get_db()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
    finally:
        conn.close()

@mcp.tool(description="Create a new todo with the given title and optional description")
def create_todo(title: str, description: str = '') -> str:
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)',
            (title, description, 0)
        )
        conn.commit()
        return f'Todo created with id {cursor.lastrowid}'
    finally:
        conn.close()

@mcp.tool(description="Get a todo by its ID")
def get_todo(id: int) -> str:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        row = cursor.fetchone()
        if row:
            return f"ID: {row['id']}, Title: {row['title']}, Description: {row['description']}, Completed: {bool(row['completed'])}"
        return f'Todo with id {id} not found'
    finally:
        conn.close()

@mcp.tool(description="List all todos in the database", )
def list_todos() -> str:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos')
        rows = cursor.fetchall()
        if not rows:
            return 'No todos found'
        return '\n'.join(
            f"ID: {r['id']}, Title: {r['title']}, Description: {r['description']}, Completed: {bool(r['completed'])}"
            for r in rows
        )
    finally:
        conn.close()

@mcp.tool(description="Update a todo's title, description, or completed status by ID")
def update_todo(id: int, title: Optional[str] = None, description: Optional[str] = None, completed: Optional[bool] = None) -> str:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        if not cursor.fetchone():
            return f'Todo with id {id} not found'
        
        updates = []
        values = []
        if title is not None:
            updates.append('title = ?')
            values.append(title)
        if description is not None:
            updates.append('description = ?')
            values.append(description)
        if completed is not None:
            updates.append('completed = ?')
            values.append(int(completed))
        
        if updates:
            values.append(id)
            conn.execute(f"UPDATE todos SET {', '.join(updates)} WHERE id = ?", values)
            conn.commit()
        return f'Todo {id} updated'
    finally:
        conn.close()

@mcp.tool(description="Delete a todo by its ID")
def delete_todo(id: int) -> str:
    conn = get_db()
    try:
        cursor = conn.execute('DELETE FROM todos WHERE id = ?', (id,))
        conn.commit()
        if cursor.rowcount > 0:
            return f'Todo {id} deleted'
        return f'Todo with id {id} not found'
    finally:
        conn.close()

if __name__ == '__main__':
    init_tables()
    mcp.run(transport='stdio')