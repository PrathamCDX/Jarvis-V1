import json
from typing import Optional
from langchain_core.tools import tool
from plsqlsync import get_connection, release_connection
from psycopg2.extras import RealDictCursor


def get_db():
    return get_connection()


def init_tables():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)


@tool(description="Create a new todo with the given title and optional description")
def create_todo(title: str, description: str = '') -> str:
    """Create a new todo with the given title and optional description"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            'INSERT INTO todos (title, description, completed) VALUES (%s, %s, %s) RETURNING id',
            (title, description, False)
        )
        conn.commit()
        row = cur.fetchone()
        result = {"id": row["id"], "title": title, "description": description, "completed": False}
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
            "result": result
        })
    finally:
        release_connection(conn)


@tool(description="Get a todo by its ID")
def get_todo(id: int) -> str:
    """Get a todo by its ID"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM todos WHERE id = %s', (id,))
        row = cur.fetchone()
        if row:
            result = {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
            cur.close()
            return json.dumps({
                "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
                "result": result
            })
        raise ValueError(f"Todo with id {id} not found")
    finally:
        release_connection(conn)


@tool(description="List all todos in the database")
def list_todos() -> str:
    """List all todos in the database"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT id, title, description, completed FROM todos')
        rows = cur.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        release_connection(conn)


@tool(description="List all completed todos in the database")
def list_completed_todos() -> str:
    """List all completed todos in the database"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT id, title, description, completed FROM todos WHERE completed = TRUE')
        rows = cur.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        release_connection(conn)


@tool(description="List all uncompleted todos in the database")
def list_uncompleted_todos() -> str:
    """List all uncompleted todos in the database"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT id, title, description, completed FROM todos WHERE completed = FALSE')
        rows = cur.fetchall()
        res = []
        for row in rows:
            res.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'completed': bool(row['completed'])
            })
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (list of todo objects each with keys: id, title, description, completed)",
            "result": res
        })
    finally:
        release_connection(conn)


@tool(description="Update a todo's title, description, or completed status by ID")
def update_todo(id: int, title: Optional[str] = None, description: Optional[str] = None, completed: Optional[bool] = None) -> str:
    """Update a todo's title, description, or completed status by ID"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM todos WHERE id = %s', (id,))
        if not cur.fetchone():
            raise ValueError(f"Todo with id {id} not found")
        updates = []
        values = []
        if title is not None:
            updates.append('title = %s')
            values.append(title)
        if description is not None:
            updates.append('description = %s')
            values.append(description)
        if completed is not None:
            updates.append('completed = %s')
            values.append(completed)
        if updates:
            values.append(id)
            cur.execute(f"UPDATE todos SET {', '.join(updates)} WHERE id = %s", values)
            conn.commit()
        cur.execute('SELECT * FROM todos WHERE id = %s', (id,))
        row = cur.fetchone()
        result = {"id": row["id"], "title": row["title"], "description": row["description"], "completed": bool(row["completed"])}
        cur.close()
        return json.dumps({
            "response_schema": "create a JSON object with the keys : result (todo object with keys: id, title, description, completed)",
            "result": result
        })
    finally:
        release_connection(conn)


@tool(description="Delete a todo by its ID")
def delete_todo(id: int) -> str:
    """Delete a todo by its ID"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM todos WHERE id = %s', (id,))
        conn.commit()
        if cur.rowcount > 0:
            result = {"success": True, "id": id}
            cur.close()
            return json.dumps({
                "response_schema": "create a JSON object with the keys : result (object with keys: success, id)",
                "result": result
            })
        raise ValueError(f"Todo with id {id} not found")
    finally:
        release_connection(conn)


todo_tools = [create_todo, get_todo, list_todos, list_completed_todos, list_uncompleted_todos, update_todo, delete_todo]
