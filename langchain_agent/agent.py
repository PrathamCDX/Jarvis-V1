from token_count import add_token
import time
import random
import json
import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from logging_system import logger
from langchain_agent.tools.calculator_tools import calculator_tools
from langchain_agent.tools.pgsql.todo_tools import todo_tools, init_tables as init_todo_tables
from langchain_agent.tools.pgsql.token_tools import token_tools, init_tables as init_token_tables

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemma-4-26b-a4b-it"

SYSTEM_PROMPT = """
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
"""

llm = ChatGoogleGenerativeAI(model=MODEL_NAME, api_key=GEMINI_API_KEY)

all_tools = calculator_tools + todo_tools + token_tools

agent = create_agent(
    llm,
    all_tools,
    system_prompt=SYSTEM_PROMPT,
)

agent_messages = []


def _extract_text_history(messages):
    text_history = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            if isinstance(msg.content, str):
                text_history.append(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_history.append(block.get("text", ""))
    return text_history


def _extract_last_tool_result(messages):
    for msg in reversed(messages):
        if msg.__class__.__name__ == 'ToolMessage' and msg.content:
            return msg.content
    return None


def _extract_function_history_full(messages):
    function_history = []
    tool_call_index = {}
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_call_index[tc["id"]] = {
                    "function_name": tc["name"],
                    "function_args": tc["args"],
                }
        if msg.__class__.__name__ == 'ToolMessage' and msg.content:
            tool_call_id = getattr(msg, 'tool_call_id', None)
            if tool_call_id and tool_call_id in tool_call_index:
                tc_info = tool_call_index[tool_call_id]
                entry = {
                    "id": len(function_history),
                    "function_name": tc_info["function_name"],
                    "function_args": tc_info["function_args"],
                    "function_response": msg.content,
                }
                function_history.append(entry)
    return function_history


def _parse_tool_result(raw_result):
    try:
        parsed = json.loads(raw_result)
        if isinstance(parsed, dict) and "result" in parsed:
            return parsed["result"]
        return parsed
    except (json.JSONDecodeError, TypeError):
        return raw_result


async def run_langchain_agent(query: str):
    logger.info(f'Running langchain agent with query: {query}')

    prompt_unique_id = time.time_ns() + random.randint(1637, 98479)

    formatted_query = f"prompt_unique_id = {prompt_unique_id}, task: {query}"

    prev_msg_count = len(agent_messages)

    input_messages = agent_messages + [HumanMessage(content=formatted_query)]

    result = await agent.ainvoke({
        "messages": input_messages,
    })

    all_messages = result.get("messages", [])

    new_messages = all_messages[prev_msg_count:]
    agent_messages.extend(new_messages)

    for msg in new_messages:
        if isinstance(msg, AIMessage) and msg.usage_metadata:
            tokens = msg.usage_metadata.get("total_tokens", 0) or 0
            print(f"tokens per message : {tokens}")
            if tokens > 0:
                add_token(tokens)

    text_history = _extract_text_history(all_messages)
    function_history = _extract_function_history_full(all_messages)

    last_tool_result = _extract_last_tool_result(new_messages)

    if last_tool_result:
        final_result = _parse_tool_result(last_tool_result)
    else:
        final_text = text_history[-1] if text_history else "No response generated."
        final_result = _parse_tool_result(final_text)

    remarks = text_history[-1] if text_history else "No response generated."

    logger.info(f"Function history: {function_history}")
    logger.info(f"Text history: {text_history}")
    logger.info(f"Final response: result={final_result}, remarks={remarks}")

    return {
        "result": final_result,
        "remarks": remarks
    }


def init_all_tables():
    init_todo_tables()
    init_token_tables()
