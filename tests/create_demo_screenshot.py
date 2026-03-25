"""Create a comprehensive demo screenshot."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.textual_app import OAIShellApp


async def create_demo():
    """Create a comprehensive demo screenshot."""
    config_path = "examples/dummy_server.yaml"
    base_url = "http://localhost:8001"
    
    mgr = ConfigManager(config_path)
    cfg = mgr.config
    
    engine = OpenAIEngine(base_url)
    engine.discover(cfg.openapi_url)
    
    app = OAIShellApp(cfg, engine)
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        # Execute login to show state update
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = "/login alice secret123"
        await pilot.press("enter")
        await pilot.pause(1.0)
        
        # Show help for completeness
        input_widget.value = "/help"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # Call a simple API
        input_widget.value = "/call health_health_get"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_complete_demo.svg")
        print("✓ Complete demo screenshot saved: textual_complete_demo.svg")


if __name__ == "__main__":
    asyncio.run(create_demo())
