# from script import init_all_tables
from langchain_agent.agent import run_langchain_agent_v2
from tokenBucketValkey import create_rate_limit_dependency, get_limiter
from fastapi import FastAPI, Request, HTTPException, Depends
from contextlib import asynccontextmanager
import uvicorn
from logging_system import server_logger
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from valkey_conn import close_valkey, get_valkey, ping_valkey
import os

load_dotenv()
PORT_NUMBER = os.getenv('PORT_NUMBER') or 8000
DB_ENV = os.getenv('DB_ENV')

# rate = 1 if DB_ENV == 'dev' else 0.13

llm_rate_limit = create_rate_limit_dependency("llm", rate=0.13, capacity=10)

@asynccontextmanager
async def lifespan(app):
    # init_all_tables()
    await get_valkey()
    await ping_valkey()
    yield
    await close_valkey()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    limiter = get_limiter("global", rate=0.3, capacity=20)
    if not await limiter.consume_token():
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Slow down!"})
    return await call_next(request)



@app.get('/ping')
async def handle_ping():
    try:
        result = 'pong2.2'
        return {"response": result}
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/query", dependencies=[Depends(llm_rate_limit)])
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

@app.get('/version', dependencies=[Depends(llm_rate_limit)])
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
