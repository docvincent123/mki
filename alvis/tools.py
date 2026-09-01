from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable, Any
from urllib.request import Request, urlopen

from .config import WORKSPACE, get_github_token, get_openai_key, MODEL
from .web import search_web, fetch_url, extract_links

class ToolError(RuntimeError):
    pass


def _safe_path(path: str) -> Path:
    p = Path(os.path.expandvars(path)).expanduser().resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents: raise ToolError("Path is outside the ALVIS workspace")
    return p


def open_url(url: str) -> str:
    if not url.startswith(("https://", "http://")): raise ToolError("Only http(s) URLs are allowed")
    webbrowser.open(url); return f"Opened {url}"


def open_app(app: str) -> str:
    allowed={"notepad":"notepad.exe","calculator":"calc.exe","explorer":"explorer.exe","terminal":"wt.exe"}
    exe=allowed.get(app.lower().strip(),app.strip())
    if not exe: raise ToolError("Application name is empty")
    subprocess.Popen([exe], shell=False); return f"Started {exe}"


def read_file(path: str) -> str:
    p=_safe_path(path)
    if not p.exists() or not p.is_file(): raise ToolError("File does not exist")
    if p.stat().st_size>4_000_000: raise ToolError("File is too large")
    return p.read_text(encoding="utf-8",errors="replace")


def write_file(path: str, content: str) -> str:
    p=_safe_path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8"); return f"Wrote {p}"


def list_files(path: str = ".") -> str:
    p=_safe_path(path)
    if not p.exists() or not p.is_dir(): raise ToolError("Directory does not exist")
    return "\n".join(("DIR " if c.is_dir() else "FILE ")+c.name for c in sorted(p.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower()))[:300]) or "(empty)"


def system_info() -> str:
    import platform, psutil
    return f"OS: {platform.platform()}\nCPU: {platform.processor()}\nRAM: {round(psutil.virtual_memory().total/1024**3,1)} GB\nWorkspace: {WORKSPACE}"


def list_windows() -> str:
    from pywinauto import Desktop
    return "\n".join(f"{w.handle}: {w.window_text().strip()}" for w in Desktop(backend="uia").windows(visible_only=True) if w.window_text().strip())[:16000]


def inspect_window(title: str) -> str:
    from pywinauto import Desktop
    wins=Desktop(backend="uia").windows(title_re=f".*{re.escape(title)}.*",visible_only=True)
    if not wins: raise ToolError(f"Window not found: {title}")
    return "\n".join(f"{c.control_type()} | {c.window_text().strip()}" for c in wins[0].descendants(depth=4)[:400] if c.window_text().strip())


def click_control(title: str, control_text: str) -> str:
    from pywinauto import Desktop
    wins=Desktop(backend="uia").windows(title_re=f".*{re.escape(title)}.*",visible_only=True)
    if not wins: raise ToolError(f"Window not found: {title}")
    matches=wins[0].descendants(title=control_text) or wins[0].descendants(best_match=control_text)
    if not matches: raise ToolError(f"Control not found: {control_text}")
    matches[0].click_input(); return f"Clicked '{control_text}' in '{title}'"


def screenshot(path: str = "screen.png") -> str:
    p=_safe_path(path); import pyautogui
    p.parent.mkdir(parents=True,exist_ok=True); pyautogui.screenshot(str(p)); return f"Screenshot saved to {p}"


def vision_screenshot(path: str = "screen.png", prompt: str = "Describe the visible screen and important UI controls.") -> str:
    p=_safe_path(path)
    if not p.exists(): screenshot(path)
    key=get_openai_key()
    if not key: raise ToolError("OPENAI_API_KEY is not configured")
    from openai import OpenAI
    data=base64.b64encode(p.read_bytes()).decode("ascii")
    client=OpenAI(api_key=key)
    response=client.chat.completions.create(model=MODEL,messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/png;base64,{data}"}}]}])
    return response.choices[0].message.content or "No visual description returned."


def mouse_move(x: int, y: int) -> str:
    import pyautogui; pyautogui.moveTo(x,y,duration=0.15); return f"Mouse moved to ({x}, {y})"


def mouse_click(x: int, y: int, button: str = "left") -> str:
    if button not in {"left","right","middle"}: raise ToolError("Invalid mouse button")
    import pyautogui; pyautogui.click(x=x,y=y,button=button); return f"Clicked {button} at ({x}, {y})"


def type_text(text: str, interval: float = 0.01) -> str:
    # Clipboard paste preserves Ukrainian and other Unicode text.
    import pyperclip, pyautogui
    pyperclip.copy(text); pyautogui.hotkey("ctrl","v"); return "Pasted text into the focused control"


def hotkey(keys: str) -> str:
    import pyautogui
    parts=[k.strip().lower() for k in keys.split("+") if k.strip()]
    if not parts: raise ToolError("No hotkey specified")
    pyautogui.hotkey(*parts); return f"Pressed {'+'.join(parts)}"


def run_command(command: str, cwd: str = ".") -> str:
    dangerous=re.compile(r"(del\s|rm\s|rmdir|format\s|shutdown|restart-computer|remove-item|git\s+reset\s+--hard|git\s+push\s+--force|\btaskkill\b)",re.I)
    if dangerous.search(command): return "NEEDS_CONFIRMATION: potentially destructive command blocked. Ask the user to confirm before running it."
    p=_safe_path(cwd)
    if not p.is_dir(): raise ToolError("Working directory does not exist")
    completed=subprocess.run(command,cwd=str(p),shell=True,capture_output=True,text=True,timeout=180)
    output=(completed.stdout or "")+("\n"+completed.stderr if completed.stderr else "")
    return f"exit_code={completed.returncode}\n{output[-50000:]}"


def _github_request(path: str) -> dict | list:
    token=get_github_token()
    if not token: raise ToolError("GITHUB_TOKEN is not configured. Add it in ALVIS Settings.")
    req=Request("https://api.github.com"+path,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","User-Agent":"ALVIS"})
    with urlopen(req,timeout=20) as response: return json.loads(response.read().decode("utf-8"))


def github_repo(repo: str) -> str:
    data=_github_request(f"/repos/{repo.strip()}")
    return json.dumps({k:data.get(k) for k in ("full_name","description","default_branch","html_url","language","stargazers_count","open_issues_count")},ensure_ascii=False,indent=2)


def github_file(repo: str, path: str, ref: str = "") -> str:
    suffix=f"?ref={ref}" if ref else ""; data=_github_request(f"/repos/{repo.strip()}/contents/{path.lstrip('/')}{suffix}")
    if isinstance(data,list): return json.dumps(data[:100],ensure_ascii=False,indent=2)
    return base64.b64decode(data["content"]).decode("utf-8",errors="replace")


def github_issues(repo: str, state: str = "open") -> str:
    data=_github_request(f"/repos/{repo.strip()}/issues?state={state}&per_page=30")
    return "\n".join(f"#{x['number']} {x['title']} — {x['html_url']}" for x in data if "pull_request" not in x)

TOOLS: dict[str,Callable[...,Any]]={
    "open_url":open_url,"open_app":open_app,"read_file":read_file,"write_file":write_file,"list_files":list_files,
    "system_info":system_info,"list_windows":list_windows,"inspect_window":inspect_window,"click_control":click_control,
    "screenshot":screenshot,"vision_screenshot":vision_screenshot,"mouse_move":mouse_move,"mouse_click":mouse_click,
    "type_text":type_text,"hotkey":hotkey,"run_command":run_command,"search_web":search_web,"fetch_url":fetch_url,
    "extract_links":extract_links,"github_repo":github_repo,"github_file":github_file,"github_issues":github_issues,
}


def _schema(name:str,description:str,properties:dict,required:list[str]|None=None)->dict:
    return {"name":name,"description":description,"parameters":{"type":"object","properties":properties,"required":required or []}}

SCHEMAS=[
_schema("open_url","Open an http(s) URL in the default browser.",{"url":{"type":"string"}},["url"]),
_schema("open_app","Open a Windows application.",{"app":{"type":"string"}},["app"]),
_schema("read_file","Read a UTF-8 text file inside ALVIS workspace.",{"path":{"type":"string"}},["path"]),
_schema("write_file","Write a UTF-8 text file inside ALVIS workspace.",{"path":{"type":"string"},"content":{"type":"string"}},["path","content"]),
_schema("list_files","List workspace files.",{"path":{"type":"string"}}),_schema("system_info","Get Windows system information.",{}),
_schema("list_windows","List visible Windows application windows.",{}),_schema("inspect_window","Inspect visible Windows UI controls.",{"title":{"type":"string"}},["title"]),
_schema("click_control","Click a named visible Windows control.",{"title":{"type":"string"},"control_text":{"type":"string"}},["title","control_text"]),
_schema("screenshot","Take a screenshot of the desktop.",{"path":{"type":"string"}}),
_schema("vision_screenshot","Take/read a screenshot with vision and describe UI, errors, or content.",{"path":{"type":"string"},"prompt":{"type":"string"}}),
_schema("mouse_move","Move the mouse cursor to screen coordinates.",{"x":{"type":"integer"},"y":{"type":"integer"}},["x","y"]),
_schema("mouse_click","Click the mouse at screen coordinates.",{"x":{"type":"integer"},"y":{"type":"integer"},"button":{"type":"string"}},["x","y"]),
_schema("type_text","Paste Unicode text into the focused Windows control.",{"text":{"type":"string"}},["text"]),
_schema("hotkey","Press a keyboard shortcut such as ctrl+l.",{"keys":{"type":"string"}},["keys"]),
_schema("run_command","Run a development/build command in the ALVIS workspace; destructive commands are blocked.",{"command":{"type":"string"},"cwd":{"type":"string"}},["command"]),
_schema("search_web","Search the public web for current information.",{"query":{"type":"string"},"max_results":{"type":"integer"}},["query"]),
_schema("fetch_url","Read a public web page.",{"url":{"type":"string"}},["url"]),_schema("extract_links","Extract links from a public web page.",{"url":{"type":"string"}},["url"]),
_schema("github_repo","Inspect a GitHub repository.",{"repo":{"type":"string"}},["repo"]),_schema("github_file","Read a file from a GitHub repository.",{"repo":{"type":"string"},"path":{"type":"string"},"ref":{"type":"string"}},["repo","path"]),
_schema("github_issues","List GitHub repository issues.",{"repo":{"type":"string"},"state":{"type":"string"}},["repo"]),
]
