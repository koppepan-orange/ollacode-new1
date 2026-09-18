"""Rich + prompt_toolkit terminal UI for OllaCode. Cross-platform."""
from __future__ import annotations

import json
from typing import Any
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

class OllaCodeUI:
    def __init__(self):
        self.console = Console()
        self._streaming_started = False

    def show_banner(self, model: str, ollama_url: str):
        banner = Text()
        banner.append("🥖 OllaCode", style="bold cyan")
        banner.append(" — Local AI Coding Agent\n", style="dim")
        banner.append("  Model : ", style="dim")
        banner.append(model, style="green")
        banner.append("\n  Server: ", style="dim")
        banner.append(ollama_url, style="blue")
        self.console.print(Panel(banner, border_style="cyan", padding=(0, 1)))
        self.console.print('Type [bold cyan]/help[/] for commands, [bold cyan]/exit[/] to quit.\n')

    def stream_token(self, token: str):
        if not self._streaming_started:
            self.console.print("\n[bold green]◆ OllaCode:[/]")
            self._streaming_started = True
        self.console.print(token, end="", markup=False, highlight=False)

    def end_stream(self):
        if self._streaming_started:
            self.console.print()
            self._streaming_started = False

    def show_thinking(self):
        self._streaming_started = False
        self.console.print("\n[dim]⟳ Thinking...[/dim]")

    def show_tool_call(self, name: str, args: dict[str, Any]):
        args_str = json.dumps(args, ensure_ascii=False, indent=2)
        panel = Panel(Syntax(args_str, "json", theme="monokai", word_wrap=True), title=f"[bold yellow]⚙ Tool: {escape(name)}[/]", border_style="yellow", padding=(0, 1))
        self.console.print(panel)

    def show_tool_result(self, name: str, result: Any):
        if isinstance(result, dict) and "error" in result:
            result_str = f"[bold red]Error:[/] {escape(str(result['error']))}"
            self.console.print(f"  [dim]↳ {escape(name)}:[/] {result_str}")
        else:
            result_str = json.dumps(result, ensure_ascii=False)
            if len(result_str) > 400: result_str = result_str[:400] + " … (truncated)"
            self.console.print(f"  [dim]↳ {escape(name)} →[/] [green]OK[/] [dim]{escape(result_str[:120])}[/]")

    def show_metrics(self, metrics: dict[str, Any]):
        self.console.print(f"  [dim]({metrics.get('tokens', 0)} tokens, {metrics.get('tokens_per_sec', 0.0)} tok/s)[/dim]")

    def show_error(self, message: str): self.console.print(f"[bold red]✗ Error:[/] {escape(message)}")
    def show_info(self, message: str): self.console.print(f"[dim]{escape(message)}[/dim]")

    def show_models(self, models: list[dict[str, Any]]):
        if not models:
            self.console.print("[yellow]No models found. Run: ollama pull qwen2.5-coder:7b[/]"); return
        table=Table(title="Available Ollama Models", border_style="cyan"); table.add_column("Name",style="green"); table.add_column("Size",justify="right"); table.add_column("Modified")
        for m in models:
            size=m.get("size",0); size_str=f"{size/1e9:.1f} GB" if size>1e9 else f"{size/1e6:.0f} MB"; table.add_row(m.get("name",""),size_str,m.get("modified_at","")[:10])
        self.console.print(table)

    def show_tools(self):
        from ollacode.tools import TOOLS
        table=Table(title="Available Tools",border_style="cyan"); table.add_column("Tool",style="green"); table.add_column("Description")
        descriptions={"read_file":"Read file with line numbers","write_file":"Create or overwrite a file","edit_file":"Targeted string replacement","run_command":"Execute shell commands","list_dir":"List directory contents","file_tree":"Show project directory tree","grep_search":"Search code with regex","python_env":"Manage Python venv","web_search":"Search web via DuckDuckGo","browser_control":"Control browser with Playwright"}
        for name in TOOLS: table.add_row(name,descriptions.get(name,""))
        self.console.print(table)

    def show_help(self):
        text="""[bold cyan]OllaCode Slash Commands[/]\n\n  [green]/help[/]            Show this help\n  [green]/models[/]          List downloaded Ollama models\n  [green]/model <name>[/]    Switch to a different model\n  [green]/tools[/]           Show available agent tools\n  [green]/clear[/]           Clear conversation history\n  [green]/history[/]         Show message count and tool call stats\n  [green]/config[/]          Show current configuration\n  [green]/exit[/], [green]/quit[/]    Exit OllaCode\n"""
        self.console.print(Panel(text.strip(),title="Help",border_style="cyan"))

    def show_config(self, config: dict[str, Any]):
        table=Table(title="Configuration",border_style="cyan"); table.add_column("Key",style="green"); table.add_column("Value")
        for k,v in config.items(): table.add_row(str(k),str(v))
        self.console.print(table)

    def show_history(self, summary: dict[str, Any]):
        self.console.print(f"  Messages   : [cyan]{summary.get('messages', 0)}[/]")
        self.console.print(f"  Tool calls : [cyan]{summary.get('tool_calls', 0)}[/]")

def get_user_input(history_file: str | None = None) -> str | None:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.styles import Style
        style=Style.from_dict({"prompt":"ansicyan bold"}); kwargs={"auto_suggest":AutoSuggestFromHistory(),"style":style}
        if history_file:
            import pathlib; pathlib.Path(history_file).parent.mkdir(parents=True,exist_ok=True); kwargs["history"]=FileHistory(str(history_file))
        return PromptSession(**kwargs).prompt("You > ")
    except ImportError:
        try:return input("You > ")
        except (EOFError,KeyboardInterrupt):return None
    except (EOFError,KeyboardInterrupt):return None
    except Exception:
        try:return input("You > ")
        except (EOFError,KeyboardInterrupt):return None
