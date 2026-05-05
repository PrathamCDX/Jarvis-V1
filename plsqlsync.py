import os
import time
from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "myapp_db"),
    "user": os.getenv("DB_USER", "myuser"),
    "password": os.getenv("DB_PASSWORD", "mypassword"),
    "port": int(os.getenv("DB_PORT", "5432"))
}

connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_CONFIG
)

def get_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)

def create_test_data(start: int = 0 ,count: int = 100):
    conn = get_connection()
    try:
        cur = conn.cursor()
        for i in range(start, start+count):
            cur.execute("INSERT INTO testTable (name) VALUES (%s);", (f'testName{i}',))
            print(f"Executing for {i}")
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)

if __name__ == "__main__":
    start_time = time.perf_counter()
    print(create_test_data(0,1000010))
    end_time = time.perf_counter()
    print(f"Time taken: {end_time - start_time} seconds")





# def get_users():
#     conn = get_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM testTable;")
#         data = cur.fetchall()
#         cur.close()
#         return data
#     finally:
#         release_connection(conn)
