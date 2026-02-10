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

from ..engine.client import OpenAIEngine, ClientState, EngineError
from ..engine.utils import PayloadAssembler
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

class ShellRunner:
    def __init__(self, config: ShellConfig, engine: OpenAIEngine):
        self.config = config
        self.engine = engine
        self.state = ClientState(persistence_file=config.state.storage)
        # Load defaults into state
        self.state.update(**config.state.defaults)
        self.assembler = PayloadAssembler(self.engine, self.state)
        self.session = PromptSession(
            completer=OAIShellCompleter(self.engine, self.config),
            history=InMemoryHistory()
        )

    def run(self):
        console.print(Panel(f"[bold green]Welcome to {self.config.name}[/bold green]\nConnected to {self.engine.base_url}"))
        
        # Initial operation list to populate completer
        if not self.engine.operations:
            console.print("[yellow]Warning: No operations discovered yet.[/yellow]")

        while True:
            try:
                line = self.session.prompt(f"{self.config.name} > ").strip()
                if not line: continue
                if line == "/exit": break
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

    def show_state(self):
        table = Table(title="Current State")
        table.add_column("Key")
        table.add_column("Value")
        for k, v in self.state.to_dict().items():
            table.add_row(k, str(v))
        console.print(table)

    def show_operations_tui(self):
        """Interactive hierarchical view of operations."""
        tag_groups: Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]] = {}
        for op_id, op in self.engine.operations.items():
            tags = op["raw"].get("tags", ["default"])
            for tag in tags:
                if tag not in tag_groups: tag_groups[tag] = {}
                path = op["path"]
                if path not in tag_groups[tag]: tag_groups[tag][path] = []
                tag_groups[tag][path].append((op_id, op))

        # Build a stable structured list for state management
        # Each item is a reference that we can toggle 'expanded' on
        structured = []
        for tag in sorted(tag_groups.keys()):
            tag_item = {"type": "tag", "name": tag, "expanded": True}
            structured.append(tag_item)
            paths = tag_groups[tag]
            for path in sorted(paths.keys()):
                path_item = {
                    "type": "path", 
                    "name": path, 
                    "tag": tag, 
                    "expanded": False, 
                    "ops": sorted(paths[path], key=lambda x: x[0])
                }
                structured.append(path_item)

        selected_idx = 0

        def get_visible_items():
            visible = []
            for item in structured:
                if item["type"] == "tag":
                    visible.append(item)
                    if not item["expanded"]:
                        continue
                elif item["type"] == "path":
                    # Only show if parent tag is expanded (handled by loop logic)
                    visible.append(item)
                    if item["expanded"]:
                        for op_id, op_data in item["ops"]:
                            visible.append({"type": "op", "name": op_id, "op": op_data})
            return visible

        try:
            input_stream = create_input()
            # We must use raw_mode to capture keys without them being echoed
            with input_stream.raw_mode():
                # We hide the cursor for a better TUI experience
                console.show_cursor(False)
                with Live(auto_refresh=False, console=console, transient=True) as live:
                    while True:
                        visible_items = get_visible_items()
                        selected_idx = max(0, min(selected_idx, len(visible_items) - 1))
                        
                        # Build the renderable tree
                        tree = Tree(f"[bold magenta]{self.config.name} API Explorer[/bold magenta] [dim](↑/↓ navigate, Space/Enter toggle, 'q' back)[/dim]")
                        for idx, item in enumerate(visible_items):
                            is_sel = (idx == selected_idx)
                            prefix = "> " if is_sel else "  "
                            style = "reverse" if is_sel else ""

                            if item["type"] == "tag":
                                icon = "▼" if item["expanded"] else "▶"
                                tree.add(f"{prefix}[bold cyan]{icon} {item['name']}[/bold cyan]", style=style)
                            elif item["type"] == "path":
                                icon = "▼" if item["expanded"] else "▶"
                                tree.add(f"  {prefix}[blue]{icon} {item['name']}[/blue]", style=style)
                            elif item["type"] == "op":
                                op = item["op"]
                                m = op["method"]
                                m_col = {"GET": "green", "POST": "yellow", "PUT": "blue", "DELETE": "red"}.get(m, "white")
                                node = tree.add(f"    {prefix}[{m_col}]{m}[/{m_col}] [bold]{item['name']}[/bold]", style=style)
                                if is_sel:
                                    all_params = self.engine.get_params_for_operation(item["name"])
                                    if all_params:
                                        p_node = node.add("[dim]Parameters[/dim]")
                                        for p in all_params:
                                            p_node.add(f"[dim]{p['name']} ({p['type']})[/dim] [yellow]in:{p['in']}[/yellow]")

                        live.update(tree, refresh=True)

                        # Handle input with a short timeout to keep UI responsive but not spin
                        # read_keys() is non-blocking in prompt_toolkit by default if nothing is in buffer
                        keys = input_stream.read_keys()
                        for k in keys:
                            if k.key == Keys.Up:
                                selected_idx -= 1
                            elif k.key == Keys.Down:
                                selected_idx += 1
                            elif k.key in (Keys.ControlM, " "): # Enter/Space
                                curr = visible_items[selected_idx]
                                if curr["type"] in ("tag", "path"):
                                    curr["expanded"] = not curr["expanded"]
                            elif k.key == "q" or k.key == Keys.ControlC:
                                return
                        time.sleep(0.05)
        except Exception as e:
            console.print(f"[red]TUI Error: {e}[/red]")
        finally:
            console.show_cursor(True)

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

    def handle_call(self, args: List[str]):
        if not args:
            console.print("[red]Usage: /call <operation_id> [--param value] [--stream][/red]")
            return
        
        op_id = args[0]
        # Very basic flag parsing for now
        cli_params = {}
        stream = False
        i = 1
        while i < len(args):
            if args[i] == "--stream":
                stream = True
                i += 1
            elif args[i].startswith("--"):
                key = args[i][2:]
                if i + 1 < len(args) and not args[i+1].startswith("--"):
                    cli_params[key] = args[i+1]
                    i += 2
                else:
                    cli_params[key] = True
                    i += 1
            else: i += 1

        self._execute_call(op_id, cli_params, stream=stream)

    def handle_custom_command(self, cmd: str, args: List[str]):
        conf = self.config.commands[cmd]
        op_id = conf.operationId
        
        # Build params from mapping
        cli_params = {}
        for key, template in conf.mapping.items():
            cli_params[key] = self.assembler.resolve_value(template, args)
            
        self._execute_call(op_id, cli_params)

    def _execute_call(self, op_id: str, cli_params: Dict[str, Any], stream: bool = False):
        # Auto-inject state
        for key in self.config.state.auto_inject:
            if key not in cli_params:
                val = self.state.get(key)
                if val: cli_params[key] = val

        payload = self.assembler.assemble(op_id, cli_params)
        
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
                
                # Print response
                console.print(Panel(json.dumps(data, indent=2), title="[bold blue]Response[/bold blue]"))
                
                # After call hooks
                conf = next((c for k, c in self.config.commands.items() if c.operationId == op_id), None)
                if conf and conf.after_call:
                    save = conf.after_call.get("save_to_state", {})
                    for state_key, path in save.items():
                        # Simple JSON path: "json:key" or "json:nested.key"
                        if path.startswith("json:"):
                            key_path = path[5:].split('.')
                            val = data
                            try:
                                for p in key_path: val = val[p]
                                self.state.update(**{state_key: val})
                                console.print(f"[dim]State updated: {state_key}[/dim]")
                            except: pass
        except EngineError as e:
            console.print(f"[red]API Error:[/red] {e}")
