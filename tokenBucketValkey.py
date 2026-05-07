import os
import time
import asyncio
import redis.asyncio as redis
from typing import Optional, Dict
from fastapi import HTTPException
from valkey_conn import get_valkey, ping_valkey
from logging_system import server_logger

LUA_SCRIPT = """
local tokens = tonumber(redis.call('GET', KEYS[1]) or '0')
local last = tonumber(redis.call('GET', KEYS[2]) or '0')
local now = tonumber(redis.call('TIME')[1])
local elapsed = now - last
local refill = elapsed * ARGV[1]
local new_tokens = math.min(ARGV[2], tokens + refill)
if new_tokens >= 1 then
    redis.call('SET', KEYS[1], new_tokens - 1)
    redis.call('SET', KEYS[2], now)
    return 1
end
redis.call('SET', KEYS[1], new_tokens)
redis.call('SET', KEYS[2], now)
return 0
"""

class ValkeyRateLimiter:
    RECOVERY_CHECK_INTERVAL = 100

    def __init__(self, name: str, rate: float, capacity: float):
        self.name = name
        self.rate = rate
        self.capacity = capacity
        self.tokens_key = f"ratelimit:{name}:tokens"
        self.last_key = f"ratelimit:{name}:last"
        self.lua_sha: Optional[str] = None

        env = os.getenv("DB_ENV", "dev")
        self.fallback_capacity = capacity * 0.7 if env == "prod" else capacity

        self.tokens = self.fallback_capacity
        self.lock = asyncio.Lock()
        self.last_updated = time.time()
        self.use_valkey = True
        self.fallback_checks = 0

    async def _seed_bucket(self):
        client = await get_valkey()
        now = str(time.time())
        await client.setnx(self.tokens_key, str(self.capacity))
        await client.setnx(self.last_key, now)

    async def _load_script(self):
        if self.lua_sha is None:
            client = await get_valkey()
            self.lua_sha = await client.script_load(LUA_SCRIPT)

    async def _consume_token_python(self) -> bool:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_updated
            refill = int(elapsed * self.rate)
            self.tokens = min(self.fallback_capacity, self.tokens + refill)
            if self.tokens >= 1:
                self.tokens -= 1
                self.last_updated = now
                return True
            return False

    async def _check_valkey_recovery(self):
        try:
            await ping_valkey()
            self.tokens = self.fallback_capacity
            self.last_updated = time.time()
            self.lua_sha = None
            self.use_valkey = True
            self.fallback_checks = 0
            server_logger.info("Valkey recovered — switching back to Valkey rate limiting (%s)", self.name)
        except Exception:
            pass

    async def consume_token(self) -> bool:
        if self.use_valkey:
            try:
                await self._seed_bucket()
                await self._load_script()
                client = await get_valkey()
                result = await client.evalsha(
                    self.lua_sha,  # type: ignore
                    2,
                    self.tokens_key,
                    self.last_key,
                    str(self.rate),
                    str(self.capacity),
                )
                return result == 1
            except (redis.ConnectionError, redis.TimeoutError) as e:
                self.use_valkey = False
                server_logger.warning("Valkey unavailable (%s) — falling back to in-memory rate limiting (%s)", e, self.name)
                return await self._consume_token_python()
        else:
            self.fallback_checks += 1
            if self.fallback_checks >= self.RECOVERY_CHECK_INTERVAL:
                self.fallback_checks = 0
                await self._check_valkey_recovery()
            return await self._consume_token_python()


_limiters: Dict[str, ValkeyRateLimiter] = {}

def get_limiter(name: str, rate: float, capacity: float) -> ValkeyRateLimiter:
    if name not in _limiters:
        _limiters[name] = ValkeyRateLimiter(name, rate, capacity)
    return _limiters[name]

def create_rate_limit_dependency(name: str, rate: float, capacity: float):
    limiter = get_limiter(name, rate, capacity)
    async def rate_limit():
        if not await limiter.consume_token():
            raise HTTPException(status_code=429, detail="Too many requests. Slow down!")
    return rate_limit
