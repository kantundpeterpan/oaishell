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
    default_response_field: "access_token" # Only show this field by default

# TUI Customization
tui:
  aggregation_depth: 1 # Depth for grouping paths in /operations-tui
  type_icons:
    string: "📝" # Override default icons
```

## 📄 Configuration Reference

### Command Config
*   `operationId`: (String) The OpenAPI operation ID to call.
*   `description`: (String) Description shown in `/help`.
*   `mapping`: (Dict) Map CLI/State variables to OpenAPI parameters.
*   `after_call`: (Dict) Hooks to run after a successful call. Supports `save_to_state`.
*   `default_response_field`: (String) Dot-notation path to the field that should be shown by default in the response panel. Supports nested objects and arrays (e.g., `data[0].id`).
*   `force_response_field`: (Boolean) Disable schema validation for `default_response_field`.

### TUI
*   `aggregation_depth`: (Integer) Controls how paths are grouped in the interactive explorer. A depth of 1 groups by the first segment (e.g., `/users/*`). Set to 0 to disable path grouping.
*   `type_icons`: (Dict) Custom icons for data types in schema trees (`object`, `array`, `string`, `integer`, `number`, `boolean`).

### State
*   `storage`: File path for persisting state between sessions.
*   `$1`, `$2`, ...: Positional arguments from the command line.
*   `$ARG_STR`: The entire string following the command.
*   `$STATE.var`: Value currently held in the session state.

---
*Back to [Index](index.md)*
