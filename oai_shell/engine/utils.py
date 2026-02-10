import re
from typing import Dict, Any, Optional, List
from ..engine.client import OpenAIEngine, ClientState

class PayloadAssembler:
    """Assembles API payloads from CLI input and state."""
    
    def __init__(self, engine: OpenAIEngine, state: ClientState):
        self.engine = engine
        self.state = state

    def resolve_value(self, template: str, args: List[str] = None) -> Any:
        """Resolves $1, $STATE.var, etc."""
        if not isinstance(template, str):
            return template
            
        # Positional args: $1, $2...
        if args:
            for i, val in enumerate(args, 1):
                if template == f"${i}":
                    return val
                template = template.replace(f"${i}", str(val))
        
        # State: $STATE.var
        def state_replacer(match):
            var_name = match.group(1)
            return str(self.state.get(var_name, match.group(0)))
            
        template = re.sub(r'\$STATE\.([a-zA-Z_][a-zA-Z0-9_]*)', state_replacer, template)
        return template

    def assemble(self, operation_id: str, cli_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Sorts flat params into path, query, body based on OpenAPI spec."""
        op = self.engine.operations.get(operation_id)
        if not op:
            return {}

        payload = {"path_params": {}, "query_params": {}, "body": {}}
        
        # Determine locations
        spec_params = op.get("parameters", [])
        path_template = op.get("path", "")
        path_vars = re.findall(r'\{([^}]+)\}', path_template)
        
        for key, value in cli_params.items():
            placed = False
            # Check path
            if key in path_vars:
                payload["path_params"][key] = value
                placed = True
            # Check spec (query/header/cookie)
            if not placed:
                for p in spec_params:
                    if p["name"] == key:
                        if p["in"] == "query":
                            payload["query_params"][key] = value
                            placed = True
                        break
            # Default to body
            if not placed:
                payload["body"][key] = value
                
        return payload
