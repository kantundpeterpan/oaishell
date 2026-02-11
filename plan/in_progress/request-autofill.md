# Feature: Request Autofill

Missing request parameters (path, body, query) should be looked up in state and used if found. This should be default behaviour and not needed to be configured in the yaml.
Notification of parameter autofill should be similar to that of saving values to state from response.

## Clarifications & Constraints
1. **Scope**: Autofill all missing parameters found in state (not just required ones).
2. **Precedence**: CLI parameters always take precedence over state variables.
3. **Nesting**: 
    - Support flat state keys matching dot-notation (e.g., state has `user.id`).
    - Support nested state objects (e.g., state has `{"user": {"id": 123}}`).
4. **Notification**: Display autofilled parameters in the UI using a style similar to state updates: `[dim italic]Autofilled from state: {key}[/dim italic]`.

## Progress
- [ ] Implement state lookup logic in `PayloadAssembler`
- [ ] Update `PayloadAssembler.assemble` to return metadata about autofilled keys
- [ ] Update `ShellRunner` to display notifications
- [ ] Remove/Integrate redundant `auto_inject` logic
- [ ] Verify with tests

## Technical Plan
1. **Engine Update (`oai_shell/engine/utils.py`)**:
    - Add `_get_from_state(key)` to `PayloadAssembler` to handle flat vs nested lookup in `self.state.data`.
    - Modify `assemble(operation_id, cli_params)`:
        - Identify all potential parameters for the operation.
        - For each missing parameter, try `_get_from_state`.
        - Track autofilled keys.
        - Return `(payload, autofilled_keys)`.
2. **Shell Update (`oai_shell/shell/runner.py`)**:
    - Update `_execute_call` to handle the new return signature.
    - Loop through `autofilled_keys` and `console.print` the notification.
    - Remove the manual `auto_inject` loop in `_execute_call`.
