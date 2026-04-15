from abc import ABC
import inspect
from typing import TYPE_CHECKING, Optional, Dict, Any, List

SKILL_ARG_TYPE = int | float | str
PROBE_RET_TYPE = Optional[int | float | bool | str]

class SkillArg:
    def __init__(self, arg_name: str, arg_type: type):
        self.arg_name = arg_name
        self.arg_type = arg_type
    
    def __repr__(self):
        return f"{self.arg_name}:{self.arg_type.__name__}"

class SkillItem(ABC):
    def __init__(self, func: callable, description: str):
        self._name = func.__name__.lower()
        self._description = description
        self._func = func
        
        sig = inspect.signature(func)   
        self._args = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation == inspect.Parameter.empty:
                raise TypeError(
                    f"Function '{self._name}' parameter '{param_name}' must have an explicit type annotation. "
                    f"Example: def {self._name}({param_name}: int, ...)"
                )
            
            param_type = param.annotation
            self._args.append(SkillArg(param_name, param_type))
    
    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)    #
     
    @property
    def name(self) -> str:
        return self._name
     
    @property
    def description(self) -> str:
        return self._description
     
    @property
    def args(self) -> list[SkillArg]:
        return self._args
     
    def __repr__(self) -> str:
        return f"name: {self._name}, description: {self._description}, args: {[arg for arg in self._args]}"

    def to_tool(self) -> dict[str, Any]:
        """Convert SkillItem to OpenAI/vLLM tool format"""
        properties: Dict[str, Any] = {}
        required: List[str] = []
        
        for arg in self._args:
            arg_type_name = arg.arg_type.__name__
            if arg_type_name == 'float':
                properties[arg.arg_name] = {"type": "number"}
            elif arg_type_name == 'int':
                properties[arg.arg_name] = {"type": "integer"}
            else:
                properties[arg.arg_name] = {"type": "string"}
            required.append(arg.arg_name)
        
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": self._description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def to_ollama_tool(self) -> dict[str, Any]:
        """Alias for to_tool() for backward compatibility."""
        return self.to_tool()
