# ALVIS V2 / V3

ALVIS is a Windows-first AI agent designed to grow into a JARVIS-style desktop copilot.

## V2 — Windows + Web
- Ukrainian/English text and voice interaction
- In-app API key setup (no `.env` editing required)
- Local encrypted secret storage on Windows via DPAPI
- Web search with structured result URLs
- Read public web pages and extract links
- Screenshot + AI vision of the desktop
- Windows UI Automation: windows, controls, clicks
- Mouse movement/clicks and keyboard shortcuts
- Unicode text input via clipboard paste
- Open Windows applications

## V3 — Developer Agent
- GitHub repository inspection
- GitHub file and issue reading
- Local project/file inspection
- Development/build/test command execution
- Build error capture for iterative debugging
- Multi-step tool loop (up to 16 steps)
- New Chat / context reset
- Safety layer blocks dangerous shell commands

## Configure inside the app
Launch ALVIS and press **⚙ API Keys**. Add:
- OpenAI API key — required for chat and voice
- GitHub token — required for private GitHub API access

Keys are stored locally and are never written to the repository. On Windows, ALVIS uses DPAPI for the stored secret blob.

## Run locally
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alvis
```

For a portable Windows build, use the GitHub Actions **ALVIS-Windows** artifact.
