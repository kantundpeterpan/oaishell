"""Test script for Textual TUI."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from textual.pilot import Pilot
from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.textual_app import OAIShellApp


import pytest

@pytest.mark.anyio
async def test_app():
    """Test the Textual app programmatically."""
    # Setup
    config_path = "examples/dummy_server.yaml"
    base_url = "http://localhost:8001"
    
    mgr = ConfigManager(config_path)
    cfg = mgr.config
    
    engine = OpenAIEngine(base_url)
    engine.discover(cfg.openapi_url)
    
    # Create and run app with pilot
    app = OAIShellApp(cfg, engine)
    
    async with app.run_test() as pilot:
        # Wait for app to mount
        await pilot.pause(1.0)
        
        # Initial state screenshot
        pilot.app.save_screenshot("textual_initial.svg")
        print("✓ Screenshot 1: Initial state")
        
        # Test /help command
        await pilot.click("#command_input")
        await pilot.press(*"/help")
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # Take a screenshot
        pilot.app.save_screenshot("textual_help.svg")
        print("✓ Screenshot 2: Help command")
        
        # Test /operations command
        await pilot.click("#command_input")
        await pilot.press(*"/operations")
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # Take another screenshot
        pilot.app.save_screenshot("textual_operations.svg")
        print("✓ Screenshot 3: Operations list")
        
        # Test /state command
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = "/state"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_state.svg")
        print("✓ Screenshot 4: State display")
        
        # Test /login command (custom command)
        input_widget.value = "/login alice secret123"
        await pilot.press("enter")
        await pilot.pause(1.0)
        
        pilot.app.save_screenshot("textual_login.svg")
        print("✓ Screenshot 5: Login command executed")
        # Test autocomplete scope and parameter suggestions
        await pilot.click("#command_input")
        # Type /call 
        for c in "/call ":
            await pilot.press(c)
        await pilot.pause(0.2)
        
        # Should show operations. Type 'h' for health
        await pilot.press("h")
        await pilot.pause(0.2)
        # Select first suggestion (health_health_get)
        await pilot.press("enter")
        await pilot.pause(0.2)
        
        # Now at '/call health_health_get '. Should show no suggestions (no params)
        # Type a space and then '--' to see if suggestions appear (even if none for health)
        await pilot.press(" ")
        await pilot.press("-", "-")
        await pilot.pause(0.2)
        
        # Try a more complex one: /call create_item_items_post
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = ""
        for c in "/call create_item_items_post ":
            await pilot.press(c)
        await pilot.pause(0.5)
        
        # Should show parameters for create_item_items_post (item.name, item.details.color, etc.)
        pilot.app.save_screenshot("textual_autocomplete_params.svg")
        
        # Select one
        await pilot.press("enter")
        await pilot.pause(0.2)
        
        # Test that entering a parameter hides it from suggestions
        # Current value should be "/call create_item_items_post --item.name "
        await pilot.press("-", "-")
        await pilot.pause(0.2)
        pilot.app.save_screenshot("textual_autocomplete_params_filtered.svg")
        
        print("\n✓ Test completed successfully!")
        print("✓ Screenshots saved: textual_initial.svg, textual_help.svg, textual_operations.svg, textual_state.svg, textual_login.svg")


if __name__ == "__main__":
    asyncio.run(test_app())

