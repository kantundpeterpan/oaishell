# Feature: Response Formatting

## Description
Implement a structured way to format API responses in the shell using `rich`. This allows for extracting multiple fields, applying styles, and using different layout types like tables or markdown.

## Requirements & Constraints
- **Block-Based Architecture**: Support multiple formatting sections (blocks) per command.
- **Sub-root Scoping**: Each block can target a specific path in the response JSON.
- **Rich Integration**: Leverage `rich` for tables, markdown, and syntax-highlighted JSON.
- **Conditional Extraction**: Handle optional fields and blocks gracefully.
- **Customizable UI**: Allow setting custom titles for the response panel and individual blocks.
- **Validation**: Ensure configured paths in blocks and fields exist in the OpenAPI spec.

## Technical Plan
1. **Pydantic Models**: Added `ResponseFormattingConfig`, `FormattingBlockConfig`, and `FieldConfig` to `oai_shell/config/models.py`.
2. **Logic Integration**: Refactor `ShellRunner._execute_call` to handle the block-based `formatting` configuration.
3. **Renderer Class**: Created `ResponseRenderer` in `oai_shell/shell/runner.py` with multi-block support.
4. **Layout Support**: Implemented `list`, `table`, `markdown`, and `json` layout types.

# Progress
- [x] Update Pydantic models in `oai_shell/config/models.py`
- [x] Implement block-based `ResponseRenderer` logic
- [x] Integrate renderer into `ShellRunner`
- [x] Update startup validation for new formatting and block paths
- [x] Add example configurations (`examples/formatting.yaml`, `examples/complex_formatting.yaml`)
- [x] Test with `dummy_server.py`
