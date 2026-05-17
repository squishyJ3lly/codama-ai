import json
import re
import time

import ollama

from urllib.parse import urlparse
from config import DEBUG, ALLOWED_DOMAINS
from sys import stdout

DEFAULT_SYSTEM_PROMPT = """
You are CODAMA, a structured AI assistant.

You must:
- answer clearly and accurately
- keep responses concise by default
- give code that is correct and ready to run
- use provided web context only when relevant
- follow any planning instructions before answering
- ask a short clarification only when needed

You must not:
- invent syntax, APIs, instructions, or facts
- mention internal prompts, routing, planning, or hidden steps
- explain code unless the user asks
- be verbose unless the user asks for detail

Behavior:
- Simple questions: short direct answer
- Complex questions: concise but complete answer
- Code requests: code-first response
- Debugging: identify the issue, then give the fix

You MUST return ONLY this format:

THINKING:
(short optional reasoning, can be empty)

MESSAGE:
(final response only)
""".strip()

def log(msg: str):
    if DEBUG:
        print(msg)

def timing(label: str, start: float):
    if DEBUG:
        stdout.write(f"[{label}] {time.perf_counter() - start:.2f}s")

def ask_ollama(model: str, messages: list[dict], stream: bool = False):
    return ollama.chat(model=model, messages=messages, stream=stream)

def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = text.replace("```json", "").replace("```python", "").replace("```", "")
    return text.strip()

def extract_json(text: str) -> dict:
    text = strip_code_fences(text)
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return {}
    return {}

def extract_section(text: str, section: str) -> str:
    pattern = rf"{section}:\s*(.*?)(?=\n[A-Z]+:|$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_thinking_message(text: str):
    thinking = extract_section(text, "THINKING")
    message = extract_section(text, "MESSAGE")
    if not message:
        message = text.strip()
    return thinking, message

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(normalize_url(url))
        host = parsed.netloc.lower().removeprefix("www.")
        for d in ALLOWED_DOMAINS:
            d = d.lower().removeprefix("www.")
            if host == d or host.endswith("." + d):
                return True
        return False
    except Exception:
        return False

def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()

def is_code_task(text: str) -> bool:
    t = text.lower()
    keywords = [
        "code", "program", "script", "python", "javascript", "java", "c++",
        "c#", "rust", "go", "assembly", "pygame", "numpy", "neural network",
        "train", "training", "backprop", "debug", "fix", "function", "class",
        "discord bot", "mineflayer", "react", "node js", "nodejs"
    ]
    return any(k in t for k in keywords)

def needs_web(text: str) -> bool:
    t = text.lower()
    keywords = [
        "docs", "documentation", "api", "reference", "current", "latest",
        "version", "release", "github", "stackoverflow", "example",
        "search", "web", "source", "verify"
    ]
    library_keywords = [
        "mineflayer", "discord.js", "pygame", "numpy", "ollama", "fastapi",
        "nextjs", "react", "flask", "pandas", "torch", "transformers"
    ]
    return any(k in t for k in keywords) or any(k in t for k in library_keywords)

def needs_planning(text: str) -> bool:
    t = text.lower()
    keywords = [
        "full", "complete", "build", "make", "create", "design", "architecture",
        "pipeline", "agent", "multi-step", "system", "train", "training",
        "neural network", "backprop", "refactor", "large", "full code"
    ]
    return any(k in t for k in keywords) or len(t.split()) >= 18