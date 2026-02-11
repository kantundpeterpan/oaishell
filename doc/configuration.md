# Configuration Guide

OAI-Shell can run entirely without a configuration file, but you can use `oai-shell.yaml` to create a "branded" experience for your API.

## 📄 File Structure

```yaml
name: "MyAPI-Shell"
base_url: "http://localhost:8080"
openapi_url: "/openapi.json"

# State management
state:
  storage: ".session-state.json"
  auto_inject:
    - "session_id" # Automatically send this if the API needs it
  defaults:
    language: "en"

# Custom Slash Commands
commands:
  /login:
    operationId: "post_auth_login"
    description: "Authenticate with the server"
    mapping:
      username: "$1" # First argument after /login
      password: "$2" # Second argument
    after_call:
      save_to_state:
        token: "json:access_token"

# TUI Customization
tui:
  aggregation_depth: 1 # Depth for grouping paths in /operations-tui
```

## 📄 Configuration Reference

### TUI
*   `aggregation_depth`: (Integer) Controls how paths are grouped in the interactive explorer. A depth of 1 groups by the first segment (e.g., `/users/*`). Set to 0 to disable path grouping.

### State
*   `storage`: File path for persisting state between sessions.
*   `$1`, `$2`, ...: Positional arguments from the command line.
*   `$ARG_STR`: The entire string following the command.
*   `$STATE.var`: Value currently held in the session state.

---
*Back to [Index](index.md)*
