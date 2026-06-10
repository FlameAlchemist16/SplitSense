import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

haiku_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL")