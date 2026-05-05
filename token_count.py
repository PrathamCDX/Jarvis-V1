from plsqlsync import get_connection, release_connection
from datetime import date


def add_token(count: int):
    today = date.today().isoformat()
    conn = get_connection()
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
