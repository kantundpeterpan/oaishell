# Feature: Call selection from /operations-tui

## Description
Using ENTER on an endpoint in /operations-tui should lead to `/call <operation_id>`. A sensible way of showing / predefining parameters in the call should be considered.

## Clarifications
1. **Prompt Seeding**: Preparation only (no immediate execution).
2. **Required Parameters**: Automatically append flags for required parameters that are missing from the current state.
3. **Internal Logic**: `show_operations_tui` will return the command string to the main loop.

## Technical Plan
- [x] Modify `show_operations_tui` to return an optional `str` (the command).
- [x] Implement logic to detect required parameters for an operation.
- [x] Filter out parameters already present in `self.state`.
- [x] Format the `/call` command string with the operation ID and required flags.
- [x] Update `ShellRunner.run()` to use the returned command as the default value for the next prompt.

## Progress Report
- [x] Initial setup and branching.
- [x] Logic for returning selection from TUI.
- [x] Logic for auto-appending required parameters.
- [x] Integration into the main REPL loop.
- [x] Code review for edge cases (falsy state values).
