from contextlib import redirect_stderr
import time
import asyncio
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class TokenBucketMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate: float, capacity: float):
        super().__init__(app)
        self.rate = rate
        self.capacity = capacity
        self.tokens = self.capacity
        self.lock = asyncio.Lock()
        self.last_updated = time.time()

    async def dispatch(self, request: Request, call_next):
        
        if not await self._consume_token():
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Slow down!"}
            )

        response = await call_next(request)
        return response

    async def _consume_token(self) -> bool:
        async with self.lock:
            now = time.time()
            
            elapsed_time = now - self.last_updated
            refill_tokens_count = int(elapsed_time * self.rate)
            self.tokens = min(self.capacity, self.tokens + refill_tokens_count)
            
            if self.tokens >= 1:
                self.tokens = self.tokens - 1
                self.last_updated = now
                return True
            
            return False
