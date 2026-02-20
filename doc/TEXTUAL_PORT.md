# Textual TUI Implementation

This document describes the Textual TUI port of OAI-Shell.

## Overview

OAI-Shell has been ported to use the [Textual](https://textual.textualize.io/) framework for its Terminal User Interface (TUI). Textual provides a modern, reactive framework for building sophisticated terminal applications with Python.

## What Changed

### Architecture
- **Before**: prompt-toolkit REPL with Rich rendering
- **After**: Full Textual application with reactive widgets

### User Interface
The new Textual interface provides:

1. **State Sidebar** (left): Real-time display of session variables
2. **Output Log** (center): Scrollable command history and API responses
3. **Command Input** (bottom): Text input with autocomplete
4. **Header** (top): Application title, connection status, and clock

### Features Preserved
All existing functionality has been maintained:
- Dynamic API endpoint discovery from OpenAPI specs
- Tab-completion for commands, operation IDs, and parameters
- State persistence and automatic variable injection
- YAML-based configuration (examples/*.yaml)
- Markdown and syntax-highlighted response rendering
- All slash commands (/help, /operations, /state, /call, custom commands)
- Response formatting with custom blocks (tables, markdown, JSON)
- After-call hooks for state extraction

## Usage

### Running the Application

The Textual interface is now the **default**:

```bash
python3 oai_shell/main.py --base-url http://localhost:8001 --config examples/dummy_server.yaml
```

To use the legacy prompt-toolkit interface:

```bash
python3 oai_shell/main.py --base-url http://localhost:8001 --config examples/dummy_server.yaml --legacy
```

### Available Commands

All commands from the original implementation are supported:

- `/help` - Show available commands
- `/operations` - List all API operations
- `/state` - Show current state variables
- `/call <operation_id>` - Call an API operation
- `/exit` - Exit the application
- Custom commands from YAML config

### Keyboard Shortcuts

- `Ctrl+C` or `Ctrl+D` - Quit the application
- `Tab` - Autocomplete commands and operation IDs
- `Enter` - Submit command
- Arrow keys - Navigate command history (in input field)
- Scroll wheel - Scroll through output history

## Implementation Details

### Key Files

- `oai_shell/shell/textual_app.py` - Main Textual application
  - `OAIShellApp` - Main application class
  - `StatePanel` - Widget for displaying state variables
  - `OAIShellSuggester` - Autocomplete logic

### CSS Styling

The application uses Textual CSS (TCSS) for styling:
- Grid layout with responsive columns
- Rounded borders with primary/accent colors
- Surface and panel backgrounds from Textual themes
- Focused input highlighting

### Widget Hierarchy

```
Screen
├── Header (app title, clock)
├── StatePanel (session variables)
├── RichLog (command output)
└── Container
    └── Input (command entry)
```

## Testing

A comprehensive test suite is provided in `tests/test_textual.py`:

```bash
python3 tests/test_textual.py
```

This test:
1. Starts the Textual app in test mode
2. Executes various commands
3. Captures screenshots of each state
4. Verifies all features work correctly

## Dependencies

The Textual port adds one new dependency:
- `textual>=0.89.1`

All other dependencies remain the same:
- `httpx>=0.28.1` - HTTP client
- `pydantic>=2.12.5` - Configuration validation
- `pyyaml>=6.0.3` - YAML parsing
- `rich>=14.3.2` - Terminal formatting (used by Textual)

The legacy interface still requires:
- `prompt-toolkit>=3.0.52`

## Migration Guide

For users of the legacy interface:

1. **No config changes needed** - All YAML configurations work unchanged
2. **Same commands** - All slash commands work identically
3. **State persistence** - Session state files are compatible
4. **Improved UI** - Better visual organization and scrollable history

### Differences from Legacy Interface

1. **Layout**: Split-pane design vs. linear REPL
2. **State visibility**: Always visible in sidebar vs. only on /state command
3. **History**: All output scrollable vs. cleared on each command
4. **Navigation**: Mouse scroll support in addition to keyboard

## Future Enhancements

Potential improvements for the Textual interface:

- [ ] Interactive operations explorer (/operations-tui) ported to Textual
- [ ] Keyboard shortcuts for common operations
- [ ] Configurable themes and colors
- [ ] Split-pane response viewer with request/response tabs
- [ ] Command history navigation with arrow keys
- [ ] Copy/paste support with mouse selection
- [ ] Export command history to file

## Known Limitations

1. **Terminal size**: Requires minimum terminal size (80x24 recommended)
2. **Colors**: Appearance depends on terminal color scheme support
3. **Mouse**: Some terminals may not support mouse interactions

## Troubleshooting

### Terminal Not Rendering Correctly

Ensure your terminal supports:
- ANSI colors
- Unicode characters
- Minimum size of 80x24

### Textual Import Errors

Install the required dependency:
```bash
pip install textual>=0.89.1
```

### Legacy Interface Preferred

Use the `--legacy` flag to continue using the prompt-toolkit interface:
```bash
python3 oai_shell/main.py --legacy --base-url <url> --config <config>
```

## Contributing

When contributing to the Textual interface:

1. Test changes with `tests/test_textual.py`
2. Ensure compatibility with existing YAML configs
3. Follow Textual best practices for widget composition
4. Maintain feature parity with legacy interface
5. Update this README with any new features

## Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Textual CSS Guide](https://textual.textualize.io/guide/CSS/)
- [Rich Library](https://rich.readthedocs.io/)
- [OAI-Shell Repository](https://github.com/kantundpeterpan/oaishell)
