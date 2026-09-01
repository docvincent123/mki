from __future__ import annotations

import json
from openai import OpenAI
from .config import MODEL, get_openai_key
from .tools import TOOLS, SCHEMAS

SYSTEM = """You are ALVIS, a proactive Ukrainian/English Windows AI copilot.
Talk naturally and concisely, but be capable of multi-step work. You can research the web,
read pages, inspect and control Windows, use keyboard/mouse, run development commands, inspect
GitHub repositories and files, and help debug/build projects.

For current facts, news, prices, products, documentation, libraries, or anything that may have
changed, search the web first. For research, prefer several independent sources and return useful
source URLs. When working on code, inspect the project before changing it, explain the plan briefly,
make small verifiable changes, run tests/builds when possible, inspect errors, and iterate.
Use screenshots/UI inspection before coordinate-based actions when possible.
Never claim an action happened unless the tool returned success. Never expose API keys or tokens.
Potentially destructive commands are blocked by the local safety layer; do not try to bypass it.
If a tool says NEEDS_CONFIRMATION, tell the user exactly what would be run and ask for confirmation.
"""

CHAT_TOOLS = [{"type": "function", "function": s} for s in SCHEMAS]


class Agent:
    def __init__(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM}]
        self.client: OpenAI | None = None
        self.refresh_credentials()

    def refresh_credentials(self) -> None:
        key = get_openai_key()
        self.client = OpenAI(api_key=key) if key else None

    def clear_context(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM}]

    def ask(self, text: str) -> str:
        self.refresh_credentials()
        if not self.client:
            return "[OPENAI_ERROR] OPENAI_API_KEY is not configured. Відкрий Налаштування → API Keys і додай OpenAI API key."
        self.messages.append({"role": "user", "content": text})
        for _ in range(16):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=CHAT_TOOLS,
                    tool_choice="auto",
                )
            except Exception as exc:
                return f"[OPENAI_ERROR] {exc}"
            msg = response.choices[0].message
            self.messages.append(msg)
            if not msg.tool_calls:
                return msg.content or "Готово."
            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = TOOLS[name](**args)
                except Exception as exc:
                    result = f"Tool error: {exc}"
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)[:60000]})
        return "Я виконав багато кроків, але зупинився на ліміті. Можу продовжити з поточного стану."
