from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable, Any

from .config import WORKSPACE
from .web import search_web, fetch_url, extract_links

class ToolError(RuntimeError): pass

def _safe_path(path: str) -> Path:
    p = Path(os.path.expandvars(path)).expanduser().resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents: raise ToolError("Path is outside the ALVIS workspace")
    return p

def open_url(url: str) -> str:
    if not url.startswith(("https://", "http://")): raise ToolError("Only http(s) URLs are allowed")
    webbrowser.open(url); return f"Opened {url}"

def open_app(app: str) -> str:
    allowed={"notepad":"notepad.exe","calculator":"calc.exe","explorer":"explorer.exe","terminal":"wt.exe"}
    exe=allowed.get(app.lower().strip(),app.strip()); subprocess.Popen([exe],shell=False); return f"Started {exe}"

def read_file(path: str) -> str:
    p=_safe_path(path)
    if not p.exists() or not p.is_file(): raise ToolError("File does not exist")
    if p.stat().st_size>2_000_000: raise ToolError("File is too large")
    return p.read_text(encoding="utf-8",errors="replace")

def write_file(path: str, content: str) -> str:
    p=_safe_path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8"); return f"Wrote {p}"

def list_files(path: str = ".") -> str:
    p=_safe_path(path)
    if not p.exists() or not p.is_dir(): raise ToolError("Directory does not exist")
    return "\n".join(("DIR " if c.is_dir() else "FILE ")+c.name for c in sorted(p.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower()))[:200]) or "(empty)"

def system_info() -> str:
    import platform, psutil
    return f"OS: {platform.platform()}\nCPU: {platform.processor()}\nRAM: {round(psutil.virtual_memory().total/1024**3,1)} GB\nWorkspace: {WORKSPACE}"

def list_windows() -> str:
    from pywinauto import Desktop
    return "\n".join(f"{w.handle}: {w.window_text().strip()}" for w in Desktop(backend="uia").windows(visible_only=True) if w.window_text().strip())[:12000]

def inspect_window(title: str) -> str:
    from pywinauto import Desktop
    wins=Desktop(backend="uia").windows(title_re=f".*{title}.*",visible_only=True)
    if not wins: raise ToolError(f"Window not found: {title}")
    return "\n".join(f"{c.control_type()} | {c.window_text().strip()}" for c in wins[0].descendants(depth=3)[:250] if c.window_text().strip())

def click_control(title: str, control_text: str) -> str:
    from pywinauto import Desktop
    wins=Desktop(backend="uia").windows(title_re=f".*{title}.*",visible_only=True)
    if not wins: raise ToolError(f"Window not found: {title}")
    root=wins[0]; matches=root.descendants(title=control_text) or root.descendants(best_match=control_text)
    if not matches: raise ToolError(f"Control not found: {control_text}")
    matches[0].click_input(); return f"Clicked '{control_text}' in '{title}'"

TOOLS: dict[str, Callable[..., Any]]={
    "open_url":open_url,"open_app":open_app,"read_file":read_file,"write_file":write_file,
    "list_files":list_files,"system_info":system_info,"list_windows":list_windows,"inspect_window":inspect_window,
    "click_control":click_control,"search_web":search_web,"fetch_url":fetch_url,"extract_links":extract_links,
}

SCHEMAS=[
{"name":"open_url","description":"Open an http(s) URL in the default browser.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
{"name":"open_app","description":"Open a Windows application.","parameters":{"type":"object","properties":{"app":{"type":"string"}},"required":["app"]}},
{"name":"read_file","description":"Read a UTF-8 text file inside ALVIS workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
{"name":"write_file","description":"Write a UTF-8 text file inside ALVIS workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
{"name":"list_files","description":"List workspace files.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":[]}},
{"name":"system_info","description":"Get Windows system information.","parameters":{"type":"object","properties":{},"required":[]}},
{"name":"list_windows","description":"List visible Windows application windows.","parameters":{"type":"object","properties":{},"required":[]}},
{"name":"inspect_window","description":"Inspect controls in a visible Windows window.","parameters":{"type":"object","properties":{"title":{"type":"string"}},"required":["title"]}},
{"name":"click_control","description":"Click a named control in a visible Windows window.","parameters":{"type":"object","properties":{"title":{"type":"string"},"control_text":{"type":"string"}},"required":["title","control_text"]}},
{"name":"search_web","description":"Search the public web for current information. Use this whenever the user asks to search, research, compare current information, or find sources.","parameters":{"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer"}},"required":["query"]}},
{"name":"fetch_url","description":"Read the text of a public web page or text endpoint.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
{"name":"extract_links","description":"Extract useful links from a public web page.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
]
