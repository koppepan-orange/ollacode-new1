"""Cross-platform coding, file, web, browser, and Python environment tools."""
from __future__ import annotations

import fnmatch
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/", r"\bformat\s+[a-zA-Z]:", r"\bdel\s+/[sS]\s+/[qQ]\s+",
    r"\brd\s+/[sS]\s+/", r">\s*/dev/sd[a-z]", r":\(\)\{.*\}", r"mkfs\.", r"dd\s+if=.*of=/dev/",
]

def _is_dangerous(command: str) -> bool:
    return any(re.search(pattern, command) for pattern in DANGEROUS_PATTERNS)

def get_venv_python_path(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

def get_venv_pip_path(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/pip.exe" if platform.system() == "Windows" else "bin/pip")

def _resolve_path(path: str, cwd: str | None = None) -> Path:
    p = Path(path)
    return Path(cwd) / p if cwd and not p.is_absolute() else p

def _decode_file(p: Path) -> tuple[str, str, bytes]:
    import chardet
    raw = p.read_bytes()
    encoding = chardet.detect(raw).get("encoding") or "utf-8"
    try:
        return raw.decode(encoding), encoding, raw
    except (UnicodeDecodeError, LookupError):
        return raw.decode("utf-8", errors="replace"), "utf-8", raw

def tool_read_file(path: str, start_line: int = 1, end_line: int | None = None, cwd: str | None = None) -> dict[str, Any]:
    try:
        p = _resolve_path(path, cwd)
        if not p.exists(): return {"error": f"File not found: {path}"}
        if not p.is_file(): return {"error": f"Not a file: {path}"}
        text, _, _ = _decode_file(p)
        lines = text.splitlines()
        end = end_line if end_line is not None else len(lines)
        numbered = "\n".join(f"{start_line + i:4d}: {line}" for i, line in enumerate(lines[start_line - 1:end]))
        return {"path": str(p.resolve()), "total_lines": len(lines), "shown_lines": f"{start_line}-{end}", "content": numbered}
    except Exception as e: return {"error": str(e)}

def tool_write_file(path: str, content: str, encoding: str = "utf-8", cwd: str | None = None) -> dict[str, Any]:
    try:
        p = _resolve_path(path, cwd); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding, newline="\n")
        return {"success": True, "path": str(p.resolve()), "bytes_written": len(content.encode(encoding))}
    except Exception as e: return {"error": str(e)}

def tool_edit_file(path: str, old_text: str, new_text: str, cwd: str | None = None) -> dict[str, Any]:
    try:
        p = _resolve_path(path, cwd)
        if not p.exists(): return {"error": f"File not found: {path}"}
        original, encoding, raw = _decode_file(p)
        if old_text not in original: return {"error": "old_text not found in file. Use read_file first to verify exact content."}
        count = original.count(old_text)
        if count > 1: return {"error": f"old_text found {count} times. Please provide more context to make it unique."}
        updated = original.replace(old_text, new_text, 1)
        newline = "\r\n" if b"\r\n" in raw and b"\n" in raw else "\n"
        p.write_text(updated, encoding=encoding, newline=newline)
        return {"success": True, "path": str(p.resolve()), "lines_changed": len(new_text.splitlines()) - len(old_text.splitlines())}
    except Exception as e: return {"error": str(e)}

def tool_run_command(command: str, cwd: str | None = None, timeout: int = 120, confirm: bool = False) -> dict[str, Any]:
    if _is_dangerous(command): return {"error": f"Command blocked as potentially dangerous: {command}"}
    if confirm:
        print(f"\n[CONFIRM] About to run: {command}")
        if input("Proceed? [y/N] ").strip().lower() != "y": return {"cancelled": True, "command": command}
    try:
        kwargs = {"shell": True, "capture_output": True, "text": True, "timeout": timeout, "encoding": "utf-8", "errors": "replace"}
        if cwd: kwargs["cwd"] = cwd
        if platform.system() == "Windows": kwargs["env"] = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(command, **kwargs)
        return {"returncode": result.returncode, "stdout": result.stdout[-4000:], "stderr": result.stderr[-2000:], "command": command}
    except subprocess.TimeoutExpired: return {"error": f"Command timed out after {timeout}s", "command": command}
    except Exception as e: return {"error": str(e), "command": command}

def tool_list_dir(path: str = ".", cwd: str | None = None) -> dict[str, Any]:
    try:
        p = _resolve_path(path, cwd)
        if not p.exists(): return {"error": f"Path not found: {path}"}
        if not p.is_dir(): return {"error": f"Not a directory: {path}"}
        entries = []
        for item in sorted(p.iterdir()):
            entry = {"name": item.name, "type": "dir" if item.is_dir() else "file"}
            if item.is_file(): entry["size"] = item.stat().st_size
            entries.append(entry)
        return {"path": str(p.resolve()), "entries": entries}
    except Exception as e: return {"error": str(e)}

def tool_file_tree(path: str = ".", max_depth: int = 4, exclude: list[str] | None = None, cwd: str | None = None) -> dict[str, Any]:
    exclude = exclude or [".git", "__pycache__", ".venv", "node_modules", ".mypy_cache", "dist", "*.egg-info"]
    def skip(name): return any(fnmatch.fnmatch(name, x) for x in exclude)
    def tree(d: Path, prefix="", depth=0):
        if depth >= max_depth: return [f"{prefix}..."]
        try: children = [x for x in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())) if not skip(x.name)]
        except PermissionError: return [f"{prefix}[Permission Denied]"]
        out=[]
        for i, child in enumerate(children):
            last=i==len(children)-1; out.append(prefix + ("└── " if last else "├── ") + child.name)
            if child.is_dir(): out += tree(child, prefix + ("    " if last else "│   "), depth+1)
        return out
    try:
        root=_resolve_path(path,cwd); return {"tree":"\n".join([str(root.resolve())]+tree(root))}
    except Exception as e: return {"error":str(e)}

def tool_grep_search(pattern: str, path: str = ".", case_sensitive: bool = True, file_pattern: str | None = None, max_results: int = 50, cwd: str | None = None) -> dict[str, Any]:
    try:
        root=_resolve_path(path,cwd); compiled=re.compile(pattern, 0 if case_sensitive else re.IGNORECASE); results=[]
        files=[root] if root.is_file() else root.rglob("*")
        for fp in sorted(files) if not root.is_file() else files:
            if len(results)>=max_results: break
            if not fp.is_file() or any(part.startswith(".") or part in ("__pycache__","node_modules",".venv") for part in fp.parts): continue
            if file_pattern and not fnmatch.fnmatch(fp.name,file_pattern): continue
            try: text,_,_= _decode_file(fp)
            except Exception: continue
            for i,line in enumerate(text.splitlines(),1):
                if len(results)>=max_results: break
                if compiled.search(line): results.append({"file":str(fp),"line":i,"content":line.rstrip()})
        return {"matches":results,"total":len(results),"pattern":pattern}
    except re.error as e: return {"error":f"Invalid regex: {e}"}
    except Exception as e: return {"error":str(e)}

def tool_python_env(action: str, venv_path: str | None = None, packages: list[str] | None = None, script: str | None = None, cwd: str | None = None) -> dict[str, Any]:
    work_dir=Path(cwd or "."); venv_dir=_resolve_path(venv_path,str(work_dir)) if venv_path else work_dir/".venv"; py=get_venv_python_path(venv_dir); pip=get_venv_pip_path(venv_dir)
    def run(cmd):
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=300,cwd=str(work_dir)); return {"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
        except subprocess.TimeoutExpired:return {"error":"Timed out"}
        except Exception as e:return {"error":str(e)}
    if action=="create":
        if venv_dir.exists() and py.exists(): return {"success":True,"message":f"venv already exists at {venv_dir}","python":str(py)}
        r=run([sys.executable,"-m","venv",str(venv_dir)]); return {"success":r.get("returncode")==0,"message":f"Created venv at {venv_dir}","python":str(py),**r} if r.get("returncode")==0 else {"error":f"Failed to create venv: {r.get('stderr','')}",**r}
    if not py.exists(): return {"error":f"venv not found at {venv_dir}. Run action='create' first."}
    if action=="info":
        r=run([str(py),"--version"]); p=run([str(pip),"list","--format=columns"]); return {"venv_path":str(venv_dir.resolve()),"python_exe":str(py),"python_version":r.get("stdout","").strip(),"installed_packages":p.get("stdout","")}
    if action=="install":
        if not packages:return {"error":"packages list is required for action='install'"}
        r=run([str(pip),"install"]+packages); return {"success":r.get("returncode")==0,"packages":packages,**r}
    if action=="run":
        if not script:return {"error":"script is required for action='run'"}
        return {"script":script,**run([str(py),script])}
    if action=="run_module":
        if not script:return {"error":"module name is required for action='run_module'"}
        return {"module":script,**run([str(py),"-m"]+script.split())}
    return {"error":f"Unknown action '{action}'. Use: create, info, install, run, run_module"}

def tool_web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    try:
        from duckduckgo_search import DDGS
        results=[]
        with DDGS() as ddgs:
            for r in ddgs.text(query,max_results=max_results): results.append({"title":r.get("title",""),"url":r.get("href",""),"snippet":r.get("body","")[:500]})
        return {"query":query,"results":results,"summary":"\n\n".join(f"**{r['title']}**\n{r['url']}\n{r['snippet']}" for r in results)}
    except Exception as e:return {"error":str(e),"query":query}

def tool_browser_control(action: str = "", url: str | None = None, selector: str | None = None, text: str | None = None, script: str | None = None, screenshot_path: str | None = None, headless: bool = True, steps: list[dict] | None = None, cwd: str | None = None) -> dict[str, Any]:
    try: from playwright.sync_api import sync_playwright
    except ImportError:return {"error":"Playwright is not installed. Run: pip install playwright && playwright install","action":action}
    shot=_resolve_path(screenshot_path,cwd) if screenshot_path else None
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=headless); page=browser.new_page()
            def do(a):
                act=a.get("action",""); u=a.get("url"); sel=a.get("selector"); val=a.get("text"); js=a.get("script")
                if act=="goto": page.goto(u,wait_until="domcontentloaded")
                elif act=="click": page.click(sel)
                elif act=="fill": page.fill(sel,val or "")
                elif act=="screenshot":
                    path=_resolve_path(a.get("screenshot_path") or "screenshot.png",cwd); path.parent.mkdir(parents=True,exist_ok=True); page.screenshot(path=str(path))
                elif act=="evaluate": return page.evaluate(js or "")
                elif act=="get_text": return page.locator(sel).inner_text() if sel else page.locator("body").inner_text()
                elif act=="close": browser.close()
                else: raise ValueError(f"Unknown browser action: {act}")
            if steps:
                result=[do(s) for s in steps]
            else:
                result=do({"action":action,"url":url,"selector":selector,"text":text,"script":script,"screenshot_path":str(shot) if shot else None})
            if action=="close": return {"success":True}
            return {"success":True,"result":result,"url":page.url}
    except Exception as e:return {"error":str(e),"action":action}

TOOLS={"read_file":tool_read_file,"write_file":tool_write_file,"edit_file":tool_edit_file,"run_command":tool_run_command,"list_dir":tool_list_dir,"file_tree":tool_file_tree,"grep_search":tool_grep_search,"python_env":tool_python_env,"web_search":tool_web_search,"browser_control":tool_browser_control}

def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {"type":"function","function":{"name":"read_file","description":"Read file contents with line numbers.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer","default":1},"end_line":{"type":"integer"},"cwd":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Create or overwrite a file.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"encoding":{"type":"string","default":"utf-8"},"cwd":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"edit_file","description":"Replace an exact string in a file. Use read_file first.","parameters":{"type":"object","properties":{"path":{"type":"string"},"old_text":{"type":"string"},"new_text":{"type":"string"},"cwd":{"type":"string"}},"required":["path","old_text","new_text"]}}},
        {"type":"function","function":{"name":"run_command","description":"Execute a shell command. Dangerous commands are blocked.","parameters":{"type":"object","properties":{"command":{"type":"string"},"cwd":{"type":"string"},"timeout":{"type":"integer","default":120}},"required":["command"]}}},
        {"type":"function","function":{"name":"list_dir","description":"List directory contents.","parameters":{"type":"object","properties":{"path":{"type":"string","default":"."},"cwd":{"type":"string"}}}}},
        {"type":"function","function":{"name":"file_tree","description":"Show project structure as a tree.","parameters":{"type":"object","properties":{"path":{"type":"string","default":"."},"max_depth":{"type":"integer","default":4},"exclude":{"type":"array","items":{"type":"string"}},"cwd":{"type":"string"}}}}},
        {"type":"function","function":{"name":"grep_search","description":"Search for a regex pattern within files.","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string","default":"."},"case_sensitive":{"type":"boolean","default":True},"file_pattern":{"type":"string"},"max_results":{"type":"integer","default":50},"cwd":{"type":"string"}},"required":["pattern"]}}},
        {"type":"function","function":{"name":"python_env","description":"Manage Python virtual environments.","parameters":{"type":"object","properties":{"action":{"type":"string","enum":["create","info","install","run","run_module"]},"venv_path":{"type":"string"},"packages":{"type":"array","items":{"type":"string"}},"script":{"type":"string"},"cwd":{"type":"string"}},"required":["action"]}}},
        {"type":"function","function":{"name":"web_search","description":"Search the web via DuckDuckGo.","parameters":{"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer","default":5}},"required":["query"]}}},
        {"type":"function","function":{"name":"browser_control","description":"Control a browser using Playwright.","parameters":{"type":"object","properties":{"action":{"type":"string","enum":["goto","click","fill","screenshot","evaluate","get_text","close"]},"url":{"type":"string"},"selector":{"type":"string"},"text":{"type":"string"},"script":{"type":"string"},"screenshot_path":{"type":"string"},"headless":{"type":"boolean","default":True},"steps":{"type":"array","items":{"type":"object","properties":{"action":{"type":"string"},"url":{"type":"string"},"selector":{"type":"string"},"text":{"type":"string"},"script":{"type":"string"},"screenshot_path":{"type":"string"}},"required":["action"]}},"cwd":{"type":"string"}}}}},
    ]

def execute_tool(name: str, args: dict[str, Any]) -> Any:
    if name not in TOOLS:return {"error":f"Unknown tool: {name}"}
    return TOOLS[name](**args)
