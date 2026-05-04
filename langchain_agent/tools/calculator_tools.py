import json
from langchain_core.tools import tool


@tool
def add(a: float, b: float) -> str:
    """Add two numbers together and return the sum"""
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": a + b
    })


@tool
def subtract(a: float, b: float) -> str:
    """Subtract b from a and return the difference"""
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": a - b
    })


@tool
def multiply(a: float, b: float) -> str:
    """Multiply two numbers together and return the product"""
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": a * b
    })


@tool
def divide(a: float, b: float) -> str:
    """Divide a by b and return the result. Returns error if b is zero"""
    if b == 0:
        raise ZeroDivisionError("Error: Cannot divide by zero")
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": a / b
    })


@tool
def power(base: float, exponent: float) -> str:
    """Raise base to the power of exponent and return the result"""
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": base ** exponent
    })


@tool
def modulo(a: float, b: float) -> str:
    """Return the remainder when a is divided by b. Returns error if b is zero"""
    if b == 0:
        raise ZeroDivisionError("Error: Cannot modulo by zero")
    return json.dumps({
        "response_schema": "create a JSON object with the keys : result",
        "result": a % b
    })


calculator_tools = [add, subtract, multiply, divide, power, modulo]
