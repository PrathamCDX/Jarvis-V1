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
break down the given task into smaller subtasts each with a function call. the task is :  
"""

tools_dict = {}
tools = []
function_history = []
text_history = []
all_mcp_tools = []


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
        await session.initialize()

        mcp_tools = await session.list_tools()
        
        for tool in mcp_tools.tools:
            tools_dict[tool.name] = server
            all_mcp_tools.append(tool)
            tools.append(tool.name)


async def main():
    async with AsyncExitStack() as stack:
        # 1. Connect to MCP Server
        # stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        # read, write = stdio_transport
        
        # # 2. Initialize Session
        # session = await stack.enter_async_context(ClientSession(read, write))
        # await session.initialize()

        # # 3. Get tools from MCP and format for Gemini
        # mcp_tools = await session.list_tools()
        # tools = []
        
        # for tool in mcp_tools.tools:
        #     tools_dict[tool.name] = 'todo_server.py'
        #     tools.append(tool.name)

        await connect_all_servers(stack, server_list=server_names)
        
        
        print("Ready! (Note: Manual tool-call handling is required for production)", tools)
        count = 0 
        while True:
            prompt = input("\nYou: ").strip()
            if prompt.lower() == 'exit': break

            # This call will fail if 'session' is passed directly as a tool
            # You must pass Gemini-compatible function declarations.
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=[
                    types.Content(role="User", parts = [
                        types.Part.from_text(text=SYSTEM_PROMT + prompt),
                        types.Part.from_text(text= 'Previous function calls in order : ' + str(function_history))
                    ])
                ],
                config=types.GenerateContentConfig(tools=all_mcp_tools) 
            )

            logger.info(response)


            if ( response and response.candidates ):
                candidate_list = response.candidates
                # gemini_parts = response.candidates.content.parts
                # print('Gemini parts', candidate_list)
                for candidate in candidate_list:
                    if (candidate.content and candidate.content.parts):
                        gemini_parts = candidate.content.parts
                        # print('gemini_parts : ', gemini_parts)
                        for part in gemini_parts:
                            if hasattr(part, 'text') and part.text:
                                text_history.append(part.text)
                            elif hasattr(part, 'function_call') and part.function_call:
                                function_history.append({
                                    "id": len(function_history) ,
                                    "function_server": tools_dict[part.function_call.name],
                                    "function_name": part.function_call.name,
                                    "function_args": part.function_call.args, 
                                    "function_res": {}
                                })
                            else:
                                print('random')
                                
            else:
                print('No gemini parts')

            # print('Current function stack for ' , count , ' is ', function_history )
            logger.info(text_history)
            logger.info(function_history)
            # print(f"Gemini: {response}")

if __name__ == "__main__":
    # Fixed the run call
    asyncio.run(main())