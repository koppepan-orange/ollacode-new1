"""Agent loop: orchestrates LLM calls and tool execution."""
from __future__ import annotations

import json
from typing import Any

from ollacode.client import OllamaClient
from ollacode.config import DEFAULT_MODEL, DEFAULT_OLLAMA_URL
from ollacode.prompts import SYSTEM_PROMPT
from ollacode.tools import execute_tool, get_tool_schemas

MAX_ITERATIONS = 30


class Agent:
    """Agentic loop that calls Ollama and executes tools."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        confirm_commands: bool = False,
        work_dir: str = ".",
        ui: Any = None,
    ):
        self.model = model
        self.client = OllamaClient(base_url=ollama_url)
        self.confirm_commands = confirm_commands
        self.work_dir = work_dir
        self.ui = ui
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.tool_call_count = 0

    def chat(self, user_message: str) -> str:
        """Process a user message through the agentic loop."""
        self.messages.append({"role": "user", "content": user_message})
        return self._run_loop()

    def clear_history(self):
        """Reset conversation to system prompt only."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_call_count = 0

    def _run_loop(self) -> str:
        """Run the agentic loop until the model stops calling tools."""
        tools = get_tool_schemas()

        for iteration in range(MAX_ITERATIONS):
            if self.ui:
                self.ui.show_thinking()

            response = self.client.collect_stream(
                model=self.model,
                messages=self.messages,
                tools=tools,
                on_token=self._on_token,
            )

            if "error" in response:
                error_msg = f"Error: {response['error']}"
                if self.ui:
                    self.ui.show_error(error_msg)
                return error_msg

            message = response["message"]
            metrics = response.get("metrics", {})
            self.messages.append(message)

            if self.ui and metrics.get("tokens_per_sec"):
                self.ui.show_metrics(metrics)

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return message.get("content", "")

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                tool_args = func.get("arguments", {})

                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError as e:
                        result = {"error": f"Invalid tool arguments for {tool_name}: {e}"}
                        self.tool_call_count += 1
                        if self.ui:
                            self.ui.show_tool_call(tool_name, {})
                            self.ui.show_tool_result(tool_name, result)
                        self.messages.append({
                            "role": "tool",
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                        continue

                if not isinstance(tool_args, dict):
                    result = {"error": f"Tool arguments for {tool_name} must be an object."}
                    self.tool_call_count += 1
                    if self.ui:
                        self.ui.show_tool_call(tool_name, {})
                        self.ui.show_tool_result(tool_name, result)
                    self.messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                    continue

                if tool_name == "run_command" and self.confirm_commands:
                    tool_args["confirm"] = True

                if tool_name in (
                    "read_file", "write_file", "edit_file", "run_command",
                    "list_dir", "file_tree", "grep_search", "python_env",
                    "browser_control"
                ) and "cwd" not in tool_args:
                    tool_args["cwd"] = self.work_dir

                if self.ui:
                    self.ui.show_tool_call(tool_name, tool_args)

                result = execute_tool(tool_name, tool_args)
                self.tool_call_count += 1

                if self.ui:
                    self.ui.show_tool_result(tool_name, result)

                self.messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return "Max iterations reached. The task may be incomplete."

    def _on_token(self, token: str):
        if self.ui:
            self.ui.stream_token(token)

    @property
    def history_summary(self) -> dict[str, int]:
        return {
            "messages": len(self.messages),
            "tool_calls": self.tool_call_count,
        }
