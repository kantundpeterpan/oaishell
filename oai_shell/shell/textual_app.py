"""Textual TUI application for OAI-Shell."""

import json
import shlex
from typing import Dict, Any, List, Optional, Tuple
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Input,
    RichLog,
    Static,
    DataTable,
    Tree,
    Label,
    Button,
)
from textual.widgets.tree import TreeNode
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    VerticalScroll,
    ScrollableContainer,
)
from textual.binding import Binding
from textual.suggester import Suggester
from textual.screen import ModalScreen
from textual_autocomplete import AutoComplete, DropdownItem
from rich.console import Group
from rich.panel import Panel
from rich.table import Table as RichTable
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree as RichTree

from ..engine.client import OpenAIEngine, ClientState, EngineError
from ..engine.utils import PayloadAssembler, SchemaPathResolver
from ..config.models import ShellConfig


class OAIShellSuggester(Suggester):
    """Custom suggester for OAI-Shell commands and operations."""

    def __init__(self, engine: OpenAIEngine, config: ShellConfig):
        self.engine = engine
        self.config = config
        super().__init__(use_cache=False, case_sensitive=False)

    async def get_suggestion(self, value: str) -> Optional[str]:
        """Get command suggestions based on current input."""
        if not value:
            return None

        words = value.split()

        # Suggest commands that start with /
        if value.startswith("/") and (len(words) <= 1 or " " not in value):
            internals = ["/help", "/exit", "/state", "/operations", "/call", "/theme"]
            custom = list(self.config.commands.keys())
            all_cmds = internals + custom

            for cmd in all_cmds:
                if cmd.startswith(value) and cmd != value:
                    return cmd

        # Suggest operation IDs after /call
        elif value.startswith("/call ") and len(words) == 2 and not value.endswith(" "):
            prefix = words[1]
            for op_id in self.engine.operations.keys():
                if op_id.lower().startswith(prefix.lower()) and op_id != prefix:
                    return f"/call {op_id}"

        return None


class StatePanel(Static):
    """Widget to display current state variables."""

    def __init__(self, state: ClientState, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = state

    def on_mount(self) -> None:
        """Update the state display when mounted."""
        self.update_display()

    def update_display(self) -> None:
        """Update the state panel with current values."""
        table = RichTable(
            title="[bold cyan]State[/bold cyan]", box=None, padding=(0, 1)
        )
        table.add_column("Key", style="yellow")
        table.add_column("Value", style="green")

        state_dict = self.state.to_dict()
        if not state_dict:
            self.update("[dim]No state variables set[/dim]")
        else:
            for k, v in state_dict.items():
                table.add_row(k, str(v)[:30])  # Truncate long values
            self.update(table)


class OperationsScreen(ModalScreen):
    """Modal screen for interactive operations explorer."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    CSS = """
    OperationsScreen {
        align: center middle;
    }
    
    #operations_container {
        width: 95%;
        height: 90%;
        background: $surface;
        border: thick $primary;
    }
    
    #tree_container {
        width: 1fr;
        height: 100%;
    }
    
    #operations_tree {
        height: 100%;
        border: round $primary;
        background: $surface;
    }
    
    #request_panel {
        width: 1fr;
        height: 100%;
        border: round $accent;
        background: $surface;
    }
    
    #response_panel {
        width: 1fr;
        height: 100%;
        border: round $accent;
        background: $surface;
    }
    """

    def __init__(self, engine: OpenAIEngine, config: ShellConfig, state: ClientState):
        super().__init__()
        self.engine = engine
        self.config = config
        self.state = state
        self.selected_operation = None

    def compose(self) -> ComposeResult:
        """Compose the operations explorer UI."""
        with Container(id="operations_container"):
            with Horizontal():
                yield ScrollableContainer(
                    Tree("API Operations", id="operations_tree"), id="tree_container"
                )
                yield ScrollableContainer(
                    Static(
                        "Select an operation to view request schema",
                        id="request_content",
                    ),
                    id="request_panel",
                )
                yield ScrollableContainer(
                    Static(
                        "Select an operation to view response schema",
                        id="response_content",
                    ),
                    id="response_panel",
                )

    def on_mount(self) -> None:
        """Build the operations tree when mounted."""
        tree = self.query_one("#operations_tree", Tree)
        tree.show_root = False

        depth = self.config.tui.aggregation_depth
        tag_groups: Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]] = {}

        # Group operations by tag and path
        for op_id, op in self.engine.operations.items():
            tags = op["raw"].get("tags", ["default"])
            for tag in tags:
                if tag not in tag_groups:
                    tag_groups[tag] = {}
                path = op.get("display_path", op["path"])
                parts = path.strip("/").split("/")
                if depth > 0 and len(parts) > depth:
                    group_path = "/" + "/".join(parts[:depth]) + "/..."
                else:
                    group_path = path
                if group_path not in tag_groups[tag]:
                    tag_groups[tag][group_path] = []
                tag_groups[tag][group_path].append((op_id, op))

        # Build tree structure
        for tag in sorted(tag_groups.keys()):
            display_tag = tag
            if self.engine.common_prefix:
                display_tag = f"{tag} ({self.engine.common_prefix})"
            tag_node = tree.root.add(display_tag, expand=True)
            tag_node.data = {"type": "tag", "name": tag}

            paths = tag_groups[tag]
            for path in sorted(paths.keys()):
                path_node = tag_node.add(path, expand=False)
                path_node.data = {"type": "path", "name": path}

                for op_id, op in sorted(paths[path], key=lambda x: x[0]):
                    method = op["method"]
                    method_style = {
                        "GET": "green",
                        "POST": "yellow",
                        "PUT": "blue",
                        "DELETE": "red",
                    }.get(method, "white")
                    # Use add_leaf for operation nodes so they are terminal (not expandable)
                    try:
                        # Terminal operation node so it can't be expanded in the tree.
                        # This addresses issue #9: endpoints should be terminal nodes.
                        op_node = path_node.add_leaf(
                            f"[{method_style}]{method}[/{method_style}] {op_id}"
                        )
                    except Exception:
                        # Fallback for older textual versions where add_leaf may not exist
                        op_node = path_node.add(
                            f"[{method_style}]{method}[/{method_style}] {op_id}"
                        )
                    op_node.data = {"type": "op", "op_id": op_id, "op": op}

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection (mouse click).

        Updates the request/response panels when an operation is selected.
        """
        node = event.node
        if not node.data or node.data.get("type") != "op":
            return

        op_id = node.data["op_id"]
        op = node.data["op"]
        self.selected_operation = op_id

        # Update request panel
        self._update_request_panel(op)

        # Update response panel
        self._update_response_panel(op)

    def on_tree_node_highlighted(self, event) -> None:
        """Handle tree node highlight (keyboard navigation).

        Updates the request/response panels when navigating with arrow keys.
        """
        node = event.node
        if not node.data or node.data.get("type") != "op":
            return

        op = node.data["op"]

        # Update request panel
        self._update_request_panel(op)

        # Update response panel
        self._update_response_panel(op)

    def on_key(self, event) -> None:
        """Handle key events.

        When Enter is pressed with an operation highlighted, close the screen.
        This addresses issue #10.
        """
        if event.key == "enter":
            tree = self.query_one("#operations_tree", Tree)
            cursor_node = tree.cursor_node
            if (
                cursor_node
                and cursor_node.data
                and cursor_node.data.get("type") == "op"
            ):
                op_id = cursor_node.data["op_id"]
                # Build command with required parameters (same logic as action_dismiss)
                cmd = f"/call {op_id}"
                op = self.engine.operations.get(op_id)
                if op:
                    all_params = self.engine.get_params_for_operation(op_id)
                    required_missing = [
                        p["name"]
                        for p in all_params
                        if p.get("required") and self.state.get(p["name"]) is None
                    ]
                    for p_name in required_missing:
                        cmd += f" --{p_name} "
                self.dismiss(cmd + " ")
                # Stop event propagation to prevent input submission
                event.stop()

    def _build_schema_tree(
        self, schema: Dict[str, Any], name: str = "root"
    ) -> RichTree:
        """Build a Rich tree from a schema."""
        schema = self.engine.resolve_schema(schema)
        s_type = schema.get("type", "object")
        description = schema.get("description", "")

        type_col = {
            "object": "blue",
            "array": "yellow",
            "string": "green",
            "integer": "cyan",
            "number": "cyan",
            "boolean": "magenta",
        }.get(s_type, "white")

        icon = self.config.tui.type_icons.get(
            s_type, self.config.tui.type_icons.get("default", "")
        )
        label = f"{icon} [bold cyan]{name}[/bold cyan] [dim][{type_col}]({s_type})[/{type_col}][/dim]"
        if description:
            label += f" - [italic]{description}[/italic]"

        res_tree = RichTree(label)

        if s_type == "object":
            props = schema.get("properties", {})
            required = schema.get("required", [])
            for p_name, p_schema in props.items():
                p_label = p_name
                if p_name in required:
                    p_label = f"[bold white]{p_name}*[/bold white]"
                sub_tree = self._build_schema_tree(p_schema, p_label)
                res_tree.add(sub_tree)
        elif s_type == "array":
            items = schema.get("items", {})
            sub_tree = self._build_schema_tree(items, "items[]")
            res_tree.add(sub_tree)

        return res_tree

    def _update_request_panel(self, op: Dict[str, Any]) -> None:
        """Update the request schema panel."""
        req_content = []

        # Parameters
        params = []
        for p in op.get("parameters", []):
            params.append(
                {
                    "name": p["name"],
                    "in": p.get("in", "query"),
                    "type": p.get("schema", {}).get("type", "string"),
                    "required": p.get("required", False),
                    "description": p.get("description", ""),
                }
            )

        if params:
            table = RichTable(title="Parameters", box=None, padding=(0, 1))
            table.add_column("Name", style="cyan")
            table.add_column("In", style="yellow")
            table.add_column("Type", style="magenta")
            table.add_column("Description")
            for p in params:
                name = f"[bold]{p['name']}*[/bold]" if p["required"] else p["name"]
                table.add_row(
                    name,
                    p["in"],
                    p["type"],
                    p["description"][:40] if p["description"] else "",
                )
            req_content.append(table)

        # Request Body
        body = op.get("requestBody")
        if body:
            content = body.get("content", {})
            json_schema = content.get("application/json", {}).get("schema")
            if json_schema:
                req_content.append(
                    self._build_schema_tree(json_schema, name="RequestBody (JSON)")
                )

        if not req_content:
            req_content.append("[dim]No request parameters or body[/dim]")

        request_static = self.query_one("#request_content", Static)
        request_static.update(Panel(Group(*req_content), title="Request Schema"))

    def _update_response_panel(self, op: Dict[str, Any]) -> None:
        """Update the response schema panel."""
        res_200 = op.get("responses", {}).get("200", {})
        res_content_spec = res_200.get("content", {})
        res_json_schema = res_content_spec.get("application/json", {}).get("schema")

        if res_json_schema:
            res_view = self._build_schema_tree(
                res_json_schema, name="Response (200 OK)"
            )
            response_static = self.query_one("#response_content", Static)
            response_static.update(Panel(res_view, title="Response Schema"))
        else:
            response_static = self.query_one("#response_content", Static)
            response_static.update(
                Panel(
                    "[dim]No response schema (application/json) found for 200 OK[/dim]",
                    title="Response Schema",
                )
            )

    def action_dismiss(self) -> None:
        """Dismiss the modal and return selected operation."""
        if self.selected_operation:
            # Build command with required parameters
            cmd = f"/call {self.selected_operation}"
            op = self.engine.operations.get(self.selected_operation)
            if op:
                all_params = self.engine.get_params_for_operation(
                    self.selected_operation
                )
                required_missing = [
                    p["name"]
                    for p in all_params
                    if p.get("required") and self.state.get(p["name"]) is None
                ]
                for p_name in required_missing:
                    cmd += f" --{p_name} "
            self.dismiss(cmd + " ")
        else:
            self.dismiss(None)


class OAIShellAutoComplete(AutoComplete):
    """Custom AutoComplete that only completes the word under the cursor."""

    def get_search_string(self, target_state) -> str:
        """The search string is just the word currently being typed."""
        before_cursor = target_state.text[: target_state.cursor_position]
        if not before_cursor or before_cursor.endswith(" "):
            return ""

        last_word = before_cursor.split()[-1]
        return last_word

    def apply_completion(self, value: str, state) -> None:
        """Insert ONLY the completion part, replacing the current word."""
        target = self.target
        before_cursor = state.text[: state.cursor_position]

        # Find the start of the word being replaced
        if not before_cursor or before_cursor.endswith(" "):
            # We are inserting at cursor (e.g. after a space)
            target.insert_text_at_cursor(value)
        else:
            # We are replacing the current word
            last_space_idx = before_cursor.rfind(" ")
            word_start = last_space_idx + 1 if last_space_idx != -1 else 0

            # Update target value by replacing the word segment
            new_text = (
                state.text[:word_start] + value + state.text[state.cursor_position :]
            )
            target.value = new_text
            target.cursor_position = word_start + len(value)


class OAIShellApp(App):
    """Textual TUI application for OAI-Shell."""

    CSS = """
    .main-screen {
        layout: grid;
        grid-size: 12 12;
        grid-rows: auto 1fr auto;
    }
    
    Header {
        column-span: 12;
    }
    
    #state_panel {
        column-span: 3;
        row-span: 10;
        height: 100%;
        border:  $primary;
        padding: 1;
        background: $surface;
    }
    
    #output_log {
        column-span: 9;
        row-span: 10;
        height: 100%;
        border: round $primary;
        background: $surface;
        scrollbar-gutter: stable;
    }
    
    #input_container {
        column-span: 12;
        height: auto;
        padding: 1;
        border: round $accent;
        background: $panel;
    }
    
    Input {
        width: 100%;
    }
    
    Input:focus {
        border: tall $accent;
    }

    AutoComplete > AutoCompleteList {
        width: auto;
        min-width: 30;
        max-width: 80;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit"),
    ]

    def __init__(self, config: ShellConfig, engine: OpenAIEngine):
        super().__init__()
        self.config = config
        self.engine = engine
        self.state = ClientState(persistence_file=config.state.storage)
        # Load defaults into state
        self.state.update(**config.state.defaults)
        self.assembler = PayloadAssembler(self.engine, self.state)
        self.title = config.name
        self.sub_title = f"Connected to {engine.base_url}"
        self._current_theme_name = "dark"  # Default theme name

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield StatePanel(self.state, id="state_panel")
        yield RichLog(id="output_log", highlight=True, markup=True, wrap=True)

        # Create input with autocomplete
        input_widget = Input(
            placeholder="Enter command (e.g., /help, /operations, /call ...)",
            id="command_input",
        )

        yield Container(input_widget, id="input_container")

        # Add autocomplete overlay
        yield OAIShellAutoComplete(
            target="#command_input", candidates=self._get_autocomplete_items
        )

    def _get_autocomplete_items(self, input_state) -> List[DropdownItem]:
        """Generate autocomplete items based on current input."""
        value = input_state.text
        cursor_pos = input_state.cursor_position

        if not value:
            return []

        # Context before and after cursor
        before_cursor = value[:cursor_pos]
        after_cursor = value[cursor_pos:]
        words_before = before_cursor.split()

        # Determine the word currently being typed
        if not before_cursor or before_cursor.endswith(" "):
            last_word = ""
        else:
            last_word = words_before[-1]

        items = []

        # 1. Command suggestions (at the very beginning)
        if len(words_before) == 0 or (
            len(words_before) == 1 and not before_cursor.endswith(" ")
        ):
            internals = ["/help", "/exit", "/state", "/operations", "/call", "/theme"]
            custom = list(self.config.commands.keys())
            all_cmds = internals + custom

            for cmd in all_cmds:
                if cmd.startswith(last_word):
                    # We only suggest the command itself, not the full line
                    items.append(DropdownItem(main=cmd))

        # 2. Operation IDs after /call
        elif words_before and words_before[0] == "/call":
            if (len(words_before) == 1 and before_cursor.endswith(" ")) or (
                len(words_before) == 2 and not before_cursor.endswith(" ")
            ):
                # Typing the operation ID
                for op_id in sorted(self.engine.operations.keys()):
                    if op_id.lower().startswith(last_word.lower()):
                        items.append(DropdownItem(main=op_id))

            # 3. Parameter suggestions after /call <op_id>
            elif len(words_before) >= 2:
                op_id = words_before[1]
                if op_id in self.engine.operations:
                    all_params = self.engine.get_params_for_operation(op_id)

                    # Filter out parameters already present in the full command
                    all_words = value.replace("=", " ").split()
                    used_params = {
                        w.lstrip("-") for w in all_words if w.startswith("--")
                    }

                    # If typing a parameter, don't filter it out
                    current_param_typing = (
                        last_word.replace("=", " ").split()[0].lstrip("-")
                        if last_word.startswith("--")
                        else None
                    )

                    for p in all_params:
                        param_name = p["name"]
                        full_param = f"--{param_name}"

                        if (
                            param_name in used_params
                            and param_name != current_param_typing
                        ):
                            continue

                        if full_param.startswith(last_word):
                            type_hint = p.get("type", "any")
                            prefix_text = f"({p['in']}) {type_hint}"
                            items.append(
                                DropdownItem(main=full_param, prefix=prefix_text)
                            )

        # 4. Theme suggestions
        elif words_before and words_before[0] == "/theme":
            themes = ["dark", "light", "dark-high-contrast"]
            if (len(words_before) == 1 and before_cursor.endswith(" ")) or (
                len(words_before) == 2 and not before_cursor.endswith(" ")
            ):
                for theme in themes:
                    if theme.startswith(last_word.lower()):
                        items.append(DropdownItem(main=theme))

        return items[:15]

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Add a class to the screen to apply the layout, since id cannot be changed after initialization
        self.screen.add_class("main-screen")
        output_log = self.query_one("#output_log", RichLog)
        output_log.write(
            Panel(
                f"[bold green]Welcome to {self.config.name}[/bold green]\n"
                f"Connected to {self.engine.base_url}\n\n"
                f"Type [cyan]/help[/cyan] for available commands",
                title="OAI-Shell",
                border_style="green",
            )
        )

        # Validate configured commands at startup
        for cmd_name, cmd_conf in self.config.commands.items():
            op = self.engine.operations.get(cmd_conf.operationId)
            if not op:
                output_log.write(
                    f"[dim yellow]Info: Command '{cmd_name}' targets unknown operation '{cmd_conf.operationId}'. "
                    "Validation skipped.[/dim yellow]"
                )
                continue

            # Validate default_response_field
            if cmd_conf.default_response_field and not cmd_conf.force_response_field:
                resp_200 = op.get("responses", {}).get("200", {})
                content = resp_200.get("content", {})
                json_schema = content.get("application/json", {}).get("schema")
                if json_schema:
                    if not SchemaPathResolver.validate_path(
                        json_schema, cmd_conf.default_response_field, self.engine
                    ):
                        output_log.write(
                            f"[yellow]Warning:[/yellow] Command '{cmd_name}' has default_response_field "
                            f"'{cmd_conf.default_response_field}' which may not exist in the schema."
                        )

        # Focus on input
        self.query_one("#command_input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command = event.value.strip()
        if not command:
            return

        output_log = self.query_one("#output_log", RichLog)
        output_log.write(f"[bold blue]> {command}[/bold blue]")

        # Clear input
        event.input.value = ""

        # Handle commands
        if command == "/exit":
            self.exit()
        elif command.startswith("/"):
            await self.handle_command(command)
        else:
            output_log.write("[dim]Use /command or /call. Type /help for list.[/dim]")

    async def handle_command(self, line: str):
        """Handle slash commands."""
        output_log = self.query_one("#output_log", RichLog)

        try:
            parts = shlex.split(line)
            cmd = parts[0]
            args = parts[1:]

            if cmd == "/help":
                self.show_help()
            elif cmd == "/operations":
                await self.show_operations_interactive()
            elif cmd == "/state":
                self.show_state()
            elif cmd == "/theme":
                self.handle_theme(args)
            elif cmd == "/call":
                await self.handle_call(args)
            elif cmd in self.config.commands:
                await self.handle_custom_command(cmd, args)
            else:
                output_log.write(f"[yellow]Unknown command: {cmd}[/yellow]")
        except Exception as e:
            output_log.write(f"[red]Error:[/red] {e}")

    def show_help(self):
        """Display help information."""
        output_log = self.query_one("#output_log", RichLog)

        table = RichTable(title="Internal Commands", box=None, padding=(0, 1))
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        table.add_row("/help", "Show this help")
        table.add_row("/operations", "Interactive API operations explorer")
        table.add_row("/state", "Show current state")
        table.add_row(
            "/theme <name>", "Change color theme (dark, light, dark-high-contrast)"
        )
        table.add_row("/call <op_id>", "Call a raw API operation")
        table.add_row("/exit", "Exit the shell")

        output_log.write(table)

        if self.config.commands:
            table2 = RichTable(title="Custom Commands", box=None, padding=(0, 1))
            table2.add_column("Command", style="cyan")
            table2.add_column("Description")
            for cmd, conf in self.config.commands.items():
                table2.add_row(cmd, conf.description or "")
            output_log.write(table2)

    async def show_operations_interactive(self):
        """Show interactive operations explorer modal."""

        def handle_result(result):
            if result:
                # Set the returned command in the input
                input_widget = self.query_one("#command_input", Input)
                input_widget.value = result
                # Position cursor at the end for easy parameter entry
                input_widget.cursor_position = len(result)
                input_widget.focus()

        await self.push_screen(
            OperationsScreen(self.engine, self.config, self.state), handle_result
        )

    def handle_theme(self, args: List[str]):
        """Handle theme changing."""
        output_log = self.query_one("#output_log", RichLog)

        if not args:
            output_log.write(
                f"[yellow]Current theme:[/yellow] {self._current_theme_name}"
            )
            output_log.write(
                "[cyan]Available themes:[/cyan] dark, light, dark-high-contrast"
            )
            return

        theme_name = args[0].lower()
        valid_themes = {
            "dark": "textual-dark",
            "light": "textual-light",
            "dark-high-contrast": "textual-dark-high-contrast",
        }

        if theme_name not in valid_themes:
            output_log.write(f"[red]Invalid theme:[/red] {theme_name}")
            output_log.write(
                "[cyan]Available themes:[/cyan] dark, light, dark-high-contrast"
            )
            return

        self.theme = valid_themes[theme_name]
        self._current_theme_name = theme_name
        output_log.write(f"[green]Theme changed to:[/green] {theme_name}")

    def show_state(self):
        """Display current state."""
        state_panel = self.query_one("#state_panel", StatePanel)
        state_panel.update_display()

        output_log = self.query_one("#output_log", RichLog)
        output_log.write("[green]State panel updated[/green]")

    def _parse_cli_args(
        self, args: List[str]
    ) -> Tuple[Dict[str, Any], List[str], bool, bool]:
        """Parse CLI arguments into parameters."""
        params = {}
        pos_args = []
        stream = False
        debug = False
        i = 0
        while i < len(args):
            if args[i] == "--stream":
                stream = True
                i += 1
            elif args[i] == "--debug":
                debug = True
                i += 1
            elif args[i].startswith("--"):
                key = args[i][2:]
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    params[key] = args[i + 1]
                    i += 2
                else:
                    params[key] = True
                    i += 1
            else:
                pos_args.append(args[i])
                i += 1
        return params, pos_args, stream, debug

    async def handle_call(self, args: List[str]):
        """Handle /call command."""
        output_log = self.query_one("#output_log", RichLog)

        if not args:
            output_log.write(
                "[red]Usage: /call <operation_id> [--param value] [--stream] [--debug][/red]"
            )
            return

        op_id = args[0]
        cli_params, _, stream, debug = self._parse_cli_args(args[1:])
        await self._execute_call(op_id, cli_params, stream=stream, debug=debug)

    async def handle_custom_command(self, cmd: str, args: List[str]):
        """Handle custom commands from config."""
        conf = self.config.commands[cmd]
        op_id = conf.operationId

        cli_flags, pos_args, stream, debug = self._parse_cli_args(args)

        # Build params from mapping using positional args
        cli_params = {}
        for key, template in conf.mapping.items():
            cli_params[key] = self.assembler.resolve_value(template, pos_args)

        # Merge CLI flags (they take precedence)
        cli_params.update(cli_flags)

        await self._execute_call(
            op_id, cli_params, stream=stream, debug=debug, cmd_conf=conf
        )

    async def _execute_call(
        self,
        op_id: str,
        cli_params: Dict[str, Any],
        stream: bool = False,
        debug: bool = False,
        cmd_conf=None,
    ):
        """Execute an API call."""
        output_log = self.query_one("#output_log", RichLog)

        try:
            payload, autofilled = self.assembler.assemble(op_id, cli_params)

            # Notify autofilled params
            for key in autofilled:
                output_log.write(
                    f"[dim italic]Autofilled from state: {key}[/dim italic]"
                )

            # Validate default_response_field
            if (
                cmd_conf
                and cmd_conf.default_response_field
                and not cmd_conf.force_response_field
            ):
                op = self.engine.operations.get(op_id)
                if op:
                    resp_200 = op.get("responses", {}).get("200", {})
                    content = resp_200.get("content", {})
                    json_schema = content.get("application/json", {}).get("schema")
                    if json_schema:
                        if not SchemaPathResolver.validate_path(
                            json_schema, cmd_conf.default_response_field, self.engine
                        ):
                            output_log.write(
                                f"[red]Error:[/red] default_response_field '{cmd_conf.default_response_field}' "
                                f"does not conform to the schema for operation {op_id}. "
                                "Use force_response_field: true to override."
                            )
                            return

            if stream:
                with self.engine.call(op_id, stream=True, **payload) as resp:
                    output_log.write("[bold blue]Streaming Response:[/bold blue]")
                    for line in resp.iter_lines():
                        if line:
                            output_log.write(line)
            else:
                resp = self.engine.call(op_id, **payload)
                data = resp.json()

                # Render response
                if cmd_conf and cmd_conf.formatting:
                    self._render_formatted_response(data, cmd_conf.formatting, debug)
                else:
                    # Default rendering
                    display_data = data
                    title = "[bold blue]Response[/bold blue]"

                    if cmd_conf and cmd_conf.default_response_field:
                        resolved = SchemaPathResolver.resolve_data(
                            data, cmd_conf.default_response_field
                        )
                        if resolved is not None:
                            display_data = resolved
                            title = f"[bold blue]Response: {cmd_conf.default_response_field}[/bold blue]"
                        else:
                            output_log.write(
                                f"[yellow]Warning: Field '{cmd_conf.default_response_field}' "
                                "not found in the response payload.[/yellow]"
                            )

                    output_log.write(
                        Panel(
                            Syntax(
                                json.dumps(display_data, indent=2),
                                "json",
                                background_color="default",
                            ),
                            title=title,
                            border_style="green",
                        )
                    )

                    if debug:
                        output_log.write(
                            Panel(
                                Syntax(
                                    json.dumps(data, indent=2),
                                    "json",
                                    background_color="default",
                                ),
                                title="[bold yellow]Raw Response (Debug)[/bold yellow]",
                                border_style="dim",
                            )
                        )

                # After call hooks
                if cmd_conf and cmd_conf.after_call:
                    save = cmd_conf.after_call.get("save_to_state", {})
                    for state_key, path in save.items():
                        if path.startswith("json:"):
                            key_path = path[5:]
                            val = SchemaPathResolver.resolve_data(data, key_path)
                            if val is not None:
                                self.state.update(**{state_key: val})
                                output_log.write(
                                    f"[dim]State updated: {state_key}[/dim]"
                                )
                                # Update state panel
                                state_panel = self.query_one("#state_panel", StatePanel)
                                state_panel.update_display()

        except EngineError as e:
            output_log.write(f"[red]API Error:[/red] {e}")
        except Exception as e:
            output_log.write(f"[red]Error:[/red] {e}")

    def _render_formatted_response(self, data: Any, formatting, debug: bool = False):
        """Render response with custom formatting."""
        output_log = self.query_one("#output_log", RichLog)

        title = formatting.title or "[bold blue]Response[/bold blue]"
        blocks_content = []

        for block in formatting.blocks:
            block_data = SchemaPathResolver.resolve_data(data, block.path)
            if block_data is None:
                if block.optional:
                    continue
                block_data = {}

            if block.title:
                blocks_content.append(f"[bold underline]{block.title}[/bold underline]")

            if block.layout == "table":
                blocks_content.append(self._get_table(block_data, block.fields))
            elif block.layout == "markdown":
                blocks_content.append(Markdown(str(block_data)))
            elif block.layout == "json":
                blocks_content.append(
                    Syntax(
                        json.dumps(block_data, indent=2),
                        "json",
                        background_color="default",
                    )
                )
            else:
                blocks_content.extend(self._get_list_items(block_data, block.fields))

            blocks_content.append("")

        output_log.write(Panel(Group(*blocks_content), title=title))

        if debug:
            output_log.write(
                Panel(
                    Syntax(
                        json.dumps(data, indent=2), "json", background_color="default"
                    ),
                    title="[bold yellow]Raw Response (Debug)[/bold yellow]",
                    border_style="dim",
                )
            )

    def _get_list_items(self, data: Any, fields: List[Any]) -> List[Any]:
        """Get list items for rendering."""
        items = []
        for field in fields:
            val = SchemaPathResolver.resolve_data(data, field.path)
            if val is None and field.optional:
                continue

            label = field.label or field.path
            rendered_val = self._format_value(val, field.format, field.style)

            if field.format == "text":
                items.append(f"[bold]{label}:[/bold] {rendered_val}")
            else:
                items.append(f"[bold]{label}:[/bold]")
                items.append(rendered_val)
        return items

    def _get_table(self, data: Any, fields: List[Any]) -> RichTable:
        """Create a Rich table from data."""
        rows = data if isinstance(data, list) else [data]

        table = RichTable(box=None, padding=(0, 1))
        for field in fields:
            table.add_column(field.label or field.path, style=field.style)

        for row in rows:
            row_vals = []
            for field in fields:
                val = SchemaPathResolver.resolve_data(row, field.path)
                row_vals.append(str(val) if val is not None else "")
            table.add_row(*row_vals)
        return table

    def _format_value(self, val: Any, format_type: str, style: Optional[str]) -> Any:
        """Format a value for display."""
        if val is None:
            return "[dim]null[/dim]"

        if format_type == "json":
            return Syntax(json.dumps(val, indent=2), "json", background_color="default")
        elif format_type == "markdown":
            return Markdown(str(val))
        else:
            res = str(val)
            if style:
                res = f"[{style}]{res}[/{style}]"
            return res
