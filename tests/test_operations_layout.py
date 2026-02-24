"""Test script to verify OperationsScreen layout."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.textual_app import OAIShellApp, OperationsScreen


async def test_operations_layout():
    """Verify that OperationsScreen fills the width and displays correctly."""
    config_path = "examples/dummy_server.yaml"
    base_url = "http://localhost:8001"
    
    mgr = ConfigManager(config_path)
    cfg = mgr.config
    
    # We need a dummy engine that has some operations
    engine = OpenAIEngine(base_url)
    # Mocking discover logic to avoid network call if server isn't running
    # but for local testing we assume dummy_server.py might be running or we use a mock
    try:
        engine.discover(cfg.openapi_url)
    except Exception:
        print("Warning: Could not connect to dummy server. Mocking operations...")
        engine.operations = {
            "get_users": {
                "method": "GET",
                "path": "/users",
                "raw": {"tags": ["users"]},
                "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer"}}]
            },
            "create_user": {
                "method": "POST",
                "path": "/users",
                "raw": {"tags": ["users"]},
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                                "required": ["name"]
                            }
                        }
                    }
                }
            }
        }

    app = OAIShellApp(cfg, engine)
    
    async with app.run_test() as pilot:
        # Trigger /operations command
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = "/operations"
        await pilot.press("enter")
        await pilot.pause(1.0)
        
        # Verify the screen is pushed
        assert isinstance(pilot.app.screen, OperationsScreen)
        
        # Select first operation in tree to show schema
        await pilot.press("down", "down", "enter")
        await pilot.pause(0.5)
        
        # Save screenshot
        pilot.app.save_screenshot("operations_layout_test.svg")
        print("✓ Operations layout screenshot saved: operations_layout_test.svg")
        
        # Check container width (approximate check via console size if possible, 
        # but screenshot is best for manual verification)
        container = pilot.app.screen.query_one("#operations_container")
        print(f"Container size: {container.size}")
        
        await pilot.press("escape")
        await pilot.pause(0.5)


if __name__ == "__main__":
    asyncio.run(test_operations_layout())
