import argparse
import sys
import requests
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine
from oai_shell.shell.runner import ShellRunner

def main():
    parser = argparse.ArgumentParser(description="OAI-Shell: Generic OpenAPI Terminal")
    parser.add_argument("--config", help="Path to oai-shell.yaml")
    parser.add_argument("--base-url", help="Override API base URL")
    parser.add_argument("--token", help="Bearer token")
    
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
        runner = ShellRunner(cfg, engine)
        runner.run()

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
