from fastapi import FastAPI, Request, HTTPException
import uvicorn
from client import run_agent_v2, global_async_stack
from logging_system import server_logger

app = FastAPI()

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
        return {"response": result}
    except* ValueError as eg:
        for e in eg.exceptions:
            server_logger.error(f"Validation error in task: {e}")
        raise HTTPException(status_code=400, detail="Invalid data in sub-task")

    except* Exception as eg:
        # This catches all other errors bundled in the ExceptionGroup
        for e in eg.exceptions:
            server_logger.exception(f"Sub-task failed: {e}")
        raise HTTPException(status_code=500, detail="Internal task group failure")

@app.on_event("shutdown")
async def shutdown_event():
    print("Cleaning up MCP resources...")
    await global_async_stack.aclose()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)