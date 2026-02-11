from oai_shell.engine.client import OpenAIEngine

def test_common_prefix_detection():
    engine = OpenAIEngine("http://test.com")
    spec = {
        "paths": {
            "/api/v1/users": {"get": {"operationId": "getUsers"}},
            "/api/v1/items": {"get": {"operationId": "getItems"}},
            "/api/v1/status": {"get": {"operationId": "getStatus"}}
        }
    }
    engine.load_spec(spec)
    assert engine.common_prefix == "/api/v1/"
    assert engine.operations["getUsers"]["display_path"] == "/users"
    assert engine.operations["getItems"]["display_path"] == "/items"

def test_no_common_prefix():
    engine = OpenAIEngine("http://test.com")
    spec = {
        "paths": {
            "/users": {"get": {"operationId": "getUsers"}},
            "/items": {"get": {"operationId": "getItems"}},
            "/status": {"get": {"operationId": "getStatus"}}
        }
    }
    engine.load_spec(spec)
    assert engine.common_prefix == ""
    assert engine.operations["getUsers"]["display_path"] == "/users"

def test_partial_slash_boundary():
    engine = OpenAIEngine("http://test.com")
    spec = {
        "paths": {
            "/api/v1/users": {"get": {"operationId": "getUsers"}},
            "/api/v2/items": {"get": {"operationId": "getItems"}},
        }
    }
    engine.load_spec(spec)
    # Common prefix is "/api/" because they diverge after that
    assert engine.common_prefix == "/api/"
    assert engine.operations["getUsers"]["display_path"] == "/v1/users"
