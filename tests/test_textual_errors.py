"""Test error handling in Textual app."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.textual_app import OAIShellApp


async def test_error_handling():
    """Test error handling in the Textual app."""
    config_path = "examples/dummy_server.yaml"
    base_url = "http://localhost:8001"
    
    mgr = ConfigManager(config_path)
    cfg = mgr.config
    
    engine = OpenAIEngine(base_url)
    engine.discover(cfg.openapi_url)
    
    app = OAIShellApp(cfg, engine)
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        # Test invalid command
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = "/invalid_command"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # Test /call without operation ID
        input_widget.value = "/call"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # Test /call with invalid operation ID
        input_widget.value = "/call nonexistent_operation"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_error_handling.svg")
        print("✓ Error handling test completed!")


if __name__ == "__main__":
    asyncio.run(test_error_handling())
