"""Textual TUI application for OAI-Shell."""
import json
import shlex
from typing import Dict, Any, List, Optional, Tuple
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, DataTable
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual.suggester import Suggester
from rich.console import Group
from rich.panel import Panel
from rich.table import Table as RichTable
from rich.markdown import Markdown
from rich.syntax import Syntax

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
        if value.startswith('/') and (len(words) <= 1 or ' ' not in value):
            internals = [
                '/help', '/exit', '/state', '/operations', 
                '/operations-tui', '/call'
            ]
            custom = list(self.config.commands.keys())
            all_cmds = internals + custom
            
            for cmd in all_cmds:
                if cmd.startswith(value) and cmd != value:
                    return cmd
        
        # Suggest operation IDs after /call
        elif value.startswith('/call ') and len(words) == 2 and not value.endswith(' '):
            prefix = words[1]
            for op_id in self.engine.operations.keys():
                if op_id.lower().startswith(prefix.lower()) and op_id != prefix:
                    return f'/call {op_id}'
        
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
        table = RichTable(title="[bold cyan]State[/bold cyan]", box=None, padding=(0, 1))
        table.add_column("Key", style="yellow")
        table.add_column("Value", style="green")
        
        state_dict = self.state.to_dict()
        if not state_dict:
            self.update("[dim]No state variables set[/dim]")
        else:
            for k, v in state_dict.items():
                table.add_row(k, str(v)[:30])  # Truncate long values
            self.update(table)


class OAIShellApp(App):
    """Textual TUI application for OAI-Shell."""
    
    CSS = """
    Screen {
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
        border: round $primary;
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
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield StatePanel(self.state, id="state_panel")
        yield RichLog(id="output_log", highlight=True, markup=True, wrap=True)
        yield Container(
            Input(
                placeholder="Enter command (e.g., /help, /operations, /call ...)",
                suggester=OAIShellSuggester(self.engine, self.config),
                id="command_input"
            ),
            id="input_container"
        )
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        output_log = self.query_one("#output_log", RichLog)
        output_log.write(
            Panel(
                f"[bold green]Welcome to {self.config.name}[/bold green]\n"
                f"Connected to {self.engine.base_url}\n\n"
                f"Type [cyan]/help[/cyan] for available commands",
                title="OAI-Shell",
                border_style="green"
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
                    if not SchemaPathResolver.validate_path(json_schema, cmd_conf.default_response_field, self.engine):
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
                self.show_operations()
            elif cmd == "/state":
                self.show_state()
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
        table.add_row("/operations", "List available API operations")
        table.add_row("/state", "Show current state")
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
    
    def show_operations(self):
        """Display available API operations."""
        output_log = self.query_one("#output_log", RichLog)
        
        table = RichTable(title="Available Operations", box=None, padding=(0, 1))
        table.add_column("Operation ID", style="cyan")
        table.add_column("Method", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Summary")
        
        for op_id, op in self.engine.operations.items():
            table.add_row(
                op_id,
                op["method"],
                op.get("display_path", op["path"]),
                op.get("summary", "")
            )
        
        output_log.write(table)
    
    def show_state(self):
        """Display current state."""
        state_panel = self.query_one("#state_panel", StatePanel)
        state_panel.update_display()
        
        output_log = self.query_one("#output_log", RichLog)
        output_log.write("[green]State panel updated[/green]")
    
    def _parse_cli_args(self, args: List[str]) -> Tuple[Dict[str, Any], List[str], bool, bool]:
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
                if i + 1 < len(args) and not args[i+1].startswith("--"):
                    params[key] = args[i+1]
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
            output_log.write("[red]Usage: /call <operation_id> [--param value] [--stream] [--debug][/red]")
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
        
        await self._execute_call(op_id, cli_params, stream=stream, debug=debug, cmd_conf=conf)
    
    async def _execute_call(
        self, 
        op_id: str, 
        cli_params: Dict[str, Any], 
        stream: bool = False, 
        debug: bool = False,
        cmd_conf = None
    ):
        """Execute an API call."""
        output_log = self.query_one("#output_log", RichLog)
        
        try:
            payload, autofilled = self.assembler.assemble(op_id, cli_params)
            
            # Notify autofilled params
            for key in autofilled:
                output_log.write(f"[dim italic]Autofilled from state: {key}[/dim italic]")
            
            # Validate default_response_field
            if cmd_conf and cmd_conf.default_response_field and not cmd_conf.force_response_field:
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
                        resolved = SchemaPathResolver.resolve_data(data, cmd_conf.default_response_field)
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
                            Syntax(json.dumps(display_data, indent=2), "json", background_color="default"),
                            title=title,
                            border_style="green"
                        )
                    )
                    
                    if debug:
                        output_log.write(
                            Panel(
                                Syntax(json.dumps(data, indent=2), "json", background_color="default"),
                                title="[bold yellow]Raw Response (Debug)[/bold yellow]",
                                border_style="dim"
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
                                output_log.write(f"[dim]State updated: {state_key}[/dim]")
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
                    Syntax(json.dumps(block_data, indent=2), "json", background_color="default")
                )
            else:
                blocks_content.extend(self._get_list_items(block_data, block.fields))
            
            blocks_content.append("")
        
        output_log.write(Panel(Group(*blocks_content), title=title))
        
        if debug:
            output_log.write(
                Panel(
                    Syntax(json.dumps(data, indent=2), "json", background_color="default"),
                    title="[bold yellow]Raw Response (Debug)[/bold yellow]",
                    border_style="dim"
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
