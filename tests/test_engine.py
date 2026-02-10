import pytest
import os
import sys

# Ensure oai_shell is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from oai_shell.engine.client import ClientState, OpenAIEngine
from oai_shell.engine.utils import PayloadAssembler

def test_client_state():
    state = ClientState()
    state.update(session_id="123", user_id="abc")
    assert state.get("session_id") == "123"
    assert state.get("nonexistent", "default") == "default"
    assert "user_id" in state.to_dict()

def test_payload_assembler_resolve_value():
    state = ClientState()
    state.update(token="secret-token")
    assembler = PayloadAssembler(None, state)
    
    # Test state injection
    assert assembler.resolve_value("Bearer $STATE.token") == "Bearer secret-token"
    
    # Test positional args
    assert assembler.resolve_value("Hello $1", ["World"]) == "Hello World"
    assert assembler.resolve_value("$1 $2", ["A", "B"]) == "A B"

def test_payload_assembler_assemble():
    engine = OpenAIEngine("http://test.com")
    spec = {
        "paths": {
            "/user/{id}": {
                "post": {
                    "operationId": "update_user",
                    "parameters": [
                        {"name": "id", "in": "path"},
                        {"name": "X-API-Key", "in": "header"},
                        {"name": "filter", "in": "query"}
                    ]
                }
            }
        }
    }
    engine.load_spec(spec)
    assembler = PayloadAssembler(engine, ClientState())
    
    cli_params = {
        "id": "user123",
        "X-API-Key": "key123",
        "filter": "active",
        "profile.name": "Alice",
        "profile.age": "30",
        "tags": "admin"
    }
    
    payload = assembler.assemble("update_user", cli_params)
    
    assert payload["path_params"]["id"] == "user123"
    assert payload["headers"]["X-API-Key"] == "key123"
    assert payload["query_params"]["filter"] == "active"
    assert payload["body"]["profile"]["name"] == "Alice"
    assert payload["body"]["profile"]["age"] == 30  # Inferred as int
    assert payload["body"]["tags"] == "admin"

def test_type_inference():
    assembler = PayloadAssembler(None, None)
    assert assembler._infer_type("123") == 123
    assert assembler._infer_type("12.3") == 12.3
    assert assembler._infer_type("true") is True
    assert assembler._infer_type("False") is False
    assert assembler._infer_type("string") == "string"
