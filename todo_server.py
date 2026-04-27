import sqlite3
from typing import Optional
from mcp.server.fastmcp import FastMCP
from logging_system import logger
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
def create_todo(title: str, description: str = '') -> dict:
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)',
            (title, description, 0)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "title": title, "description": description, "completed": False}
    finally:
        conn.close()

@mcp.tool(description="Get a todo by its ID")
def get_todo(id: int) -> dict:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
        return {"error": f"Todo with id {id} not found"}
    finally:
        conn.close()

@mcp.tool(description="List all todos in the database")
def list_todos() -> list:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos')
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        res = []
        for row in rows:
            # 2. Use string keys and append to the list
            new_data = {
                'id': row['id'], 
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed']) # Converts 0/1 to True/False
            }
            res.append(new_data)
        # logger.info(res)
        return res
    finally:
        conn.close()

@mcp.tool(description="List all completed todos in the database")
def list_completed_todos() -> list:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos WHERE completed = 1')
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        res = []
        for row in rows:
            # 2. Use string keys and append to the list
            new_data = {
                'id': row['id'], 
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed']) # Converts 0/1 to True/False
            }
            res.append(new_data)
        # logger.info(res)
        return res
    finally:
        conn.close()

@mcp.tool(description="List all uncompleted todos in the database")
def list_uncompleted_todos() -> list:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos WHERE completed = 0')
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        res = []
        for row in rows:
            # 2. Use string keys and append to the list
            new_data = {
                'id': row['id'], 
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed']) # Converts 0/1 to True/False
            }
            res.append(new_data)
        # logger.info(res)
        return res
    finally:
        conn.close()

@mcp.tool(description="Update a todo's title, description, or completed status by ID")
def update_todo(id: int, title: Optional[str] = None, description: Optional[str] = None, completed: Optional[bool] = None) -> dict:
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        if not cursor.fetchone():
            return {"error": f"Todo with id {id} not found"}
        
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
        
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        row = cursor.fetchone()
        return {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
    finally:
        conn.close()

@mcp.tool(description="Delete a todo by its ID")
def delete_todo(id: int) -> dict:
    conn = get_db()
    try:
        cursor = conn.execute('DELETE FROM todos WHERE id = ?', (id,))
        conn.commit()
        if cursor.rowcount > 0:
            return {"success": True, "id": id}
        return {"error": f"Todo with id {id} not found"}
    finally:
        conn.close()

if __name__ == '__main__':
    init_tables()
    mcp.run(transport='stdio')