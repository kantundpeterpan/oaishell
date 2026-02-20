
import asyncio
from typing import List
from unittest.mock import MagicMock
from oai_shell.shell.textual_app import OAIShellApp, OAIShellAutoComplete
from oai_shell.engine.client import OpenAIEngine
from oai_shell.config.models import ShellConfig
from textual_autocomplete import TargetState

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
    
    # We need to test the custom AutoComplete behavior
    ac = OAIShellAutoComplete(target="#command_input")
    
    # 1. Test Search String extraction (should only be the word under cursor)
    state = TargetState("/call get_user --i", 18)
    search_str = ac.get_search_string(state)
    print(f"Search string for '/call get_user --i': {repr(search_str)}")
    assert search_str == "--i"

    # 2. Test Candidates for '/call get_user --i' (should only return the parameter)
    items = app._get_autocomplete_items(state)
    print(f"Candidates for '--i': {[i.main.plain for i in items]}")
    # Candidate should be just '--id', NOT the full line
    assert any(i.main.plain == "--id" for i in items)
    assert not any("/call" in i.main.plain for i in items)

    # 3. Test Application of completion
    mock_target = MagicMock()
    mock_target.value = "/call get_user --i"
    mock_target.cursor_position = 18
    # Override property to avoid screen query
    type(ac).target = property(lambda self: mock_target)
    
    ac.apply_completion("--id", state)
    print(f"Target value after completion: {repr(mock_target.value)}")
    assert mock_target.value == "/call get_user --id"
    assert mock_target.cursor_position == 19 # After '--id'

    # 4. Test Completion in the middle
    # Initial: "/call get_u --id 123" (cursor at 11, after 'u')
    state = TargetState("/call get_u --id 123", 11)
    ac.apply_completion("get_user", state)
    print(f"Target value after middle completion: {repr(mock_target.value)}")
    assert mock_target.value == "/call get_user --id 123"

    print("Autocomplete scope and insertion tests passed!")

if __name__ == "__main__":
    test_autocomplete_logic()
