from __future__ import annotations

import json
from openai import OpenAI
from .config import API_KEY, MODEL
from .tools import TOOLS, SCHEMAS, ToolError

SYSTEM="""You are ALVIS, a proactive Ukrainian/English Windows AI copilot.
Be conversational: discuss ideas with the user, explain tradeoffs, suggest better approaches,
and say when you disagree. For current facts, news, products, documentation, prices, libraries,
or anything that may have changed, SEARCH THE WEB FIRST. When researching, use multiple searches
when useful, inspect relevant pages, synthesize the findings, and mention sources/URLs in your answer.
You can operate Windows through tools. Before destructive, irreversible, financial, security,
message-sending, installation, or bulk-edit actions, ask the user for confirmation.
Never claim an action happened unless the tool returned success. Do not expose secrets.
"""

CHAT_TOOLS=[{"type":"function","function":s} for s in SCHEMAS]

class Agent:
    def __init__(self)->None:
        self.client=OpenAI(api_key=API_KEY) if API_KEY else None
        self.messages=[{"role":"system","content":SYSTEM}]

    def ask(self,text:str)->str:
        if not self.client: return "API ключ не налаштований. Додай OPENAI_API_KEY у .env."
        self.messages.append({"role":"user","content":text})
        for _ in range(12):
            response=self.client.chat.completions.create(model=MODEL,messages=self.messages,tools=CHAT_TOOLS,tool_choice="auto")
            msg=response.choices[0].message
            self.messages.append(msg)
            if not msg.tool_calls: return msg.content or "Готово."
            for call in msg.tool_calls:
                name=call.function.name
                try:
                    args=json.loads(call.function.arguments or "{}")
                    result=TOOLS[name](**args)
                except Exception as exc:
                    result=f"Tool error: {exc}"
                self.messages.append({"role":"tool","tool_call_id":call.id,"content":str(result)[:60000]})
        return "Я виконав багато кроків, але зупинився на ліміті виконання."
