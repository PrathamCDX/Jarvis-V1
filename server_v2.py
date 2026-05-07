from tokenBucketValkey import TokenBucketValkeyMiddleware
from langchain_agent.agent import run_langchain_agent_v2
# from tokenBucket import TokenBucketMiddleware
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
import uvicorn
from logging_system import server_logger
from dotenv import load_dotenv
from valkey_conn import close_valkey, get_valkey, ping_valkey
import os

load_dotenv()
PORT_NUMBER = os.getenv('PORT_NUMBER')
DB_ENV = os.getenv('DB_ENV')

rate= 1 if DB_ENV == 'dev' else 0.13

@asynccontextmanager
async def lifespan(app):
    await get_valkey()
    await ping_valkey()
    yield
    await close_valkey()

app = FastAPI(lifespan=lifespan)

# rate = RPS , max burst = capacity, refil per min = 7
app.add_middleware(TokenBucketValkeyMiddleware, rate = rate, capacity=10)

@app.get('/ping')
async def handle_ping():
    try:
        result = 'pong2.2'
        return {"response": result}
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/query")
async def handle_query(request: Request):
    data = await request.json()

    user_query = data.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")

    try:
        result = await run_langchain_agent_v2(user_query)
        return {
            "success": True,
            "message": "Query handled successfully",
            "data": result,
            "error": False
        }
    except* ValueError as eg:
        for e in eg.exceptions:
            server_logger.error(f"Validation error in task: {e}")
        raise HTTPException(status_code=400, detail="Invalid data in sub-task")

    except* Exception as eg:
        for e in eg.exceptions:
            server_logger.exception(f"Sub-task failed: {e}")
        raise HTTPException(status_code=500, detail="Internal task group failure")

@app.get('/version')
async def version():
    return {
        "success": True,
        "message": "Version fetch successful",
        "data": "V2",
        "error": False
    }

@app.get('/debug/env')
async def debug_env():
    return {
        "success": True,
        "message": "Environment fetched successfully",
        "data": DB_ENV,
        "error": False
    }

if __name__ == "__main__":
    print('Port_number', PORT_NUMBER)
    uvicorn.run(app, host="0.0.0.0", port=int(PORT_NUMBER))
