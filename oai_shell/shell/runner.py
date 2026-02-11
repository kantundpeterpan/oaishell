import shlex
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.live import Live
from rich.console import Console, Group
from rich.style import Style
import sys
import time

# For key capture
try:
    from prompt_toolkit.input import create_input
    from prompt_toolkit.keys import Keys
except ImportError:
    pass

from prompt_toolkit import PromptSession

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory

from rich.layout import Layout
from rich.markdown import Markdown
from rich.syntax import Syntax

from ..engine.client import OpenAIEngine, ClientState, EngineError
from ..engine.utils import PayloadAssembler, SchemaPathResolver
from ..config.models import ShellConfig

console = Console()
logger = logging.getLogger("oai_shell.shell")

class OAIShellCompleter(Completer):
    def __init__(self, engine: OpenAIEngine, config: ShellConfig):
        self.engine = engine
        self.config = config

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if not text:
            return

        # Complete custom commands from YAML
        if text.startswith('/') and (len(words) <= 1 or not ' ' in text):
            # Internal commands
            internals = {
                '/help': 'Show help',
                '/exit': 'Exit shell',
                '/state': 'Show current state',
                '/operations': 'List available API operations',
                '/operations-tui': 'Interactive API explorer',
                '/call': 'Call raw operation'
            }
            
            for cmd, desc in internals.items():
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display_meta=desc)
            
            for cmd, cmd_conf in self.config.commands.items():
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display_meta=cmd_conf.description)

        # Complete operation IDs after /call
        elif text.startswith('/call ') and len(words) == 2 and not text.endswith(' '):
            prefix = words[1]
            for op_id in self.engine.operations.keys():
                if op_id.lower().startswith(prefix.lower()):
                    yield Completion(op_id, start_position=-len(prefix))

        # Complete parameter flags after /call <op_id>
        elif text.startswith('/call ') and len(words) >= 2:
            op_id = words[1]
            if op_id in self.engine.operations:
                current_word = words[-1] if text.endswith(words[-1]) else ""
                if current_word.startswith('--'):
                    prefix = current_word[2:]
                    all_params = self.engine.get_params_for_operation(op_id)
                    
                    for p in all_params:
                        name = p['name']
                        if name.lower().startswith(prefix.lower()):
                            yield Completion(f"--{name}", start_position=-len(current_word), display_meta=f"({p['in']}) {p['type']}")
                    
                    # Special flags
                    if "stream".startswith(prefix.lower()):
                        yield Completion("--stream", start_position=-len(current_word))

class ResponseRenderer:
    def __init__(self, console: Console):
        self.console = console

    def render(self, data: Any, config: Optional[Any], debug: bool = False):
        if not config:
            self._render_json(data, "[bold blue]Response[/bold blue]", debug)
            return

        title = config.title or "[bold blue]Response[/bold blue]"
        
        blocks_content = []
        for block in config.blocks:
            block_data = SchemaPathResolver.resolve_data(data, block.path)
            if block_data is None:
                if block.optional: continue
                block_data = {} # Fallback

            if block.title:
                blocks_content.append(f"[bold underline]{block.title}[/bold underline]")

            if block.layout == "table":
                blocks_content.append(self._get_table(block_data, block.fields))
            elif block.layout == "markdown":
                blocks_content.append(Markdown(str(block_data)))
            elif block.layout == "json":
                blocks_content.append(Syntax(json.dumps(block_data, indent=2), "json", background_color="default"))
            else:
                blocks_content.extend(self._get_list_items(block_data, block.fields))
            
            # Add spacing between blocks
            blocks_content.append("")

        self.console.print(Panel(Group(*blocks_content), title=title))

        if debug:
            self.console.print(Panel(json.dumps(data, indent=2), title="[bold yellow]Raw Response (Debug)[/bold yellow]", border_style="dim"))

    def _render_json(self, data: Any, title: str, debug: bool = False):
        self.console.print(Panel(json.dumps(data, indent=2), title=title))

    def _get_list_items(self, data: Any, fields: List[Any]) -> List[Any]:
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

    def _get_table(self, data: Any, fields: List[Any]) -> Table:
        # Data should be a list for table layout
        rows = data if isinstance(data, list) else [data]
        
        table = Table(box=None, padding=(0, 1))
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

class ShellRunner:
    def __init__(self, config: ShellConfig, engine: OpenAIEngine):
        self.config = config
        self.engine = engine
        self.state = ClientState(persistence_file=config.state.storage)
        # Load defaults into state
        self.state.update(**config.state.defaults)
        self.assembler = PayloadAssembler(self.engine, self.state)
        self.renderer = ResponseRenderer(console)
        self.session = PromptSession(
            completer=OAIShellCompleter(self.engine, self.config),
            history=InMemoryHistory()
        )

    def run(self):
        console.print(Panel(f"[bold green]Welcome to {self.config.name}[/bold green]\nConnected to {self.engine.base_url}"))
        
        # Initial operation list to populate completer
        if not self.engine.operations:
            console.print("[yellow]Warning: No operations discovered yet.[/yellow]")

        # Validate configured commands at startup
        for cmd_name, cmd_conf in self.config.commands.items():
            op = self.engine.operations.get(cmd_conf.operationId)
            if not op:
                console.print(f"[dim yellow]Info: Command '{cmd_name}' targets unknown operation '{cmd_conf.operationId}'. Validation skipped.[/dim yellow]")
                continue

            # 1. Validate default_response_field
            if cmd_conf.default_response_field and not cmd_conf.force_response_field:
                resp_200 = op.get("responses", {}).get("200", {})
                content = resp_200.get("content", {})
                json_schema = content.get("application/json", {}).get("schema")
                if json_schema:
                    if not SchemaPathResolver.validate_path(json_schema, cmd_conf.default_response_field, self.engine):
                        console.print(f"[yellow]Warning:[/yellow] Command '{cmd_name}' has default_response_field '{cmd_conf.default_response_field}' which may not exist in the schema.")
                else:
                    console.print(f"[dim yellow]Info: Command '{cmd_name}' has default_response_field but no 200 OK JSON schema found. Validation skipped.[/dim yellow]")

            # 2. Validate formatting blocks
            if cmd_conf.formatting and not cmd_conf.force_response_field:
                resp_200 = op.get("responses", {}).get("200", {})
                content = resp_200.get("content", {})
                json_schema = content.get("application/json", {}).get("schema")
                if json_schema:
                    for block in cmd_conf.formatting.blocks:
                        # Resolve path to the block's root
                        block_schema = json_schema
                        if block.path:
                            # We might need a SchemaPathResolver.get_sub_schema but for now we validate paths from root
                            # if block.path != "": 
                            #   ...
                            pass
                        
                        for field in block.fields:
                            full_path = f"{block.path}.{field.path}" if block.path and field.path else (block.path or field.path)
                            if full_path == "": continue
                            if not SchemaPathResolver.validate_path(json_schema, full_path, self.engine):
                                console.print(f"[yellow]Warning:[/yellow] Command '{cmd_name}' formatting block path '{full_path}' may not exist in the schema.")

        next_prompt_default = ""

        while True:
            try:
                line = self.session.prompt(
                    f"{self.config.name} > ", 
                    default=next_prompt_default
                ).strip()
                next_prompt_default = "" # Reset after use
                
                if not line: continue
                if line == "/exit": break
                
                # Check if it's a TUI call that might return a selection
                if line == "/operations-tui":
                    result = self.show_operations_tui()
                    if result:
                        next_prompt_default = result
                else:
                    self.handle_input(line)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

    def handle_input(self, line: str):
        if line.startswith("/"):
            parts = shlex.split(line)
            cmd = parts[0]
            args = parts[1:]

            if cmd == "/help":
                self.show_help()
            elif cmd == "/operations":
                self.show_operations()
            elif cmd == "/operations-tui":
                self.show_operations_tui()
            elif cmd == "/state":
                self.show_state()
            elif cmd == "/call":
                self.handle_call(args)
            elif cmd in self.config.commands:
                self.handle_custom_command(cmd, args)
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
        else:
            console.print("[dim]Use /command or /call. Type /help for list.[/dim]")

    def _build_schema_tree(self, schema: Dict[str, Any], tree: Optional[Tree] = None, name: str = "root") -> Tree:
        """Recursively builds a Rich Tree from an OpenAPI schema."""
        schema = self.engine.resolve_schema(schema)
        s_type = schema.get("type", "object")
        description = schema.get("description", "")
        
        # Color mapping for types
        type_col = {
            "object": "blue",
            "array": "yellow",
            "string": "green",
            "integer": "cyan",
            "number": "cyan",
            "boolean": "magenta"
        }.get(s_type, "white")
        
        icon = self.config.tui.type_icons.get(s_type, self.config.tui.type_icons.get("default", ""))
        label = f"{icon} [bold cyan]{name}[/bold cyan] [dim][{type_col}]({s_type})[/{type_col}][/dim]"
        if description:
            label += f" - [italic]{description}[/italic]"
            
        if tree is None:
            res_tree = Tree(label)
        else:
            res_tree = tree.add(label)
            
        if s_type == "object":
            props = schema.get("properties", {})
            required = schema.get("required", [])
            for p_name, p_schema in props.items():
                p_label = p_name
                if p_name in required:
                    p_label = f"[bold white]{p_name}*[/bold white]"
                self._build_schema_tree(p_schema, res_tree, p_label)
        elif s_type == "array":
            items = schema.get("items", {})
            self._build_schema_tree(items, res_tree, "items[]")
            
        return res_tree

    def show_state(self):
        table = Table(title="Current State")
        table.add_column("Key")
        table.add_column("Value")
        for k, v in self.state.to_dict().items():
            table.add_row(k, str(v))
        console.print(table)

    def show_operations_tui(self) -> Optional[str]:
        """Interactive hierarchical view of operations. Returns selected command if any."""
        depth = self.config.tui.aggregation_depth
        tag_groups: Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]] = {}
        
        for op_id, op in self.engine.operations.items():
            tags = op["raw"].get("tags", ["default"])
            for tag in tags:
                if tag not in tag_groups: tag_groups[tag] = {}
                path = op.get("display_path", op["path"])
                parts = path.strip('/').split('/')
                if depth > 0 and len(parts) > depth:
                    group_path = '/' + '/'.join(parts[:depth]) + '/...'
                else:
                    group_path = path
                if group_path not in tag_groups[tag]: tag_groups[tag][group_path] = []
                tag_groups[tag][group_path].append((op_id, op))

        structured = []
        for tag in sorted(tag_groups.keys()):
            display_tag = tag
            if self.engine.common_prefix:
                display_tag = f"{tag} [dim]({self.engine.common_prefix})[/dim]"
            structured.append({"type": "tag", "name": tag, "display_name": display_tag, "expanded": True})
            paths = tag_groups[tag]
            for path in sorted(paths.keys()):
                structured.append({"type": "path", "name": path, "tag": tag, "expanded": False, "ops": sorted(paths[path], key=lambda x: x[0])})

        selected_idx = 0

        def get_visible_items():
            visible = []
            for item in structured:
                if item["type"] == "tag":
                    visible.append(item)
                    if not item["expanded"]: continue
                elif item["type"] == "path":
                    visible.append(item)
                    if item["expanded"]:
                        for op_id, op_data in item["ops"]:
                            visible.append({"type": "op", "name": op_id, "op": op_data})
            return visible

        def make_schema_view(op_id: str):
            op = self.engine.operations.get(op_id)
            if not op: return Panel("No operation selected")
            
            # Request Panel
            req_content = []
            
            # 1. Standard Parameters
            params = []
            for p in op.get("parameters", []):
                params.append({
                    "name": p["name"],
                    "in": p.get("in", "query"),
                    "type": p.get("schema", {}).get("type", "string"),
                    "required": p.get("required", False)
                })
            
            if params:
                table = Table(title="Parameters", box=None, padding=(0, 1), expand=True)
                table.add_column("Name", style="cyan", ratio=2)
                table.add_column("In", style="yellow", ratio=1)
                table.add_column("Type", style="magenta", ratio=1)
                for p in params:
                    name = f"[bold]{p['name']}*[/bold]" if p["required"] else p["name"]
                    table.add_row(name, p["in"], p["type"])
                req_content.append(table)

            # 2. Request Body
            body = op.get("requestBody")
            if body:
                content = body.get("content", {})
                json_schema = content.get("application/json", {}).get("schema")
                if json_schema:
                    req_content.append(self._build_schema_tree(json_schema, name="RequestBody (JSON)"))

            # Response Panel
            res_200 = op.get("responses", {}).get("200", {})
            res_content_spec = res_200.get("content", {})
            res_json_schema = res_content_spec.get("application/json", {}).get("schema")
            
            if res_json_schema:
                res_view = self._build_schema_tree(res_json_schema, name="Response (200 OK)")
            else:
                res_view = Panel("No response schema (application/json) found for 200 OK", border_style="dim")

            layout = Layout()
            layout.split_row(
                Layout(Panel(Group(*req_content), title="Request"), name="req"),
                Layout(Panel(res_view, title="Response"), name="res")
            )
            return layout

        try:
            input_stream = create_input()
            with input_stream.raw_mode():
                console.show_cursor(False)
                with Live(auto_refresh=False, console=console, transient=True) as live:
                    while True:
                        visible_items = get_visible_items()
                        selected_idx = max(0, min(selected_idx, len(visible_items) - 1))
                        
                        header = f"[bold magenta]{self.config.name} API Explorer[/bold magenta]"
                        tree = Tree(f"{header} [dim](↑/↓, Space/Enter, 'q' back)[/dim]")
                        
                        for idx, item in enumerate(visible_items):
                            is_sel = (idx == selected_idx)
                            style = "reverse" if is_sel else ""
                            prefix = "> " if is_sel else "  "

                            if item["type"] == "tag":
                                icon = "▼" if item["expanded"] else "▶"
                                tree.add(f"{prefix}[bold cyan]{icon} {item['display_name']}[/bold cyan]", style=style)
                            elif item["type"] == "path":
                                icon = "▼" if item["expanded"] else "▶"
                                tree.add(f"  {prefix}[blue]{icon} {item['name']}[/blue]", style=style)
                            elif item["type"] == "op":
                                m = item["op"]["method"]
                                m_col = {"GET": "green", "POST": "yellow", "PUT": "blue", "DELETE": "red"}.get(m, "white")
                                tree.add(f"    {prefix}[{m_col}]{m}[/{m_col}] [bold]{item['name']}[/bold]", style=style)

                        main_layout = Layout()
                        main_layout.split_row(
                            Layout(Panel(tree), name="tree", ratio=1),
                            Layout(name="details", ratio=2)
                        )
                        
                        curr = visible_items[selected_idx]
                        if curr["type"] == "op":
                            main_layout["details"].update(make_schema_view(curr["name"]))
                        else:
                            main_layout["details"].update(Panel("Select an operation to view schemas", title="Details"))

                        live.update(main_layout, refresh=True)

                        keys = input_stream.read_keys()
                        for k in keys:
                            if k.key == Keys.Up: selected_idx -= 1
                            elif k.key == Keys.Down: selected_idx += 1
                            elif k.key in (Keys.ControlM, " "):
                                curr = visible_items[selected_idx]
                                if curr["type"] in ("tag", "path"):
                                    curr["expanded"] = not curr["expanded"]
                                elif curr["type"] == "op" and k.key == Keys.ControlM:
                                    op_id = curr["name"]
                                    cmd = f"/call {op_id}"
                                    all_params = self.engine.get_params_for_operation(op_id)
                                    required_missing = [p["name"] for p in all_params if p.get("required") and self.state.get(p["name"]) is None]
                                    for p_name in required_missing: cmd += f" --{p_name} "
                                    return cmd + " "
                            elif k.key == "q" or k.key == Keys.ControlC: return
                        time.sleep(0.05)
        except Exception as e: console.print(f"[red]TUI Error: {e}[/red]")
        finally: console.show_cursor(True)

    def show_help(self):
        table = Table(title="Internal Commands")
        table.add_column("Command")
        table.add_column("Description")
        table.add_row("/help", "Show this help")
        table.add_row("/operations", "List available API operations")
        table.add_row("/state", "Show current state")
        table.add_row("/call <op_id>", "Call a raw API operation")
        table.add_row("/exit", "Exit the shell")
        console.print(table)

        if self.config.commands:
            table = Table(title="Custom Commands")
            table.add_column("Command")
            table.add_column("Description")
            for cmd, conf in self.config.commands.items():
                table.add_row(cmd, conf.description or "")
            console.print(table)

    def show_operations(self):
        table = Table(title="Available Operations")
        table.add_column("Operation ID", style="cyan")
        table.add_column("Method", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Summary")
        
        for op_id, op in self.engine.operations.items():
            table.add_row(op_id, op["method"], op["path"], op["summary"])
        console.print(table)

    def _parse_cli_args(self, args: List[str]) -> Tuple[Dict[str, Any], List[str], bool, bool]:
        """Parses args into (params, positional_args, stream_flag, debug_flag)."""
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

    def handle_call(self, args: List[str]):
        if not args:
            console.print("[red]Usage: /call <operation_id> [--param value] [--stream] [--debug][/red]")
            return
        
        op_id = args[0]
        cli_params, _, stream, debug = self._parse_cli_args(args[1:])
        self._execute_call(op_id, cli_params, stream=stream, debug=debug)

    def handle_custom_command(self, cmd: str, args: List[str]):
        conf = self.config.commands[cmd]
        op_id = conf.operationId
        
        cli_flags, pos_args, stream, debug = self._parse_cli_args(args)

        # Build params from mapping using positional args
        cli_params = {}
        for key, template in conf.mapping.items():
            cli_params[key] = self.assembler.resolve_value(template, pos_args)
            
        # Merge CLI flags (they take precedence over mapping)
        cli_params.update(cli_flags)
        
        self._execute_call(op_id, cli_params, stream=stream, debug=debug)

    def _execute_call(self, op_id: str, cli_params: Dict[str, Any], stream: bool = False, debug: bool = False):
        payload, autofilled = self.assembler.assemble(op_id, cli_params)
        
        # Notify autofilled params
        for key in autofilled:
            console.print(f"[dim italic]Autofilled from state: {key}[/dim italic]")
        
        # Get command config if exists
        cmd_conf = next((c for k, c in self.config.commands.items() if c.operationId == op_id), None)
        
        # Validation of default_response_field
        if cmd_conf and cmd_conf.default_response_field and not cmd_conf.force_response_field:
            op = self.engine.operations.get(op_id)
            if op:
                resp_200 = op.get("responses", {}).get("200", {})
                content = resp_200.get("content", {})
                json_schema = content.get("application/json", {}).get("schema")
                if json_schema:
                    if not SchemaPathResolver.validate_path(json_schema, cmd_conf.default_response_field, self.engine):
                        console.print(f"[red]Error:[/red] default_response_field '{cmd_conf.default_response_field}' does not conform to the schema for operation {op_id}. Use force_response_field: true to override.")
                        return

        try:
            if stream:
                with self.engine.call(op_id, stream=True, **payload) as resp:
                    console.print("[bold blue]Streaming Response:[/bold blue]")
                    for line in resp.iter_lines():
                        if line:
                            console.print(line)
            else:
                resp = self.engine.call(op_id, **payload)
                data = resp.json()
                
                # Rendering using the new ResponseRenderer
                if cmd_conf and cmd_conf.formatting:
                    self.renderer.render(data, cmd_conf.formatting, debug=debug)
                else:
                    # Legacy support / Default fallback
                    display_data = data
                    title = "[bold blue]Response[/bold blue]"
                    if cmd_conf and cmd_conf.default_response_field:
                        resolved = SchemaPathResolver.resolve_data(data, cmd_conf.default_response_field)
                        if resolved is not None:
                            display_data = resolved
                            title = f"[bold blue]Response: {cmd_conf.default_response_field}[/bold blue]"
                        else:
                            console.print(f"[yellow]Warning: Field '{cmd_conf.default_response_field}' not found in the response payload.[/yellow]")

                    if debug:
                        group = Group(
                            Panel(json.dumps(display_data, indent=2), title=title, border_style="green"),
                            Panel(json.dumps(data, indent=2), title="[bold yellow]Raw Response (Debug)[/bold yellow]", border_style="dim")
                        )
                        console.print(group)
                    else:
                        console.print(Panel(json.dumps(display_data, indent=2), title=title))
                
                # After call hooks
                if cmd_conf and cmd_conf.after_call:
                    save = cmd_conf.after_call.get("save_to_state", {})
                    for state_key, path in save.items():
                        # Simple JSON path: "json:key" or "json:nested.key"
                        if path.startswith("json:"):
                            key_path = path[5:]
                            val = SchemaPathResolver.resolve_data(data, key_path)
                            if val is not None:
                                self.state.update(**{state_key: val})
                                console.print(f"[dim]State updated: {state_key}[/dim]")
        except EngineError as e:
            console.print(f"[red]API Error:[/red] {e}")
