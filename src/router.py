from config import MODELS
from utils import (
    ask_ollama, extract_json, log,
    is_code_task, needs_planning, needs_web
)

ROUTER_PROMPT = """
You are CODAMA Router.

Return ONLY valid JSON with this schema:
{
  "action": "direct|search|code|plan|clarify",
  "model": "fast|deep|code",
  "use_web": true,
  "use_planning": false,
  "query": "",
  "reason": ""
}

Rules:
- NEVER return an empty object.
- If the task is coding, choose action "code" and model "code".
- If the task is complex or multi-step, use_planning should be true.
- If the task needs docs, APIs, current info, or verification, use_web should be true.
- Do not add markdown, code fences, or extra text.
""".strip()

def heuristic_route(user_text: str) -> dict:
    code = is_code_task(user_text)
    web = needs_web(user_text)
    plan = needs_planning(user_text)

    if code:
        action = "code"
        model = "code"
    elif plan:
        action = "plan"
        model = "deep"
    elif web:
        action = "search"
        model = "deep"
    else:
        action = "direct"
        model = "fast"

    return {
        "action": action,
        "model": model,
        "use_web": web,
        "use_planning": plan or (code and len(user_text.split()) >= 12),
        "query": user_text.strip(),
        "reason": "heuristic fallback",
    }

def route_request(user_text: str, history: list[dict]) -> dict:
    base = heuristic_route(user_text)

    router_messages = [
        {"role": "system", "content": ROUTER_PROMPT},
        *history[-6:],
        {"role": "user", "content": user_text},
    ]

    try:
        result = ask_ollama(MODELS["router"], router_messages, stream=False)
        data = extract_json(result["message"]["content"]) # type: ignore

        if not data or "action" not in data:
            log("[ROUTER] invalid output, using heuristic fallback")
            return base

        action = str(data.get("action", base["action"])).strip().lower()
        model = str(data.get("model", base["model"])).strip().lower()
        use_web = bool(data.get("use_web", False)) or base["use_web"]
        use_planning = bool(data.get("use_planning", False)) or base["use_planning"]
        query = str(data.get("query", user_text)).strip()
        reason = str(data.get("reason", "")).strip()

        if base["action"] == "code":
            action = "code"
            model = "code"
        elif base["action"] == "plan" and action == "direct":
            action = "plan"
            model = "deep"
        elif base["action"] == "search" and action == "direct":
            action = "search"
            model = "deep"

        if action == "code":
            model = "code"
        elif action in {"plan", "search"} and model == "fast":
            model = "deep"

        if model not in MODELS:
            model = base["model"]

        final = {
            "action": action,
            "model": model,
            "use_web": use_web,
            "use_planning": use_planning,
            "query": query,
            "reason": reason or base["reason"],
        }

        log(f"[ROUTER] {final}")
        return final

    except Exception as e:
        log(f"[ROUTER] error: {e}")
        return base