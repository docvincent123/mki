from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable, Any

from .config import WORKSPACE


class ToolError(RuntimeError):
    pass


def _safe_path(path: str) -> Path:
    p = Path(os.path.expandvars(path)).expanduser().resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents:
        raise ToolError("Path is outside the ALVIS workspace")
    return p


def open_url(url: str) -> str:
    if not url.startswith(("https://", "http://")):
        raise ToolError("Only http(s) URLs are allowed")
    webbrowser.open(url)
    return f"Opened {url}"


def open_app(app: str) -> str:
    allowed = {"notepad": "notepad.exe", "calculator": "calc.exe", "explorer": "explorer.exe", "terminal": "wt.exe"}
    exe = allowed.get(app.lower().strip(), app.strip())
    subprocess.Popen([exe], shell=False)
    return f"Started {exe}"


def read_file(path: str) -> str:
    p = _safe_path(path)
    if not p.exists() or not p.is_file():
        raise ToolError("File does not exist")
    if p.stat().st_size > 2_000_000:
        raise ToolError("File is too large")
    return p.read_text(encoding="utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {p}"


def list_files(path: str = ".") -> str:
    p = _safe_path(path)
    if not p.exists() or not p.is_dir():
        raise ToolError("Directory does not exist")
    rows = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]:
        rows.append(("DIR " if child.is_dir() else "FILE") + child.name)
    return "\n".join(rows) or "(empty)"


def system_info() -> str:
    import platform
    import psutil
    return "\n".join([
        f"OS: {platform.platform()}",
        f"CPU: {platform.processor()}",
        f"RAM: {round(psutil.virtual_memory().total / 1024**3, 1)} GB",
        f"Workspace: {WORKSPACE}",
    ])


def list_windows() -> str:
    from pywinauto import Desktop
    windows = Desktop(backend="uia").windows(visible_only=True)
    rows = []
    for w in windows[:100]:
        title = w.window_text().strip()
        if title:
            rows.append(f"{w.handle}: {title}")
    return "\n".join(rows) or "No visible titled windows"


def inspect_window(title: str) -> str:
    from pywinauto import Desktop
    wins = Desktop(backend="uia").windows(title_re=f".*{title}.*", visible_only=True)
    if not wins:
        raise ToolError(f"Window not found: {title}")
    root = wins[0]
    rows = []
    for c in root.descendants(depth=3)[:250]:
        name = c.window_text().strip()
        if name:
            rows.append(f"{c.control_type()} | {name}")
    return "\n".join(rows) or "No named controls found"


def click_control(title: str, control_text: str) -> str:
    from pywinauto import Desktop
    wins = Desktop(backend="uia").windows(title_re=f".*{title}.*", visible_only=True)
    if not wins:
        raise ToolError(f"Window not found: {title}")
    root = wins[0]
    matches = root.descendants(title=control_text)
    if not matches:
        matches = root.descendants(best_match=control_text)
    if not matches:
        raise ToolError(f"Control not found: {control_text}")
    matches[0].click_input()
    return f"Clicked '{control_text}' in '{title}'"


TOOLS: dict[str, Callable[..., Any]] = {
    "open_url": open_url,
    "open_app": open_app,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "system_info": system_info,
    "list_windows": list_windows,
    "inspect_window": inspect_window,
    "click_control": click_control,
}

SCHEMAS = [
    {"name": "open_url", "description": "Open an http(s) URL in the default browser.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "open_app", "description": "Open a Windows application. Prefer known aliases: notepad, calculator, explorer, terminal.", "parameters": {"type": "object", "properties": {"app": {"type": "string"}}, "required": ["app"]}},
    {"name": "read_file", "description": "Read a UTF-8 text file inside the ALVIS workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write a UTF-8 text file inside the ALVIS workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "list_files", "description": "List files and directories inside the ALVIS workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}, "required": []}},
    {"name": "system_info", "description": "Get basic Windows system information.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "list_windows", "description": "List visible titled Windows application windows and handles.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "inspect_window", "description": "Inspect named controls in a visible Windows application window.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "click_control", "description": "Click a named UI control in a visible Windows application window.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "control_text": {"type": "string"}}, "required": ["title", "control_text"]}},
]
