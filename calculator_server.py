from mcp.server.fastmcp import FastMCP

mcp = FastMCP('calculator_server')

@mcp.tool(description="Add two numbers together and return the sum")
def add(a: float, b: float) -> dict:
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : a + b 
    }

@mcp.tool(description="Subtract b from a and return the difference")
def subtract(a: float, b: float) -> dict:
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : a - b
    }

@mcp.tool(description="Multiply two numbers together and return the product")
def multiply(a: float, b: float) -> dict:
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : a * b
    }

@mcp.tool(description="Divide a by b and return the quotient. Returns error if b is zero")
def divide(a: float, b: float) -> dict:
    if b == 0:
        raise ZeroDivisionError("Error: Cannot divide by zero")
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : a / b
    }

@mcp.tool(description="Raise base to the power of exponent and return the result")
def power(base: float, exponent: float) -> dict:
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : base ** exponent
    }

@mcp.tool(description="Return the remainder when a is divided by b. Returns error if b is zero")
def modulo(a: float, b: float) -> dict:
    if b == 0:
        raise ZeroDivisionError("Error: Cannot modulo by zero")
    return {
        "response_schema" : "create a JSON object with the keys : result ",
        "result" : a % b
    }

if __name__ == '__main__':
    mcp.run(transport='stdio')