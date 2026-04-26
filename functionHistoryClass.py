from dataclasses import dataclass

@dataclass
class FunctionHistoryType:
    function_name: str
    function_args: dict
    function_response: dict