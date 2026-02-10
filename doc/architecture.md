# OAI-Shell Architecture

OAI-Shell is designed as a modular pipeline that transforms a static OpenAPI specification into a live terminal environment.

## 🏗️ Core Components

### 1. The Engine (`oai_shell/engine/client.py`)
The Engine is the heart of the system. It handles:
*   **Spec Ingestion**: Parsing `openapi.json` into a searchable dictionary of operations.
*   **Schema Discovery**: Recursive `$ref` resolution and flattening of complex request models.
*   **HTTP Communication**: Using `httpx` to manage REST requests and Streaming (SSE).
*   **Authentication**: Handling Bearer tokens and custom security headers.

### 2. The Config Manager (`oai_shell/config/`)
Loads the `oai-shell.yaml` file (if provided). It uses **Pydantic** models to validate:
*   **Custom Commands**: Aliases for complex API operations.
*   **State Rules**: Where to save data and what to inject automatically.

### 3. The Payload Assembler (`oai_shell/engine/utils.py`)
A specialized utility that bridges the gap between CLI flags and API requirements:
*   **Mapping**: Uses the OpenAPI spec to decide if a flag like `--id` belongs in the URL path, the headers, or the JSON body.
*   **Nesting**: Parses dot-notation (e.g., `--user.name`) into structured JSON objects.
*   **Type Inference**: Automatically casts strings to integers, floats, or booleans.

### 4. The Shell Runner (`oai_shell/shell/runner.py`)
The UI layer built on `prompt_toolkit`. It provides:
*   **The REPL**: Persistent command loop with history.
*   **Interactive Explorer**: Hierarchical TUI (`/operations-tui`) for browsing the API.
*   **Autocomplete**: Context-aware suggestions for commands, operation IDs, and nested body parameters.
*   **Output Rendering**: Uses `rich` for beautiful JSON and Markdown formatting.

---
*Back to [Index](index.md)*
