from typing import Optional, List, Dict, Any, Union
import os
import json
import logging
import httpx
from pathlib import Path

logger = logging.getLogger("oai_shell.engine")

class EngineError(Exception):
    pass

class ClientState:
    """Manages session state and variables."""
    def __init__(self, persistence_file: Optional[str] = None):
        self.persistence_file = persistence_file
        self.data: Dict[str, Any] = {}
        if persistence_file:
            self.load()

    def update(self, **kwargs):
        self.data.update(kwargs)
        if self.persistence_file:
            self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def save(self):
        if self.persistence_file:
            with open(self.persistence_file, 'w') as f:
                json.dump(self.data, f)

    def load(self):
        p = Path(self.persistence_file)
        if p.exists():
            with open(p, 'r') as f:
                self.data = json.load(f)

    def to_dict(self) -> Dict[str, Any]:
        return self.data

class OpenAIEngine:
    """Generic OpenAPI-driven request engine."""
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(timeout=30.0)
        self.spec: Dict[str, Any] = {}
        self.operations: Dict[str, Dict[str, Any]] = {}

    def set_token(self, token: str):
        self.token = token

    def load_spec(self, spec_data: Dict[str, Any]):
        self.spec = spec_data
        self._parse_spec()

    def _parse_spec(self):
        paths = self.spec.get("paths", {})
        
        # 1. Identify common prefix
        common_prefix = ""
        if paths:
            path_list = list(paths.keys())
            if len(path_list) > 1:
                # Find longest common prefix among all paths
                s1, s2 = min(path_list), max(path_list)
                for i, c in enumerate(s1):
                    if c != s2[i]:
                        common_prefix = s1[:i]
                        break
                else:
                    common_prefix = s1
                
                # Ensure we break at a slash boundary
                if common_prefix and not common_prefix.endswith('/'):
                    last_slash = common_prefix.rfind('/')
                    if last_slash != -1:
                        common_prefix = common_prefix[:last_slash+1]
                    else:
                        common_prefix = ""
                
                # Special case: if common_prefix is just "/", we treat it as no common prefix
                if common_prefix == "/":
                    common_prefix = ""
            elif len(path_list) == 1:
                # If only one path, we don't really have a "common" prefix to strip in a useful way
                # unless it has multiple segments. But let's stick to 2+ for safety or just keep it.
                pass

        self.common_prefix = common_prefix

        for path, path_item in paths.items():
            # Strip common prefix for internal representation
            display_path = path[len(common_prefix):] if path.startswith(common_prefix) else path
            if not display_path.startswith('/'):
                display_path = '/' + display_path

            for method in ["get", "post", "put", "delete", "patch"]:
                if method in path_item:
                    op = path_item[method]
                    op_id = op.get("operationId")
                    if op_id:
                        self.operations[op_id] = {
                            "path": path,
                            "display_path": display_path,
                            "method": method.upper(),
                            "parameters": op.get("parameters", []),
                            "requestBody": op.get("requestBody"),
                            "summary": op.get("summary", ""),
                            "raw": op
                        }

    def resolve_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves $ref in a schema object."""
        if not isinstance(schema, dict):
            return schema
        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")
            # Assuming #/components/schemas/...
            curr = self.spec
            for part in ref_path[1:]:
                curr = curr.get(part, {})
            # Merge original schema (minus $ref) into resolved for constraints
            resolved = curr.copy()
            for k, v in schema.items():
                if k != "$ref": resolved[k] = v
            return self.resolve_schema(resolved)
        return schema

    def get_params_for_operation(self, op_id: str) -> List[Dict[str, Any]]:
        """Returns flattened list of all available parameters (Path, Query, Body, etc)."""
        op = self.operations.get(op_id)
        if not op: return []

        all_params = []
        # 1. Standard Parameters (Path, Query, Header)
        for p in op.get("parameters", []):
            all_params.append({
                "name": p["name"],
                "in": p.get("in", "query"),
                "type": p.get("schema", {}).get("type", "string"),
                "required": p.get("required", False)
            })

        # 2. Request Body
        body = op.get("requestBody")
        if body:
            content = body.get("content", {})
            # We primarily support JSON
            json_schema = content.get("application/json", {}).get("schema")
            if json_schema:
                all_params.extend(self._flatten_schema(json_schema, prefix=""))

        return all_params

    def _flatten_schema(self, schema: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        """Recursively flattens a schema into dot-notation parameters."""
        schema = self.resolve_schema(schema)
        params = []
        
        s_type = schema.get("type")
        if s_type == "object":
            props = schema.get("properties", {})
            for name, prop in props.items():
                full_name = f"{prefix}{name}"
                params.extend(self._flatten_schema(prop, prefix=f"{full_name}."))
        else:
            # Leaf node
            if prefix:
                params.append({
                    "name": prefix.rstrip('.'),
                    "in": "body",
                    "type": s_type or "any",
                    "required": False # Complex to determine accurately from here
                })
        return params

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def discover(self, openapi_url: str = "/openapi.json"):
        url = openapi_url
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"{self.base_url}/{openapi_url.lstrip('/')}"
        
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            self.load_spec(resp.json())
            return self.spec
        except Exception as e:
            raise EngineError(f"Failed to discover API at {url}: {e}")

    def call(self, operation_id: str, 
             path_params: Dict[str, Any] = None,
             query_params: Dict[str, Any] = None,
             body: Any = None,
             files: Dict[str, Any] = None,
             headers: Dict[str, str] = None,
             stream: bool = False) -> Union[httpx.Response, httpx.Response]:
        
        if operation_id not in self.operations:
            raise EngineError(f"Operation {operation_id} not found")

        op = self.operations[operation_id]
        path = op["path"]
        
        if path_params:
            for k, v in path_params.items():
                path = path.replace(f"{{{k}}}", str(v))
        
        url = f"{self.base_url}{path}"
        
        # Prepare request params
        all_headers = self._get_headers()
        if headers:
            all_headers.update(headers)
            
        request_kwargs = {
            "method": op["method"],
            "url": url,
            "headers": all_headers,
            "params": query_params,
        }
        
        if files:
            request_kwargs["files"] = files
        elif body:
            request_kwargs["json"] = body

        try:
            if stream:
                # Returns a context manager for streaming
                return self.client.stream(**request_kwargs)
            else:
                resp = self.client.request(**request_kwargs)
                resp.raise_for_status()
                return resp
        except httpx.HTTPError as e:
            raise EngineError(f"HTTP Request failed: {e}")
