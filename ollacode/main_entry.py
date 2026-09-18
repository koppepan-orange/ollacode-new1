"""Main entry point for OllaCode (python -m ollacode and ollacode command)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ollacode import __version__
from ollacode.config import (
    CONFIG_DIR,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    HISTORY_FILE,
    get_ollama_url,
)
from ollacode.agent import Agent
from ollacode.ui import OllaCodeUI, get_user_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ollacode",
        description="OllaCode - Local AI Coding Agent powered by Ollama",
    )
    parser.add_argument("prompt", nargs="*", help="One-shot prompt to execute")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("-u", "--url", default=DEFAULT_OLLAMA_URL, help="Ollama server URL")
    parser.add_argument("-d", "--dir", default=".", help="Working directory")
    parser.add_argument(
        "-c", "--confirm-commands",
        action="store_true",
        help="Ask for confirmation before each command",
    )
    parser.add_argument("-v", "--version", action="version", version=f"OllaCode {__version__}")
    return parser


def run_interactive(agent: Agent, ui: OllaCodeUI, work_dir: str):
    """Run the interactive REPL."""
    ui.show_banner(agent.model, agent.client.base_url)

    history_path = str(HISTORY_FILE)

    while True:
        try:
            user_input = get_user_input(history_file=history_path)
        except KeyboardInterrupt:
            ui.show_info("\nUse /exit or /quit to quit.")
            continue

        if user_input is None:
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split()
            cmd = parts[0].lower()

            if cmd in ("/exit", "/quit"):
                ui.show_info("Goodbye!")
                break
            elif cmd == "/help":
                ui.show_help()
            elif cmd == "/models":
                models = agent.client.list_models()
                if models and "_error" in models[0]:
                    ui.show_error(models[0]["_error"])
                else:
                    ui.show_models(models)
            elif cmd == "/model":
                if len(parts) < 2:
                    ui.show_error("Usage: /model <model-name>")
                else:
                    agent.model = parts[1]
                    ui.show_info(f"Switched to model: {agent.model}")
            elif cmd == "/tools":
                ui.show_tools()
            elif cmd == "/clear":
                agent.clear_history()
                ui.show_info("Conversation history cleared.")
            elif cmd == "/history":
                ui.show_history(agent.history_summary)
            elif cmd == "/config":
                ui.show_config({
                    "model": agent.model,
                    "ollama_url": agent.client.base_url,
                    "work_dir": work_dir,
                    "config_dir": str(CONFIG_DIR),
                })
            else:
                ui.show_error(f"Unknown command: {cmd}. Type /help for help.")
            continue

        try:
            response = agent.chat(user_input)
            ui.end_stream()
        except KeyboardInterrupt:
            ui.show_info("\nInterrupted.")
        except Exception as e:
            ui.show_error(f"Unexpected error: {e}")


def main():
    """CLI entry point."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()

    work_dir = str(Path(args.dir).resolve())
    url = args.url or get_ollama_url()

    ui = OllaCodeUI()
    agent = Agent(
        model=args.model,
        ollama_url=url,
        confirm_commands=args.confirm_commands,
        work_dir=work_dir,
        ui=ui,
    )

    if not agent.client.is_available():
        ui.show_error(
            f"Cannot connect to Ollama at {url}.\n"
            "Make sure Ollama is running: https://ollama.com"
        )
        sys.exit(1)

    if args.prompt:
        prompt_text = " ".join(args.prompt)
        response = agent.chat(prompt_text)
        ui.end_stream()
    else:
        run_interactive(agent, ui, work_dir)


if __name__ == "__main__":
    main()
