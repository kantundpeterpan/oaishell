# OAI-Shell

**OAI-Shell** is a vibecoded project—a generic, configuration-driven terminal interface for any OpenAPI-compliant backend. It transforms an API specification into a fully interactive shell with tab-completion, state management, and custom commands.

## 🔮 The Vibe
This project is **vibecoded**. It was built with AI agents, moving fast from concept to shell. It's experimental, stateful, and designed for those who want to interact with APIs at the speed of thought.

## 🚀 Key Features
*   **Modern TUI**: Built with Textual for a beautiful, reactive terminal interface.
*   **Dynamic Discovery**: Connect to any URL and explore endpoints instantly.
*   **Smart Autocomplete**: Tab-complete commands, operation IDs, and parameters.
*   **State Persistence**: Automatically tracks and injects variables like `session_id` or `auth_token`.
*   **Zero-Boilerplate**: Map complex API calls to simple slash commands via YAML.
*   **Rich UI**: Beautifully rendered responses using Markdown and Syntax highlighting.

## 🏁 Quick Start

```bash
# Run against a local API (Auto-discovery)
python3 oai_shell/main.py --base-url http://localhost:8000

# Run with a custom configuration
python3 oai_shell/main.py --config examples/stopchat.yaml

# Use legacy prompt-toolkit interface
python3 oai_shell/main.py --config examples/stopchat.yaml --legacy
```

## 📖 Documentation
Detailed information is available in the `doc/` directory:

*   **[Architecture](doc/architecture.md)**: How the engine and shell work together.
*   **[Configuration](doc/configuration.md)**: Writing your own `oai-shell.yaml`.
*   **[Textual TUI](doc/TEXTUAL_PORT.md)**: Information about the new Textual interface.
*   **[Technical Index](doc/index.md)**: Full table of contents.

---
*Generated with [Continue](https://continue.dev)*
