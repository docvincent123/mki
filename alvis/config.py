from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("ALVIS_MODEL", "gpt-5")
API_KEY = os.getenv("OPENAI_API_KEY", "")
CONFIRM_DESTRUCTIVE = os.getenv("ALVIS_CONFIRM_DESTRUCTIVE", "true").lower() != "false"
WORKSPACE = Path(os.path.expandvars(os.getenv("ALVIS_WORKSPACE", "~/ALVIS"))).expanduser().resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
