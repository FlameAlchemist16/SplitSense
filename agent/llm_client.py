import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

haiku_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL")


def parse_llm_json(raw_text: str):
    text = (raw_text or "").strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Haiku returned invalid JSON: {e}\nRaw response: {raw_text}")
    return parsed[0] if isinstance(parsed, list) else parsed
