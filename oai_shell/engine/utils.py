import re
from typing import Dict, Any, Optional, List, Union, Tuple
from ..engine.client import OpenAIEngine, ClientState

class SchemaPathResolver:
    """Utility to traverse JSON/Schema with a.b[0].c notation."""

    @staticmethod
    def resolve_data(data: Any, path: str) -> Any:
        """Extracts data from a JSON object using dot and bracket notation."""
        if not path:
            return data
            
        # Tokenize: a.b[0].c -> ['a', 'b', '[0]', 'c']
        tokens = re.findall(r'[^.\[\]]+|\[\d+\]', path)
        curr = data
        try:
            for token in tokens:
                if token.startswith('[') and token.endswith(']'):
                    idx = int(token[1:-1])
                    curr = curr[idx]
                else:
                    curr = curr[token]
            return curr
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def validate_path(schema: Dict[str, Any], path: str, engine: OpenAIEngine) -> bool:
        """Validates if a path exists within an OpenAPI schema."""
        if not path:
            return True
            
        tokens = re.findall(r'[^.\[\]]+|\[\d+\]', path)
        curr = engine.resolve_schema(schema)
        
        try:
            for token in tokens:
                s_type = curr.get("type")
                if token.startswith('[') and token.endswith(']'):
                    if s_type != "array":
                        return False
                    curr = engine.resolve_schema(curr.get("items", {}))
                else:
                    if s_type != "object":
                        return False
                    props = curr.get("properties", {})
                    if token not in props:
                        return False
                    curr = engine.resolve_schema(props[token])
            return True
        except (KeyError, AttributeError):
            return False

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

    def assemble(self, operation_id: str, cli_params: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Sorts flat params into path, query, body based on OpenAPI spec.
        
        Returns (payload, autofilled_keys).
        """
        # 1. Identify all potential parameters for this operation
        all_spec_params = self.engine.get_params_for_operation(operation_id)
        
        # 2. Autofill missing params from state
        autofilled_keys = []
        for p in all_spec_params:
            name = p["name"]
            if name not in cli_params:
                val = self._get_from_state(name)
                if val is not None:
                    cli_params[name] = val
                    autofilled_keys.append(name)

        # Convert any numeric strings in cli_params to actual numbers if needed
        cli_params = {k: self._infer_type(v) for k, v in cli_params.items()}
        
        op = self.engine.operations.get(operation_id)
        if not op:
            return {}, []

        payload = {"path_params": {}, "query_params": {}, "body": {}, "headers": {}}
        
        # Determine locations
        spec_params = op.get("parameters", [])
        path_template = op.get("path", "")
        path_vars = re.findall(r'\{([^}]+)\}', path_template)
        
        # Determine nesting (dot notation)
        nested_params = {}
        for key, value in cli_params.items():
            if '.' in key:
                parts = key.split('.')
                curr = nested_params
                for p in parts[:-1]:
                    if p not in curr: curr[p] = {}
                    curr = curr[p]
                curr[parts[-1]] = value
            else:
                nested_params[key] = value

        for key, value in nested_params.items():
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
                        elif p["in"] == "header":
                            payload["headers"][key] = value
                            placed = True
                        break
            # Default to body
            if not placed:
                payload["body"][key] = value
                
        return payload, autofilled_keys

    def _get_from_state(self, key: str) -> Any:
        """Looks up a key in state, supporting both flat dot-notation and nested objects."""
        # 1. Direct match (flat or exact)
        val = self.state.get(key)
        if val is not None:
            return val
            
        # 2. Nested match using SchemaPathResolver logic
        return SchemaPathResolver.resolve_data(self.state.to_dict(), key)

    def _infer_type(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value.lower() == 'true': return True
        if value.lower() == 'false': return False
        try:
            if '.' in value: return float(value)
            return int(value)
        except ValueError:
            return value
