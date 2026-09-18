import tempfile
import unittest
from pathlib import Path

from ollacode.agent import Agent
from ollacode.client import OllamaClient
from ollacode.tools import execute_tool, validate_tool_call


class ToolValidationTests(unittest.TestCase):
    def test_unknown_argument_is_rejected(self):
        result = validate_tool_call("browser_control", {
            "action": "goto",
            "scroll": "true",
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertIn("Unknown argument: scroll", result["details"])

    def test_missing_required_argument_is_rejected(self):
        result = validate_tool_call("read_file", {})
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertIn("Missing required argument: path", result["details"])

    def test_wrong_type_is_rejected(self):
        result = validate_tool_call("browser_control", {
            "action": "goto",
            "headless": "false",
        })
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertIn("headless must be boolean", result["details"])

    def test_nested_unknown_argument_is_rejected(self):
        result = validate_tool_call("browser_control", {
            "steps": [{
                "action": "goto",
                "scroll": True,
            }]
        })
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertIn("Unknown argument: steps[0].scroll", result["details"])

    def test_nested_action_enum_is_rejected(self):
        result = validate_tool_call("browser_control", {
            "steps": [{
                "action": "gotoo",
            }]
        })
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertTrue(any("steps[0].action must be one of" in x for x in result["details"]))

    def test_unknown_tool_is_rejected(self):
        result = validate_tool_call("not_a_tool", {})
        self.assertEqual(result["error_type"], "unknown_tool")

    def test_execute_tool_does_not_raise_on_invalid_arguments(self):
        result = execute_tool("browser_control", {
            "action": "goto",
            "scroll": "true",
        })
        self.assertEqual(result["error_type"], "invalid_arguments")

    def test_agent_validates_before_workspace_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = Agent.__new__(Agent)
            agent.model = "test"
            agent.confirm_commands = False
            agent.work_dir = str(Path(tmp).resolve())
            agent.ui = None

            calls = [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "function": {
                                "name": "read_file",
                                "arguments": {
                                    "path": "x.txt",
                                    "cwd": 123,
                                },
                            }
                        }],
                    }
                },
                {
                    "message": {
                        "role": "assistant",
                        "content": "recovered",
                        "tool_calls": None,
                    }
                },
            ]

            class FakeClient:
                def __init__(self):
                    self.index = 0

                def collect_stream(self, **kwargs):
                    result = calls[self.index]
                    self.index += 1
                    return result

            agent.client = FakeClient()
            agent.messages = [{"role": "system", "content": "test"}]
            agent.tool_call_count = 0

            result = agent._run_loop()

            self.assertEqual(result, "recovered")
            self.assertEqual(agent.tool_call_count, 1)
            self.assertEqual(agent.messages[-2]["role"], "tool")
            self.assertEqual(agent.messages[-2]["tool_name"], "read_file")
            payload = agent.messages[-2]["content"]
            self.assertIn("invalid_arguments", payload)

    def test_workspace_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = Agent.__new__(Agent)
            agent.work_dir = str(Path(tmp).resolve())

            safe_args = {"path": "file.txt"}
            prepared, error = agent._prepare_tool_args("read_file", safe_args)
            self.assertIsNone(error)
            self.assertEqual(prepared["cwd"], agent.work_dir)

            _, error = agent._prepare_tool_args(
                "read_file",
                {"path": "file.txt", "cwd": str(Path(tmp).parent.resolve())},
            )
            self.assertIsNotNone(error)
            self.assertEqual(error["error_type"], "security_error")


    def test_stream_accumulates_tool_calls(self):
        client = OllamaClient()

        first_call = {
            "type": "function",
            "function": {
                "index": 0,
                "name": "read_file",
                "arguments": {"path": "one.txt"},
            },
        }
        second_call = {
            "type": "function",
            "function": {
                "index": 1,
                "name": "read_file",
                "arguments": {"path": "two.txt"},
            },
        }

        chunks = [
            {
                "message": {
                    "role": "assistant",
                    "content": "checking ",
                    "tool_calls": [first_call],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "files",
                    "tool_calls": [second_call],
                }
            },
            {
                "done": True,
                "eval_count": 10,
                "eval_duration": 1000000000,
            },
        ]

        client.chat_stream = lambda *args, **kwargs: iter(chunks)
        result = client.collect_stream("test", [], tools=[])

        self.assertEqual(result["message"]["content"], "checking files")
        self.assertEqual(result["message"]["tool_calls"], [first_call, second_call])

    def test_public_browser_ip_is_allowed(self):
        from ollacode.tools import _validate_browser_url
        _validate_browser_url("https://1.1.1.1")

    def test_private_browser_ip_is_blocked(self):
        from ollacode.tools import _validate_browser_url
        with self.assertRaises(ValueError):
            _validate_browser_url("http://127.0.0.1")

    def test_non_http_browser_url_is_blocked(self):
        from ollacode.tools import _validate_browser_url
        with self.assertRaises(ValueError):
            _validate_browser_url("file:///etc/passwd")

    def test_private_ipv6_browser_ip_is_blocked(self):
        from ollacode.tools import _validate_browser_url
        with self.assertRaises(ValueError):
            _validate_browser_url("http://[::1]")



if __name__ == "__main__":
    unittest.main()
