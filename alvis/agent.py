from __future__ import annotations

import json
from openai import OpenAI

from .config import API_KEY, MODEL
from .tools import TOOLS, SCHEMAS, ToolError

SYSTEM = """You are ALVIS, a concise Ukrainian/English Windows desktop assistant.
You can use tools to act on the user's computer. Explain what you are doing briefly.
Never claim an action happened unless the tool returned success. Ask for confirmation before
any future tool that can delete data, install software, change security settings, send messages,
or perform other irreversible external actions.
"""

CHAT_TOOLS = [{"type": "function", "function": s} for s in SCHEMAS]


class Agent:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=API_KEY) if API_KEY else None
        self.messages = [{"role": "system", "content": SYSTEM}]

    def ask(self, text: str) -> str:
        if not self.client:
            return "API ключ не налаштований. Додай OPENAI_API_KEY у .env."
        self.messages.append({"role": "user", "content": text})
        for _ in range(8):
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=CHAT_TOOLS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            self.messages.append(msg)
            if not msg.tool_calls:
                return msg.content or "Готово."
            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = TOOLS[name](**args)
                except (ToolError, Exception) as exc:
                    result = f"Tool error: {exc}"
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                })
        return "Я виконав кілька кроків, але досяг ліміту циклу виконання."
