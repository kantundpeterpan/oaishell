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
    
    payload, autofilled = assembler.assemble("update_user", cli_params)
    
    assert payload["path_params"]["id"] == "user123"
    assert payload["headers"]["X-API-Key"] == "key123"
    assert payload["query_params"]["filter"] == "active"
    assert payload["body"]["profile"]["name"] == "Alice"
    assert payload["body"]["profile"]["age"] == 30  # Inferred as int
    assert payload["body"]["tags"] == "admin"

def test_payload_assembler_autofill():
    engine = OpenAIEngine("http://test.com")
    spec = {
        "paths": {
            "/chat/{session_id}": {
                "post": {
                    "operationId": "send_message",
                    "parameters": [
                        {"name": "session_id", "in": "path"}
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user.id": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    engine.load_spec(spec)
    
    state = ClientState()
    state.update(session_id="session_789", user={"id": "user_456"})
    # Also test flat dot notation in state
    state.update(**{"some.other.param": "val"})
    
    assembler = PayloadAssembler(engine, state)
    
    # 1. Test nested autofill (session_id from path, user.id from nested state)
    cli_params = {"message": "hello"}
    payload, autofilled = assembler.assemble("send_message", cli_params)
    
    assert "session_id" in autofilled
    assert "user.id" in autofilled
    assert payload["path_params"]["session_id"] == "session_789"
    assert payload["body"]["user"]["id"] == "user_456"
    assert payload["body"]["message"] == "hello"
    
    # 2. Test precedence (CLI override)
    cli_params = {"session_id": "manual_session", "message": "hello"}
    payload, autofilled = assembler.assemble("send_message", cli_params)
    assert "session_id" not in autofilled
    assert payload["path_params"]["session_id"] == "manual_session"

def test_type_inference():
    assembler = PayloadAssembler(None, None)
    assert assembler._infer_type("123") == 123
    assert assembler._infer_type("12.3") == 12.3
    assert assembler._infer_type("true") is True
    assert assembler._infer_type("False") is False
    assert assembler._infer_type("string") == "string"
