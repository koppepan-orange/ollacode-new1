import tempfile
import unittest
from pathlib import Path

from ollacode.agent import Agent
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


if __name__ == "__main__":
    unittest.main()
