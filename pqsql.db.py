# # import time
# # # db.py
# # from psycopg2 import pool
# # # from db import get_connection, release_connection


# # DB_CONFIG = {
# #     "host": "localhost",
# #     "database": "myapp_db",
# #     "user": "myuser",
# #     "password": "mypassword",
# #     "port": 5432
# # }

# # connection_pool = pool.SimpleConnectionPool(
# #     minconn=1,
# #     maxconn=10,
# #     **DB_CONFIG
# # )

# # def get_connection():
# #     return connection_pool.getconn()

# # def release_connection(conn):
# #     connection_pool.putconn(conn)


# # def get_users():
# #     conn = get_connection()
# #     try:
# #         cur = conn.cursor()
# #         cur.execute("SELECT * FROM testTable;")
# #         data = cur.fetchall()
# #         cur.close()
# #         return data
# #     finally:
# #         release_connection(conn)

# # def create_test_data(start: int = 0 ,count: int = 100):
# #     conn = get_connection()
# #     try:
# #         cur = conn.cursor()
# #         for i in range(start, start+count):
# #             cur.execute("INSERT INTO testTable (name) VALUES (%s);", (f'testName{i}',))
# #             print(f"Executing for {i}")
# #         conn.commit()
# #         cur.close()
# #     finally:
# #         release_connection(conn)

# # if __name__ == "__main__":
# #     start_time = time.perf_counter()
# #     print(create_test_data(1000010, 1))
# #     end_time = time.perf_counter()
# #     print(f"Time taken: {end_time - start_time} seconds")

# # db_async.py
# import asyncpg
# import asyncio
# import time

# DB_CONFIG = {
#     "user": "myuser",
#     "password": "mypassword",
#     "database": "myapp_db",
#     "host": "localhost",
#     "port": 5432
# }

# pool = None

# async def init_db():
#     global pool
#     pool = await asyncpg.create_pool(
#         min_size=1,
#         max_size=10,
#         **DB_CONFIG
#     )

# async def create_test_data_single(start: int = 0, count: int = 100):
#     async with pool.acquire() as conn:
#         for i in range(start, start + count):
#             await conn.execute(
#                 "INSERT INTO testTableWithoutIndex (name) VALUES ($1);",
#                 f"testName{i}"
#             )
#             print(f"Executing for {i}")

# async def main():
#     await init_db()

#     start_time = time.perf_counter()
#     await create_test_data_single(0,1000011)
#     end_time = time.perf_counter()

#     print(f"Time taken: {end_time - start_time} seconds")

# if __name__ == "__main__":
#     asyncio.run(main())




# # async def get_users():
# #     async with pool.acquire() as conn:
# #         return await conn.fetch("SELECT * FROM testTableWithoutIndex;")

# # async def create_test_data(start: int = 0, count: int = 100):
# #     async with pool.acquire() as conn:
# #         values = [(f'testName{i}',) for i in range(start, start + count)]

# #         await conn.executemany(
# #             "INSERT INTO testTableWithoutIndex (name) VALUES ($1);",
# #             values
# #         )