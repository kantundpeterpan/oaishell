import shlex
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

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

    def show_help(self):
        table = Table(title="Available Commands")
        table.add_column("Command")
        table.add_column("Description")
        for cmd, conf in self.config.commands.items():
            table.add_row(cmd, conf.description or "")
        console.print(table)

    def handle_call(self, args: List[str]):
        if not args:
            console.print("[red]Usage: /call <operation_id> [--param value][/red]")
            return
        
        op_id = args[0]
        # Very basic flag parsing for now
        cli_params = {}
        i = 1
        while i < len(args):
            if args[i].startswith("--"):
                key = args[i][2:]
                if i + 1 < len(args):
                    cli_params[key] = args[i+1]
                    i += 2
                else:
                    cli_params[key] = True
                    i += 1
            else: i += 1

        self._execute_call(op_id, cli_params)

    def handle_custom_command(self, cmd: str, args: List[str]):
        conf = self.config.commands[cmd]
        op_id = conf.operationId
        
        # Build params from mapping
        cli_params = {}
        for key, template in conf.mapping.items():
            cli_params[key] = self.assembler.resolve_value(template, args)
            
        self._execute_call(op_id, cli_params)

    def _execute_call(self, op_id: str, cli_params: Dict[str, Any]):
        # Auto-inject state
        for key in self.config.state.auto_inject:
            if key not in cli_params:
                val = self.state.get(key)
                if val: cli_params[key] = val

        payload = self.assembler.assemble(op_id, cli_params)
        
        try:
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
