"""Ollama API client with streaming and tool call support."""
from __future__ import annotations

import json
from typing import Any, Iterator
import urllib.request
import urllib.error


class OllamaClient:
    """Thin client for the Ollama REST API."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def list_models(self) -> list[dict[str, Any]]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            return data.get("models", [])
        except Exception as e:
            return [{"_error": str(e)}]

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream chat completion. Yields chunks as dicts."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except urllib.error.URLError as e:
            yield {"error": f"Connection failed: {e}"}
        except Exception as e:
            yield {"error": str(e)}

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming chat. Returns full response dict."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            return {"error": f"Connection failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def collect_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_token: Any = None,
    ) -> dict[str, Any]:
        """Stream a response and collect it."""
        full_content = ""
        tool_calls: list[dict[str, Any]] = []
        total_tokens = 0
        eval_duration_ns = 0

        for chunk in self.chat_stream(model, messages, tools=tools):
            if "error" in chunk:
                return {"error": chunk["error"]}

            msg = chunk.get("message", {})
            content_piece = msg.get("content", "")
            if content_piece:
                full_content += content_piece
                if on_token:
                    on_token(content_piece)

            tc = msg.get("tool_calls")
            if tc:
                tool_calls.extend(tc)

            if chunk.get("done"):
                total_tokens = chunk.get("eval_count", 0)
                eval_duration_ns = chunk.get("eval_duration", 0)
                break

        tokens_per_sec = 0.0
        if eval_duration_ns > 0:
            tokens_per_sec = total_tokens / (eval_duration_ns / 1e9)

        return {
            "message": {
                "role": "assistant",
                "content": full_content,
                "tool_calls": tool_calls if tool_calls else None,
            },
            "metrics": {
                "tokens": total_tokens,
                "tokens_per_sec": round(tokens_per_sec, 1),
            },
        }
