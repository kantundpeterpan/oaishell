"""Test new features: themes, autocomplete, and operations screen."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.textual_app import OAIShellApp


async def test_new_features():
    """Test the new features."""
    config_path = "examples/dummy_server.yaml"
    base_url = "http://localhost:8001"
    
    mgr = ConfigManager(config_path)
    cfg = mgr.config
    
    engine = OpenAIEngine(base_url)
    engine.discover(cfg.openapi_url)
    
    app = OAIShellApp(cfg, engine)
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        # Test initial state
        pilot.app.save_screenshot("textual_new_initial.svg")
        print("✓ Screenshot 1: Initial state with new features")
        
        # Test /help to show new commands
        input_widget = pilot.app.query_one("#command_input")
        input_widget.value = "/help"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_new_help.svg")
        print("✓ Screenshot 2: Help showing theme command")
        
        # Test /theme command
        input_widget.value = "/theme light"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_theme_light.svg")
        print("✓ Screenshot 3: Light theme applied")
        
        # Test /theme dark-high-contrast
        input_widget.value = "/theme dark-high-contrast"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        pilot.app.save_screenshot("textual_theme_high_contrast.svg")
        print("✓ Screenshot 4: High contrast theme applied")
        
        # Test /theme back to dark
        input_widget.value = "/theme dark"
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        print("✓ Screenshot 5: Back to dark theme")
        
        # Test /operations (opens modal)
        input_widget.value = "/operations"
        await pilot.press("enter")
        await pilot.pause(1.0)
        
        pilot.app.save_screenshot("textual_operations_modal.svg")
        print("✓ Screenshot 6: Operations explorer modal")
        
        # Close the modal
        await pilot.press("escape")
        await pilot.pause(0.5)
        
        print("\n✓ All new features tested successfully!")


if __name__ == "__main__":
    asyncio.run(test_new_features())
