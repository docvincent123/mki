from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "ALVIS"
APP_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_FILE = APP_DIR / "secrets.dat"
MODEL = os.getenv("ALVIS_MODEL", "gpt-5")
CONFIRM_DESTRUCTIVE = os.getenv("ALVIS_CONFIRM_DESTRUCTIVE", "true").lower() != "false"
WORKSPACE = Path(os.path.expandvars(os.getenv("ALVIS_WORKSPACE", "~/ALVIS"))).expanduser().resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)


def _protect(value: str) -> bytes:
    """Encrypt a secret with Windows DPAPI when available."""
    raw = value.encode("utf-8")
    try:
        import win32crypt
        return win32crypt.CryptProtectData(raw, "ALVIS", None, None, None, 0)[1]
    except Exception:
        # Fallback is only for non-Windows/dev environments; permissions protect the file.
        return base64.b64encode(raw)


def _unprotect(value: bytes) -> str:
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(value, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        return base64.b64decode(value).decode("utf-8")


def save_secret(name: str, value: str) -> None:
    secrets = load_secrets()
    if value.strip():
        secrets[name] = value.strip()
    else:
        secrets.pop(name, None)
    lines = []
    for key, secret in sorted(secrets.items()):
        token = base64.b64encode(_protect(secret)).decode("ascii")
        lines.append(f"{key}={token}")
    SECRETS_FILE.write_text("\n".join(lines), encoding="utf-8")
    try:
        os.chmod(SECRETS_FILE, 0o600)
    except Exception:
        pass


def load_secrets() -> dict[str, str]:
    if not SECRETS_FILE.exists():
        return {}
    result: dict[str, str] = {}
    for line in SECRETS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, token = line.split("=", 1)
        try:
            result[key] = _unprotect(base64.b64decode(token)).strip()
        except Exception:
            continue
    return result


def get_secret(name: str, env_name: str | None = None) -> str:
    stored = load_secrets().get(name, "")
    if stored:
        return stored
    return os.getenv(env_name or name, "")


def get_openai_key() -> str:
    return get_secret("OPENAI_API_KEY", "OPENAI_API_KEY")


def get_github_token() -> str:
    return get_secret("GITHUB_TOKEN", "GITHUB_TOKEN")


def has_openai_key() -> bool:
    return bool(get_openai_key())
