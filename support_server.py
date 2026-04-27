from mcp.server.fastmcp import FastMCP
from logging_system import logger
mcp = FastMCP("support_server")

@mcp.tool(description = """
                        Builds a string by replacing '_$' placeholders with values from a list.
                        Example: query="Hello _$", args=["World"] -> "Hello World"
                        """)
def query_string_builder(query: str, args: list[str]) -> str:
    """
    Builds a string by replacing '_$' placeholders with values from a list.
    Example: query="Hello _$", args=["World"] -> "Hello World"
    """
    res = ""
    arg_idx = 0
    i = 0
    
    while i < len(query):
        if i < len(query) - 1 and query[i:i+2] == "_$" and arg_idx < len(args):
            res += str(args[arg_idx])
            arg_idx += 1
            i += 2 
        else:
            res += query[i]
            i += 1
            
    return res

if __name__ == '__main__':
    mcp.run(transport="stdio")