# Feature: Response Formatting

## Description
Implement a structured way to format API responses in the shell using `rich`. This allows for extracting multiple fields, applying styles, and using different layout types like tables or markdown.

## Requirements & Constraints
- **Structured Mapping**: Use a list of fields in the YAML configuration.
- **Rich Integration**: Leverage `rich` for tables, markdown, and styled text.
- **Conditional Extraction**: Handle optional fields gracefully.
- **Customizable UI**: Allow setting custom titles for the response panel.
- **Validation**: Ensure configured paths exist in the OpenAPI spec.

## Technical Plan
1. **Pydantic Models**: Add `ResponseFormattingConfig` and `FieldConfig` to `oai_shell/config/models.py`.
2. **Logic Integration**: Refactor `ShellRunner._execute_call` to handle the new `formatting` configuration.
3. **Renderer Class**: Create a dedicated `ResponseRenderer` (possibly in `oai_shell/shell/runner.py` or a new file) to keep the code clean.
4. **Table & Markdown Support**: Implement logic to detect and render lists as tables and strings as markdown when requested.

# Progress
- [ ] Update Pydantic models in `oai_shell/config/models.py`
- [ ] Implement `ResponseRenderer` logic
- [ ] Integrate renderer into `ShellRunner`
- [ ] Update startup validation for new formatting paths
- [ ] Add example configuration in a sample YAML
- [ ] Test with `dummy_server.py`
