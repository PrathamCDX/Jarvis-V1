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
import json
# from functionHistoryClass import FunctionHistoryType


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# server_params = StdioServerParameters(
#     command='python',
#     # args=['todo_server.py']
#     args = [ 'calculator_server.py', 'todo_server.py']
# )

RESPONSE_PROMT = """
Role: You are a high-precision JSON serialization engine.
Task: Convert the provided function_response into a JSON string using the exact keys defined in response_schema.

Strict Requirements:

Output Format: Return ONLY a raw, valid JSON string.

No Markdown: Do NOT use code blocks (e.g., ```json), bolding, or headers.

No Prose: Do NOT include introductory text, explanations, or "Here is your JSON" style sentences.

Schema Compliance: Use the required keys from response_schema strictly. Do not add or omit keys.

JSON Integrity: Ensure all strings are double-quoted and special characters are properly escaped.
"""

SYSTEM_PROMT = """
You are a precise personal assistant capable of task decomposition and function execution.

CORE RESPONSIBILITIES:

ID VALIDATION: Every task is associated with a unique 'prompt_id'. Before initiating any action, cross-reference this ID with the provided 'function_call_history'.

DUPLICATE PREVENTION: If the history shows a function was already called with the correct arguments for a specific ID, do not repeat the call. Acknowledge the previous completion.

TASK ANALYSIS: Evaluate if the user's request can be resolved in a single step or requires multiple sub-tasks.

DECOMPOSITION:

If a single function call suffices, execute it immediately.

If the task is complex, break it down into the smallest necessary sequence of sub-tasks.

Assign the original 'prompt_id' to these sub-tasks to maintain traceability.

OPERATIONAL RULES:

Minimize steps; do not over-complicate simple requests.

Ensure every function call uses valid, extracted arguments from the prompt or history.

If data is missing to complete a task, request it from the user instead of guessing.

The task is: 
"""

tools_dict = {}
tools = []
function_history = []
text_history = []
all_mcp_tools = []
session_dict = {}
connected_servers = 0
global_async_stack = AsyncExitStack()


async def connect_all_servers(server_list: list[str], connected_servers: int):
    
    print("connected servers start : ", connected_servers)
    # if connected_servers > 0 :
    #     return None
    for server in server_list:
        print(server)
        server_params = StdioServerParameters(
            command='python',
            # args=['todo_server.py']
            args = [server] 
        )

        stdio_transport = await global_async_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        
        # 2. Initialize Session
        session = await global_async_stack.enter_async_context(ClientSession(read, write))
        session_dict[server] = session
        await session.initialize()

        mcp_tools = await session.list_tools()
        
        for tool in mcp_tools.tools:
            tools_dict[tool.name] = server
            all_mcp_tools.append(tool)
            tools.append(tool.name)
        
        connected_servers += 1 
    print(f"connected_servers : {connected_servers}")


async def run_agent_v2(query: str):
    
    print('Running agent v2')
    global function_history 
    text_history = []
    max_chaining = 50
    chaining = 0
        
    # Connect to your MCP servers
    # await connect_all_servers( server_list=server_names)
        
    prompt_unique_id = time.time_ns() + random.randint(1637, 98479)
        
    # 2. Initial Model Call
    # We wrap the core logic in a way that handles the first call and tool loops
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_text(text=f" {SYSTEM_PROMT} prompt_unique_id = {prompt_unique_id}, task: {query} "),
                types.Part.from_text(text=f" . Previous function calls: {function_history} ")
            ])
        ],
        config=types.GenerateContentConfig(tools=all_mcp_tools)
    )

    # 3. The Chaining Loop
    # We loop as long as the model wants to call tools
    while chaining < max_chaining:
        if not response.candidates:
            break

        tool_called_this_turn = False
            
        # Extract parts from the first candidate
        parts = response.candidates[0].content.parts
        
        for part in parts:
            # Handle Text Responses
            if hasattr(part, 'text') and part.text:
                text_history.append(part.text)
            
            # Handle Tool/Function Calls
            elif hasattr(part, 'function_call') and part.function_call:
                tool_called_this_turn = True
                fn_name = part.function_call.name
                fn_args = part.function_call.args
                server_name = tools_dict[fn_name]

                # Execute the tool
                function_response = await session_dict[server_name].call_tool(fn_name, fn_args)

                # Update history
                current_function_data = {
                    "id": len(function_history),
                    "promt_id": prompt_unique_id,
                    "function_server": server_name,
                    "function_name": fn_name,
                    "function_args": fn_args, 
                    "function_response": function_response.content 
                }
                function_history.append(current_function_data)

        # 4. If tools were called, feed results back to Gemini
        if tool_called_this_turn:
            chaining += 1
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=[
                    types.Content(role="user", parts=[
                        types.Part.from_text(text=f" {query} prompt_unique_id = {prompt_unique_id} "),
                        types.Part.from_text(text=f". All Previous function calls: {function_history} ")
                    ])
                ],
                config=types.GenerateContentConfig(tools=all_mcp_tools)
            )
            # Global token tracking (assuming add_token is defined globally)
            add_token(int(response.usage_metadata.total_token_count))
        else:
            # No more tools called; we are done
            break

    logger.info(text_history)
    logger.info(function_history)
    logger.info(text_history[-1] )

    final_response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_text(text=f" {RESPONSE_PROMT} function_response: {function_history[-1]["function_response"]} "),
                # types.Part.from_text(text=f"")
            ])
        ],
        config=types.GenerateContentConfig(tools=all_mcp_tools)
    )
    add_token(int(final_response.usage_metadata.total_token_count))

    json_text = (final_response.candidates[0].content.parts[-1].text)
    logger.info(json_text)
    final_json_response = parse_json_from_text(json_text)
    final_json_response["remarks"] = text_history[-1] if text_history else "No response generated."
    logger.info(final_json_response)
    return final_json_response


def parse_json_from_text(input_string):
    start_index = input_string.find('{')
    end_index = input_string.rfind('}')
    
    if start_index == -1 or end_index == -1 or end_index < start_index:
        return None
        
    json_content = input_string[start_index : end_index + 1]
    
    try:
        return json.loads(json_content)
    except json.JSONDecodeError:
        return None

async def run_agent(query: str):
    async with AsyncExitStack() as stack:
        token_count = 0
        max_chaining = 50

        await connect_all_servers(stack, server_list=server_names)
        
        
        print("Ready! (Note: Manual tool-call handling is required for production)", tools)
        count = 0 
        while True:
            prompt = query.strip()
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

            while has_function_call and chaining < max_chaining:
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