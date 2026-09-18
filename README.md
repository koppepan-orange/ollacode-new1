# OllaCode

OllaCode is a local AI coding-agent CLI powered by Ollama. It provides an agentic loop with file editing, command execution, code search, Python venv management, web search, and optional Playwright browser control.

## Requirements

- Python 3.10+
- Ollama
- A coding model such as `qwen2.5-coder:7b`

## Windows quick start

```powershell
.\setup.bat
.\ollacode.bat
```

Or run directly:

```powershell
python main.py
```

## Options

```text
ollacode [-h] [-m MODEL] [-u URL] [-d DIR] [-c] [-v] [prompt ...]
```

`-d / --dir` sets the workspace used by filesystem, process, Python-environment, and browser tools.

## Slash commands

- `/help`
- `/models`
- `/model <name>`
- `/tools`
- `/clear`
- `/history`
- `/config`
- `/exit` / `/quit`

## Browser support

Install the optional browser dependency and Chromium when browser automation is needed:

```powershell
pip install playwright
playwright install chromium
```
