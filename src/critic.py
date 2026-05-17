from config import MODELS
from utils import ask_ollama, extract_section, log

CRITIC_PROMPT = """
You are CODAMA Critic.

Analyze the provided code.

Check for:
- hallucinated APIs
- invalid syntax
- fake methods
- missing imports
- incompatible libraries
- obvious logic bugs

Return ONLY this format:

THINKING:
(short reasoning)

MESSAGE:
(corrected code OR CODE_OK)
""".strip()

def critic_review(code_text: str) -> str:
    critic_messages = [
        {"role": "system", "content": CRITIC_PROMPT},
        {"role": "user", "content": code_text},
    ]

    try:
        result = ask_ollama(MODELS["critic"], critic_messages, stream=False)
        return result["message"]["content"] # type: ignore
    except Exception as e:
        log(f"[CRITIC] error: {e}")
        return "MESSAGE:\nCODE_OK"