# ALVIS

ALVIS is a Windows-first AI assistant designed to grow into a JARVIS-style desktop agent.

## V1
- Ukrainian/English text commands
- Open applications and URLs
- Run safe shell commands with confirmation
- Read/write text files inside allowed workspaces
- AI tool calling through OpenAI-compatible API
- PySide6 desktop UI
- Modular tools architecture
- GitHub Actions Windows build

## Run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Put your API key into .env
python -m alvis
```

The first release deliberately keeps destructive operations behind confirmation. Windows UI Automation will be added as the next agent layer; Microsoft documents UI Automation as a programmatic interface for inspecting and manipulating most desktop UI elements.
