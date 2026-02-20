
import asyncio
from typing import List
from unittest.mock import MagicMock
from oai_shell.shell.textual_app import OAIShellApp
from oai_shell.engine.client import OpenAIEngine
from oai_shell.config.models import ShellConfig

def test_autocomplete_logic():
    # Mocking Engine and Config
    engine = MagicMock(spec=OpenAIEngine)
    engine.base_url = "http://test"
    engine.operations = {
        "get_user": {"path": "/users/{id}", "method": "GET"},
        "create_item": {"path": "/items", "method": "POST"}
    }
    engine.get_params_for_operation.return_value = [
        {"name": "id", "in": "path", "type": "integer", "required": True},
        {"name": "name", "in": "query", "type": "string", "required": False}
    ]
    
    config = MagicMock(spec=ShellConfig)
    config.name = "Test"
    config.commands = {}
    config.state = MagicMock()
    config.state.storage = None
    config.state.defaults = {}
    
    app = OAIShellApp(config, engine)
    
    class MockInputState:
        def __init__(self, text, cursor_position):
            self.text = text
            self.cursor_position = cursor_position

    # 1. Test Command Completion
    state = MockInputState("/he", 3)
    items = app._get_autocomplete_items(state)
    print(f"Items for '/he': {[str(i.main) for i in items]}")
    assert any("/help" in str(item.main) for item in items)
    
    # 2. Test Operation Completion after /call
    state = MockInputState("/call ", 6)
    items = app._get_autocomplete_items(state)
    print(f"Items for '/call ': {[str(i.main) for i in items]}")
    assert any("get_user" in str(item.main) for item in items)
    
    # 3. Test Parameter Completion
    state = MockInputState("/call get_user --", 18)
    items = app._get_autocomplete_items(state)
    print(f"Items for '/call get_user --': {[str(i.main) for i in items]}")
    assert any("--id" in str(item.main) for item in items)
    assert any("(path) integer" in str(item.prefix) for item in items)
    
    # 4. Test Completion with trailing text (preserving it)
    state = MockInputState("/call get_u --id 123", 11) # Cursor after 'u'
    items = app._get_autocomplete_items(state)
    print(f"Items for '/call get_u --id 123': {[str(i.main) for i in items]}")
    assert any("get_user" in str(item.main) for item in items)
    assert any("--id 123" in str(item.main) for item in items)

    # 5. Test Parameter Filtering (don't suggest already used)
    state = MockInputState("/call get_user --id 1 --", 24)
    items = app._get_autocomplete_items(state)
    print(f"Items for '/call get_user --id 1 --':")
    for item in items:
        print(f"  - main: {repr(item.main)}, prefix: {repr(item.prefix)}")
    
    # We want to ensure that '--id' is not being suggested as a NEW parameter.
    # Since '--id' is already in the base_text, we check if any suggestion 
    # has a SECOND occurrence of '--id' or if the part after the base_text contains '--id'.
    base_text = "/call get_user --id 1 "
    for item in items:
        suggestion_main = str(item.main)
        completion_part = suggestion_main[len(base_text):]
        assert "--id" not in completion_part, f"Should not suggest already used parameter '--id' in completion part: {completion_part}"
    
    assert any("--name" in str(item.main) for item in items)

    print("Autocomplete logic tests passed!")

if __name__ == "__main__":
    test_autocomplete_logic()
