import os
import redis.asyncio as redis

_client = None

async def get_valkey():
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("VALKEY_HOST", "localhost"),
            port=int(os.getenv("VALKEY_PORT", "6379")),
            password=os.getenv("VALKEY_PASSWORD", "myvalkey"),

            decode_responses=True,
        )
    return _client

async def close_valkey():
    global _client
    if _client:
        await _client.close()
        _client = None

async def ping_valkey():
    client = await get_valkey()
    return await client.ping()
