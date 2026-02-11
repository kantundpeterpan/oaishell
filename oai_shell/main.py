import argparse
import sys
import requests
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.runner import ShellRunner
from oai_shell.shell.textual_app import OAIShellApp

def main():
    parser = argparse.ArgumentParser(description="OAI-Shell: Generic OpenAPI Terminal")
    parser.add_argument("--config", help="Path to oai-shell.yaml")
    parser.add_argument("--base-url", help="Override API base URL")
    parser.add_argument("--token", help="Bearer token")
    parser.add_argument("--textual", action="store_true", help="Use Textual TUI interface (new)")
    parser.add_argument("--legacy", action="store_true", help="Use legacy prompt-toolkit interface")
    
    args = parser.parse_args()

    try:
        # 1. Load Config
        mgr = ConfigManager(args.config)
        cfg = mgr.config

        # 2. Setup Engine
        base_url = args.base_url or cfg.base_url
        if not base_url:
            print("Error: No base_url provided in config or arguments.")
            sys.exit(1)

        engine = OpenAIEngine(base_url, token=args.token)
        
        # 3. Discover API
        print(f"Discovering API at {base_url}{cfg.openapi_url}...")
        engine.discover(cfg.openapi_url)

        # 4. Start Shell
        if args.textual:
            # Use new Textual TUI
            app = OAIShellApp(cfg, engine)
            app.run()
        else:
            # Use legacy prompt-toolkit interface (default for now)
            if args.legacy:
                print("Using legacy prompt-toolkit interface...")
            runner = ShellRunner(cfg, engine)
            runner.run()

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
