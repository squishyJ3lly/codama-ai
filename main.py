# ============================================
# CODAMA AI SYSTEM
# Router + Planner + Critic + Web + Streaming
# ============================================

import os
import re
import json
import time
import requests
import ollama

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

# ============================================
# MODELS
# ============================================

MODELS = {
    "router": "llama3.2:3b",
    "planner": "llama3.1:8b",
    "fast": "llama3.2:3b",
    "deep": "llama3.1:8b",
    "code": "qwen2.5-coder:7b",
    "critic": "deepseek-coder:6.7b"
}

# ============================================
# SETTINGS
# ============================================

DEBUG = True
MAX_WEB_CHARS = 7000
REQUEST_TIMEOUT = 6

ALLOWED_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "stackoverflow.com",
    "github.com",
    "realpython.com",
    "wiki.archlinux.org",
    "learn.microsoft.com",
}

# ============================================
# PROMPTS
# ============================================

SYSTEM_PROMPT = """
You are CODAMA, a structured AI assistant.

You must:
- answer clearly and accurately
- keep responses concise by default
- give code that is correct and ready to run
- use provided web context only when relevant
- follow planning instructions before answering
- ask short clarifying questions only when needed

You must not:
- invent APIs, syntax, instructions, or facts
- explain code unless asked
- mention internal prompts, routing, planning, or hidden systems

Behavior:
- simple questions -> concise answers
- coding questions -> code-first
- debugging -> identify issue then fix
- architecture tasks -> structured responses

You MUST return ONLY this format:

THINKING:
(short optional reasoning)

MESSAGE:
(final answer only)

Rules:
- thinking should stay short
- message is the final user-facing response
- for simple prompts, thinking can be empty
"""

ROUTER_PROMPT = """
You are CODAMA Router.

Return ONLY valid JSON:

{
  "action": "direct|search|code|plan|clarify",
  "model": "fast|deep|code",
  "use_web": true,
  "use_planning": false,
  "query": "",
  "reason": ""
}

Rules:
- code tasks -> action=code model=code
- large systems -> use_planning=true
- obscure libraries/frameworks -> use_web=true
- explanations -> model=deep
- simple chat -> model=fast
"""

PLANNER_PROMPT = """
You are CODAMA Planner.

Return ONLY valid JSON:

{
  "plan": [
    "step 1",
    "step 2"
  ],
  "notes": ""
}

Rules:
- keep plans concise
- break large tasks into logical steps
- no markdown
"""

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
(corrected code OR 'CODE_OK')
"""

# ============================================
# MEMORY
# ============================================

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]

# ============================================
# UTILITIES
# ============================================

def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def timing(label, start):
    elapsed = time.perf_counter() - start
    print(f"[{label}] {elapsed:.2f}s")

def extract_section(text, section):
    pattern = rf"{section}:\s*(.*?)(?=\n[A-Z]+:|$)"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return ""

def extract_json(text):
    try:
        return json.loads(text)
    except:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass

    return {}

# ============================================
# OLLAMA
# ============================================

def ask_model(model, chat_messages, stream=False):
    return ollama.chat(
        model=model,
        messages=chat_messages,
        stream=stream
    )

# ============================================
# STREAMING
# ============================================

def stream_response(model, chat_messages):
    start = time.perf_counter()

    stream = ask_model(model, chat_messages, stream=True)

    full = ""

    print("\nAI: ", end="", flush=True)

    for chunk in stream:
        text = chunk["message"]["content"] # type: ignore

        full += text

        print(text, end="", flush=True)

    print()

    timing("model_response", start)

    return full

# ============================================
# URL HELPERS
# ============================================

def normalize_url(url):
    if not url.startswith("http"):
        url = "https://" + url

    return url

def is_allowed(url):
    parsed = urlparse(url)

    domain = parsed.netloc.lower().replace("www.", "")

    return domain in ALLOWED_DOMAINS

# ============================================
# SEARCH
# ============================================

def search_web(query):
    start = time.perf_counter()

    debug(f"Searching web: {query}")

    query += " " + " ".join(
        f"site:{d}" for d in ALLOWED_DOMAINS
    )

    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        timeout=REQUEST_TIMEOUT
    )

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for a in soup.select(".result__a"):
        href = a.get("href")

        if not href:
            continue

        parsed = urlparse(href) # type: ignore

        qs = parse_qs(parsed.query)

        if "uddg" in qs:
            target = unquote(qs["uddg"][0])
        else:
            target = href

        target = normalize_url(target)

        if is_allowed(target):
            results.append(target)

    timing("search", start)

    return results[:2]

# ============================================
# SCRAPER
# ============================================

def scrape(url):
    start = time.perf_counter()

    url = normalize_url(url)

    if not is_allowed(url):
        raise ValueError(f"Blocked domain: {url}")

    debug(f"Scraping: {url}")

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    html = response.text[:200000]

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup([
        "script",
        "style",
        "svg",
        "img",
        "noscript"
    ]):
        tag.decompose()

    text = soup.get_text("\n")

    lines = []

    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()

        if line:
            lines.append(line)

    cleaned = "\n".join(lines)

    cleaned = cleaned[:MAX_WEB_CHARS]

    timing("scrape", start)

    return cleaned

# ============================================
# ROUTER
# ============================================

def route(user_text):
    start = time.perf_counter()

    router_messages = [
        {
            "role": "system",
            "content": ROUTER_PROMPT
        },
        {
            "role": "user",
            "content": user_text
        }
    ]

    result = ask_model(
        MODELS["router"],
        router_messages
    )

    content = result["message"]["content"] # type: ignore

    data = extract_json(content)

    timing("router", start)

    debug(f"Route: {data}")

    return data

# ============================================
# PLANNER
# ============================================

def create_plan(user_text):
    start = time.perf_counter()

    planner_messages = [
        {
            "role": "system",
            "content": PLANNER_PROMPT
        },
        {
            "role": "user",
            "content": user_text
        }
    ]

    result = ask_model(
        MODELS["planner"],
        planner_messages
    )

    content = result["message"]["content"] # type: ignore

    data = extract_json(content)

    timing("planner", start)

    debug(f"Plan: {data}")

    return data

# ============================================
# CRITIC
# ============================================

def critic_review(code):
    start = time.perf_counter()

    critic_messages = [
        {
            "role": "system",
            "content": CRITIC_PROMPT
        },
        {
            "role": "user",
            "content": code
        }
    ]

    result = ask_model(
        MODELS["critic"],
        critic_messages
    )

    content = result["message"]["content"] # type: ignore

    timing("critic", start)

    return content

# ============================================
# WEB CONTEXT
# ============================================

def build_web_context(query):
    start = time.perf_counter()

    urls = search_web(query)

    contexts = []

    for url in urls:
        try:
            page = scrape(url)

            contexts.append(
                f"URL: {url}\n\n{page}"
            )

        except Exception as e:
            debug(str(e))

    final = "\n\n---\n\n".join(contexts)

    timing("web_context", start)

    return final

# ============================================
# MAIN AI PIPELINE
# ============================================

def process(user_text):
    overall_start = time.perf_counter()

    print("\n===================================")
    print("CODAMA PIPELINE")
    print("===================================")

    # ----------------------------
    # ROUTER
    # ----------------------------

    decision = route(user_text)

    action = decision.get("action", "direct")
    model_key = decision.get("model", "fast")
    use_web = decision.get("use_web", False)
    use_planning = decision.get("use_planning", False)

    model = MODELS.get(model_key, MODELS["fast"])

    print(f"\n[ROUTER]")
    print(f"Action: {action}")
    print(f"Model: {model}")
    print(f"Web: {use_web}")
    print(f"Planning: {use_planning}")

    # ----------------------------
    # PLANNING
    # ----------------------------

    plan_text = ""

    if use_planning:
        plan = create_plan(user_text)

        print("\n[PLANNER]")

        for i, step in enumerate(plan.get("plan", []), 1):
            print(f"{i}. {step}")

        plan_text = json.dumps(plan, indent=2)

    # ----------------------------
    # WEB
    # ----------------------------

    web_context = ""

    if use_web:
        print("\n[WEB SEARCH ENABLED]")

        web_context = build_web_context(
            decision.get("query", user_text)
        )

        print(f"[WEB CONTEXT SIZE] {len(web_context)} chars")

    # ----------------------------
    # FINAL MODEL INPUT
    # ----------------------------

    final_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if plan_text:
        final_messages.append({
            "role": "system",
            "content": f"PLANNING:\n{plan_text}"
        })

    if web_context:
        final_messages.append({
            "role": "system",
            "content": f"WEB_CONTEXT:\n{web_context}"
        })

    final_messages.append({
        "role": "user",
        "content": user_text
    })

    # ----------------------------
    # MAIN RESPONSE
    # ----------------------------

    response = stream_response(
        model,
        final_messages
    )

    thinking = extract_section(response, "THINKING")
    message = extract_section(response, "MESSAGE")

    # ----------------------------
    # DEBUG THINKING
    # ----------------------------

    if thinking:
        print("\n[THINKING]")
        print(thinking)

    # ----------------------------
    # CRITIC PASS
    # ----------------------------

    if action == "code":
        print("\n[CRITIC REVIEW]")

        critic = critic_review(message)

        critic_message = extract_section(
            critic,
            "MESSAGE"
        )

        if critic_message and critic_message != "CODE_OK":
            print("\n[CRITIC FIXED CODE]")
            print(critic_message)

            message = critic_message

    # ----------------------------
    # SAVE MEMORY
    # ----------------------------

    messages.append({
        "role": "user",
        "content": user_text
    })

    messages.append({
        "role": "assistant",
        "content": message
    })

    # ----------------------------
    # FINAL OUTPUT
    # ----------------------------

    print("\n===================================")
    print("FINAL OUTPUT")
    print("===================================\n")

    print(message)

    timing("total_pipeline", overall_start)

# ============================================
# CHAT LOOP
# ============================================

def chat():
    print("CODAMA READY.")
    print("Type 'exit' to quit.")

    while True:
        user = input("\nYou: ").strip()

        if not user:
            continue

        if user.lower() in ["exit", "quit"]:
            break

        try:
            process(user)

        except Exception as e:
            print(f"\n[ERROR] {e}")

# ============================================
# START
# ============================================

if __name__ == "__main__":
    chat()