import sqlite3
from plsqlsync import get_connection, release_connection

SQLITE_DB_PATH = 'todo.db'


def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_pgsql_tables(pg_conn):
    cur = pg_conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT FALSE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS token_count (
            id SERIAL PRIMARY KEY,
            date DATE DEFAULT CURRENT_DATE UNIQUE,
            token_count BIGINT NOT NULL DEFAULT 0
        )
    ''')
    pg_conn.commit()
    cur.close()


def migrate_sqlite_to_pgsql():
    sqlite_conn = get_sqlite_conn()
    pg_conn = get_connection()
    try:
        create_pgsql_tables(pg_conn)

        # Migrate todos
        rows = sqlite_conn.execute('SELECT id, title, description, completed FROM todos').fetchall()
        todos_data = [(r['title'], r['description'], bool(r['completed'])) for r in rows]
        cur = pg_conn.cursor()
        cur.executemany(
            'INSERT INTO todos ( title, description, completed) VALUES ( %s, %s, %s) ON CONFLICT (id) DO NOTHING',
            todos_data
        )
        pg_conn.commit()
        cur.close()
        print(f'Migrated {len(todos_data)} todos')

        # Migrate token_count
        rows = sqlite_conn.execute('SELECT id, date, token_count FROM token_count').fetchall()
        token_data = [( r['date'], r['token_count']) for r in rows]
        cur = pg_conn.cursor()
        cur.executemany(
            'INSERT INTO token_count ( date, token_count) VALUES ( %s, %s) ON CONFLICT (date) DO NOTHING',
            token_data
        )
        pg_conn.commit()
        cur.close()
        print(f'Migrated {len(token_data)} token_count records')

    finally:
        sqlite_conn.close()
        release_connection(pg_conn)


if __name__ == '__main__':
    migrate_sqlite_to_pgsql()
