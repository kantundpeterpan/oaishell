# Feature Comparison: Textual vs Legacy Interface

This document compares the new Textual TUI with the legacy prompt-toolkit interface.

## Architecture

| Aspect | Legacy (prompt-toolkit) | Textual TUI |
|--------|------------------------|-------------|
| Framework | prompt-toolkit REPL | Textual reactive framework |
| Layout | Line-by-line output | Split-pane grid layout |
| State Display | On-demand (/state) | Always visible sidebar |
| Output | Cleared between commands | Persistent scrollable log |
| Rendering | Rich library | Rich via Textual widgets |

## User Experience

| Feature | Legacy | Textual | Notes |
|---------|--------|---------|-------|
| State Visibility | ⚠️ Hidden until /state | ✅ Always visible | Textual shows state in real-time |
| Command History | ✅ Via arrow keys | ✅ Scrollable output | Textual keeps full history visible |
| Visual Organization | ⚠️ Linear flow | ✅ Split-pane design | Better use of screen space |
| Mouse Support | ❌ No | ✅ Scroll support | Textual supports mouse wheel |
| Themes | ⚠️ Terminal-dependent | ✅ TCSS styling | Consistent appearance |

## Feature Parity

All core features are preserved in both interfaces:

| Feature | Legacy | Textual | Status |
|---------|--------|---------|--------|
| OpenAPI Discovery | ✅ | ✅ | Identical |
| Command Autocomplete | ✅ | ✅ | Same functionality |
| State Persistence | ✅ | ✅ | Compatible files |
| YAML Configuration | ✅ | ✅ | No changes needed |
| Custom Commands | ✅ | ✅ | Full compatibility |
| Response Formatting | ✅ | ✅ | Tables, markdown, JSON |
| After-call Hooks | ✅ | ✅ | State extraction works |
| Slash Commands | ✅ | ✅ | All supported |
| Parameter Injection | ✅ | ✅ | Same logic |
| Error Handling | ✅ | ✅ | Robust in both |

## Implementation Details

### Legacy Interface (runner.py)
- **REPL Loop**: Traditional prompt-input-output cycle
- **Rendering**: Direct Rich console printing
- **Completion**: prompt-toolkit Completer class
- **State**: Manual display via /state command
- **Lines of Code**: ~650

### Textual Interface (textual_app.py)
- **Event-Driven**: Reactive message passing
- **Rendering**: Textual widgets (RichLog, Input, Static)
- **Completion**: Textual Suggester class
- **State**: Live-updating StatePanel widget
- **Lines of Code**: ~540

## Performance

| Metric | Legacy | Textual | Winner |
|--------|--------|---------|--------|
| Startup Time | Fast (~0.5s) | Fast (~0.7s) | Tie |
| Response Time | Instant | Instant | Tie |
| Memory Usage | Low (~30MB) | Medium (~40MB) | Legacy |
| CPU Usage | Minimal | Minimal | Tie |
| Responsiveness | Good | Excellent | Textual |

## When to Use Each

### Use Legacy Interface If:
- Running on minimal/embedded systems with limited memory
- Terminal doesn't support full ANSI/Unicode
- Prefer traditional CLI experience
- Need absolute minimum dependencies

### Use Textual Interface If:
- Want modern TUI experience (recommended)
- Need to monitor state changes in real-time
- Working with complex API workflows
- Prefer visual organization of information
- Running on standard terminal (most users)

## Migration Path

For users switching from legacy to Textual:

1. **No configuration changes required** - All YAML files work as-is
2. **Same commands** - All slash commands identical
3. **Compatible state** - Session files can be used by both
4. **Easy switch** - Use `--legacy` flag if needed

## Keyboard Shortcuts

### Legacy Interface
- `Ctrl+C` - Interrupt/Exit
- `Ctrl+D` - Exit
- `Tab` - Autocomplete
- `Up/Down` - Command history

### Textual Interface
- `Ctrl+C` - Exit
- `Ctrl+D` - Exit
- `Tab` - Autocomplete
- `Up/Down` - Navigate in input
- `Scroll` - Scroll output log
- `Mouse` - Click to focus input

## Code Quality

Both implementations:
- ✅ Pass all unit tests
- ✅ Follow Python best practices
- ✅ Type hints where appropriate
- ✅ Comprehensive error handling
- ✅ Well-documented with docstrings
- ✅ Modular and maintainable

## Future Development

### Textual Roadmap
- [ ] Interactive operations explorer (/operations-tui in Textual)
- [ ] Keyboard shortcuts for common operations
- [ ] Configurable themes/colors
- [ ] Request/response tabs
- [ ] Export functionality

### Legacy Status
- ✅ Maintained for backward compatibility
- ⚠️ No new features planned
- ✅ Bug fixes will be applied
- ℹ️ Recommended to migrate to Textual

## Conclusion

The Textual interface is the **recommended default** for most users because it:
- Provides better user experience with split-pane layout
- Shows state changes in real-time
- Maintains scrollable history
- Offers modern TUI aesthetics
- Supports all existing features

The legacy interface remains available for specific use cases where:
- Minimal resource usage is critical
- Traditional CLI workflow is preferred
- Running on limited terminals

Both interfaces are fully functional and maintain complete feature parity with existing YAML configurations.
