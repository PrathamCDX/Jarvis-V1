import sqlite3
import json
from typing import Optional
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


@tool
def create_todo(title: str, description: str = '') -> str:
    """Create a new todo with the given title and optional description"""
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)',
            (title, description, 0)
        )
        conn.commit()
        result = {"id": cursor.lastrowid, "title": title, "description": description, "completed": False}
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
            "result": result
        })
    finally:
        conn.close()


@tool
def get_todo(id: int) -> str:
    """Get a todo by its ID"""
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        row = cursor.fetchone()
        if row:
            result = {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
            return json.dumps({
                "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
                "result": result
            })
        raise ValueError(f"Todo with id {id} not found")
    finally:
        conn.close()


@tool
def list_todos() -> str:
    """List all todos in the database"""
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos')
        rows = cursor.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        conn.close()


@tool
def list_completed_todos() -> str:
    """List all completed todos in the database"""
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos WHERE completed = 1')
        rows = cursor.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        conn.close()


@tool
def list_uncompleted_todos() -> str:
    """List all uncompleted todos in the database"""
    conn = get_db()
    try:
        cursor = conn.execute('SELECT id, title, description, completed FROM todos WHERE completed = 0')
        rows = cursor.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        conn.close()


@tool
def update_todo(id: int, title: Optional[str] = None, description: Optional[str] = None, completed: Optional[bool] = None) -> str:
    """Update a todo's title, description, or completed status by ID"""
    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM todos WHERE id = ?', (id,))
        if not cursor.fetchone():
            raise ValueError(f"Todo with id {id} not found")
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
        result = {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
            "result": result
        })
    finally:
        conn.close()


@tool
def delete_todo(id: int) -> str:
    """Delete a todo by its ID"""
    conn = get_db()
    try:
        cursor = conn.execute('DELETE FROM todos WHERE id = ?', (id,))
        conn.commit()
        if cursor.rowcount > 0:
            result = {"success": True, "id": id}
            return json.dumps({
                "response_schema": "create a JSON object with the keys : result (object with keys: success, id)",
                "result": result
            })
        raise ValueError(f"Todo with id {id} not found")
    finally:
        conn.close()


todo_tools = [create_todo, get_todo, list_todos, list_completed_todos, list_uncompleted_todos, update_todo, delete_todo]
