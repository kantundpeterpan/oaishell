# Feature: Response Schemas

Response schemas should also be discovered and shown in the shell / CLI, e.g. in /operations-tui. Furthermore, based on response schemas, the yaml configuration should make it possible to define the response field that is to be shown in the response panel by default (`default_response_field` or similar). This should cover nested objects and arrays as well (good notation needed). The --debug flag should then trigger a second panel showing the nicely formatted raw response.
The `default_response_field` is to be validated against the Response schema, but an override setting should exist.

## Clarifications & Constraints
- **TUI Layout**: The `/operations-tui` should have a three-panel layout: Tree on the left, Request Schema and Response Schema on the right (stacked or side-by-side).
- **Validation**: `default_response_field` is validated against the schema. Non-conformity raises an error unless forcefully overridden.
- **Notation**: Standard dot-notation for nested objects (`obj.prop`) and bracket notation for arrays (`arr[0]`). Combined usage supported: `nested_obj.prop[0]`.

# Progress
- [x] Create branch `feature/response-schemas`
- [x] Update `oai_shell/engine/client.py` to capture response schemas
- [x] Update `oai_shell/config/models.py` to include `default_response_field`
- [x] Implement response field extraction with dot/bracket notation
- [x] Implement validation logic for `default_response_field`
- [x] Refactor `show_operations_tui` in `oai_shell/shell/runner.py` for three-panel layout
- [x] Add `--debug` flag and selective rendering in `_execute_call`

# Technical Plan

1. **Engine Updates**:
    - Modify `OpenAIEngine._parse_spec` to store `responses` in the `operations` dictionary.
    - Implement a helper to flatten or format schemas for TUI display.

2. **Configuration Updates**:
    - Add `default_response_field` and `force_response_field` (for override) to `CommandConfig`.

3. **Schema Path Resolver**:
    - Create a utility to traverse JSON/Schema using `a.b[0].c` notation.
    - This will be used for both validation (against schema) and extraction (against actual response).

4. **TUI Refactoring**:
    - Update `show_operations_tui` to use `Layout` or `Columns` for the three-panel view.
    - Left: Operations Tree.
    - Top Right: Request Schema (parameters + body).
    - Bottom Right: Response Schema (200 OK schema).

5. **Execution Updates**:
    - Update `_execute_call` to check for `--debug`.
    - If `default_response_field` is set, extract it.
    - Display in a `Panel`. If debug is on, show both panels.
