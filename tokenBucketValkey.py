import os
import time
import asyncio
import redis.asyncio as redis
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
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

class TokenBucketValkeyMiddleware(BaseHTTPMiddleware):
    TOKENS_KEY = "ratelimit:tokens"
    LAST_KEY = "ratelimit:last"
    RECOVERY_CHECK_INTERVAL = 100

    def __init__(self, app, rate: float, capacity: float):
        super().__init__(app)
        self.rate = rate
        self.capacity = capacity
        self.lua_sha: Optional[str] = None

        env = os.getenv("DB_ENV", "dev")
        self.fallback_capacity = self.capacity * 0.7 if env == "prod" else self.capacity

        self.tokens = self.fallback_capacity
        self.lock = asyncio.Lock()
        self.last_updated = time.time()
        self.use_valkey = True
        self.fallback_checks = 0

    async def _seed_bucket(self):
        client = await get_valkey()
        now = str(time.time())
        await client.setnx(self.TOKENS_KEY, str(self.capacity))
        await client.setnx(self.LAST_KEY, now)

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
            server_logger.info("Valkey recovered — switching back to Valkey rate limiting")
        except Exception:
            pass

    async def _consume_token(self) -> bool:
        if self.use_valkey:
            try:
                await self._seed_bucket()
                await self._load_script()
                client = await get_valkey()
                result = await client.evalsha(
                    self.lua_sha,  # type: ignore
                    2,
                    self.TOKENS_KEY,
                    self.LAST_KEY,
                    str(self.rate),
                    str(self.capacity),
                )
                return result == 1
            except (redis.ConnectionError, redis.TimeoutError) as e:
                self.use_valkey = False
                server_logger.warning("Valkey unavailable (%s) — falling back to in-memory rate limiting", e)
                return await self._consume_token_python()
        else:
            self.fallback_checks += 1
            if self.fallback_checks >= self.RECOVERY_CHECK_INTERVAL:
                self.fallback_checks = 0
                await self._check_valkey_recovery()
            return await self._consume_token_python()

    async def dispatch(self, request: Request, call_next):
        if not await self._consume_token():
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Slow down!"}
            )
        return await call_next(request)
