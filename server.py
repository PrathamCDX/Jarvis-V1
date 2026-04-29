from fastapi import FastAPI, Request, HTTPException
import uvicorn
from client import run_agent_v2, global_async_stack, connect_all_servers
from logging_system import server_logger
from contextlib import asynccontextmanager
from config import server_names


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_all_servers(server_list=server_names, connected_servers=0)
    yield
    server_logger.info('Cleanig all MCP servers in async stack ')
    await global_async_stack.aclose()

app = FastAPI(lifespan=lifespan)

@app.get('/ping')
async def handle_ping():
    try:
        result = 'pong'
        return {"response": result}
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/query")
async def handle_mcp_query(request: Request):
    data = await request.json()
    
    user_query = data.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")

    try:
        result = await run_agent_v2(user_query)
        return {
            "success" : True,
            "message" : "Query handle successful",
            "data" : result ,
            "error" : False
        }
    except* ValueError as eg:
        for e in eg.exceptions:
            server_logger.error(f"Validation error in task: {e}")
        raise HTTPException(status_code=400, detail="Invalid data in sub-task")

    except* Exception as eg:
        # This catches all other errors bundled in the ExceptionGroup
        for e in eg.exceptions:
            server_logger.exception(f"Sub-task failed: {e}")
        raise HTTPException(status_code=500, detail="Internal task group failure")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)