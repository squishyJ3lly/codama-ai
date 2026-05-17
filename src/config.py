MODELS = {
    "router": "llama3.2:3b",
    "planner": "llama3.1:8b",
    "fast": "llama3.2:3b",
    "deep": "llama3.1:8b",
    "code": "qwen2.5-coder:7b",
    "critic": "deepseek-coder:6.7b",
}

ALLOWED_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "stackoverflow.com",
    "github.com",
    "realpython.com",
    "wiki.archlinux.org",
    "learn.microsoft.com",
}

DEBUG = True
REQUEST_TIMEOUT = 6
MAX_HTML_CHARS = 250000
MAX_WEB_CHARS = 7000