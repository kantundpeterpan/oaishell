# Repository Overview

## Project Description
**OAI-Shell** is a generic, configuration-driven terminal interface for any OpenAPI-compliant backend. It transforms a static OpenAPI specification into a fully interactive shell environment.
- **Purpose**: Provide a stateful, interactive CLI for exploring and interacting with REST APIs.
- **Goals**: Zero-boilerplate API interaction, state persistence (tokens, IDs), and dynamic endpoint discovery.
- **Key Technologies**: 
    - **Python 3.10+**
    - **httpx**: For async-capable HTTP requests and SSE streaming.
    - **prompt_toolkit**: For the interactive REPL and advanced tab-completion.
    - **rich**: For beautiful TUI rendering, tables, and hierarchical trees.
    - **Pydantic**: For configuration validation and state management.
    - **PyYAML**: For loading custom command mappings.

## Architecture Overview
The system follows a modular pipeline:
1.  **Discovery**: Fetches `openapi.json` from the target backend.
2.  **Engine**: Parses the spec, resolves `$ref` recursively, detects common path prefixes (e.g., `/api/v1/`), and manages HTTP calls.
3.  **Payload Assembler**: Maps flat CLI flags (`--param`) to the correct OpenAPI location (Path, Query, Header, or Body) and handles nested dot-notation.
4.  **Shell/REPL**: Handles user input, provides context-aware completions, and renders the TUI (including a hierarchical API explorer).
5.  **State Manager**: Persists variables (like `session_id`) and auto-injects them into subsequent requests.

## Directory Structure
- `oai_shell/`: Root package.
    - `main.py`: Entry point for the CLI.
    - `engine/`:
        - `client.py`: `OpenAIEngine` (HTTP logic, spec parsing, $ref resolution) and `ClientState`.
        - `utils.py`: `PayloadAssembler` (mapping CLI flags to JSON payloads).
    - `config/`:
        - `manager.py`: Config loading logic.
        - `models.py`: Pydantic schemas for `oai-shell.yaml`.
    - `shell/`:
        - `runner.py`: `ShellRunner` (REPL loop, TUI navigation, `/operations-tui`).
- `examples/`: Sample configuration files (e.g., `stopchat.yaml`).
- `tests/`: Unit tests and a `dummy_server.py` (FastAPI) for integration testing.
- `plan/`: Development roadmap and feature tracking.
    - `features.md`: Backlog of planned features.
    - `in_progress/`: Tracking files for features currently under development.
    - `implemented/`: Archived tracking files for completed features.
- `.continue/`: Agentic workflows and local rules.
    - `agents/`: Custom AI agents (e.g., `feature-orchestrator.md`).
    - `rules/`: Coding standards and review guidelines.

## Development Workflow
- **Run**: `python3 oai_shell/main.py --base-url <url>`
- **Test Server**: `python3 tests/dummy_server.py` (FastAPI server for testing all features).
- **Testing**: `pytest tests/`
- **Dependencies**: `httpx`, `prompt_toolkit`, `rich`, `pydantic`, `pyyaml`.
- **Environment**: Python virtual environment recommended.
