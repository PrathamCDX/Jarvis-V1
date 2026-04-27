import time
import os
import asyncio
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from logging_system import logger
from config import server_names
from token_count import add_token
import random
# from functionHistoryClass import FunctionHistoryType


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# server_params = StdioServerParameters(
#     command='python',
#     # args=['todo_server.py']
#     args = [ 'calculator_server.py', 'todo_server.py']
# )

SYSTEM_PROMT = """
You are a personal assistant.
You will be given task or tasks. 
Each task will have a unique prompt id.
Validate the unique id with the history of function calls to check 
if the corresponding task has already called the function with proper args
You can break down the given task into smaller subtasts each with a function call if necessary. 
If it can be completed in a single function call not need to break it down in further sub tasks. 
The task is :  
"""

tools_dict = {}
tools = []
function_history = []
text_history = []
all_mcp_tools = []
session_dict = {}


async def connect_all_servers(stack: AsyncExitStack, server_list: list[str]):
    for server in server_list:
        server_params = StdioServerParameters(
            command='python',
            # args=['todo_server.py']
            args = [server] 
        )

        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        
        # 2. Initialize Session
        session = await stack.enter_async_context(ClientSession(read, write))
        session_dict[server] = session
        await session.initialize()

        mcp_tools = await session.list_tools()
        
        for tool in mcp_tools.tools:
            tools_dict[tool.name] = server
            all_mcp_tools.append(tool)
            tools.append(tool.name)


async def main():
    async with AsyncExitStack() as stack:
        token_count = 0

        await connect_all_servers(stack, server_list=server_names)
        
        
        print("Ready! (Note: Manual tool-call handling is required for production)", tools)
        count = 0 
        while True:
            prompt = input("\nYou: ").strip()
            prompt_unique_id = time.time_ns() + random.randint(1637, 98479)
            if prompt.lower() == 'exit': break

            # This call will fail if 'session' is passed directly as a tool
            # You must pass Gemini-compatible function declarations.
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=[
                    types.Content(role="User", parts = [
                        types.Part.from_text(text=SYSTEM_PROMT + f' . prompt_unique_id = {prompt_unique_id} . '+ prompt),
                        types.Part.from_text(text= ' . Previous function calls in order : ' + str(function_history))
                    ])
                ],
                config=types.GenerateContentConfig(tools=all_mcp_tools) 
            )

            logger.info(response)

            chaining = 1
            has_function_call = True

            while has_function_call :
                if ( response and response.candidates ):
                    candidate_list = response.candidates
                    for candidate in candidate_list:
                        if (candidate.content and candidate.content.parts):
                            gemini_parts = candidate.content.parts
                            for part in gemini_parts:
                                has_function_call = False
                                if hasattr(part, 'text') and part.text:
                                    text_history.append(part.text)
                                    continue
                                elif hasattr(part, 'function_call') and part.function_call:
                                    has_function_call = True
                                    server_name = tools_dict[part.function_call.name]
                                    current_function_data = {
                                        "id": len(function_history) ,
                                        "promt_id": prompt_unique_id,
                                        "function_server": server_name,
                                        "function_name": part.function_call.name,
                                        "function_args": part.function_call.args, 
                                        "function_response": {}
                                    }
                                    function_response = await session_dict[server_name].call_tool(
                                        current_function_data['function_name'],
                                        current_function_data['function_args']
                                    )

                                    current_function_data['function_response'] = function_response.content 
                                    function_history.append(current_function_data)

                                    response = client.models.generate_content(
                                        model="gemma-4-26b-a4b-it",
                                        contents=[
                                            types.Content(role="User", parts = [
                                                types.Part.from_text(text= prompt + f' . prompt_unique_id = {prompt_unique_id} . '),
                                                types.Part.from_text(text= ' . All Previous function calls in order : ' + str(function_history))
                                            ])
                                        ],
                                        config=types.GenerateContentConfig(tools=all_mcp_tools) 
                                    )
                                    add_token(int(response.usage_metadata.total_token_count))
                                    logger.info(response)
                                    chaining += 1 
                                    print(f"chaining : {chaining}")
                                    continue
                                else:
                                    print('random')
                                    
                else:
                    print('No gemini parts')


            

            start_time = time.perf_counter()

            token_count += int(response.usage_metadata.total_token_count)
            logger.info(text_history)
            logger.info(function_history)
            end_time = time.perf_counter()
            print('Response :' , text_history[ len(text_history) - 1 ])
            add_token(int(response.usage_metadata.total_token_count))
            logger.info(f"Execution time: {end_time - start_time:.8f} seconds")


if __name__ == "__main__":
    asyncio.run(main())