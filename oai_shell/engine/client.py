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
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in path_item:
                    op = path_item[method]
                    op_id = op.get("operationId")
                    if op_id:
                        self.operations[op_id] = {
                            "path": path,
                            "method": method.upper(),
                            "parameters": op.get("parameters", []),
                            "requestBody": op.get("requestBody"),
                            "summary": op.get("summary", ""),
                            "raw": op
                        }

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def call(self, operation_id: str, 
             path_params: Dict[str, Any] = None,
             query_params: Dict[str, Any] = None,
             body: Any = None,
             files: Dict[str, Any] = None) -> httpx.Response:
        
        if operation_id not in self.operations:
            raise EngineError(f"Operation {operation_id} not found")

        op = self.operations[operation_id]
        path = op["path"]
        
        if path_params:
            for k, v in path_params.items():
                path = path.replace(f"{{{k}}}", str(v))
        
        url = f"{self.base_url}{path}"
        
        # Prepare request params
        request_kwargs = {
            "method": op["method"],
            "url": url,
            "headers": self._get_headers(),
            "params": query_params,
        }
        
        if files:
            request_kwargs["files"] = files
        elif body:
            request_kwargs["json"] = body

        try:
            resp = self.client.request(**request_kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as e:
            raise EngineError(f"HTTP Request failed: {e}")
