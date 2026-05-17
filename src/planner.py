from config import MODELS
from utils import ask_ollama, extract_json, log

PLANNER_PROMPT = """
You are CODAMA Planner.

Return ONLY valid JSON:
{
  "plan": ["step 1", "step 2", "step 3"],
  "notes": ""
}

Rules:
- Keep the plan short and useful.
- Break the task into the smallest useful steps.
- Do not add markdown or extra text.
""".strip()

def create_plan(user_text: str, history: list[dict]) -> dict:
    planner_messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        *history[-6:],
        {"role": "user", "content": user_text},
    ]

    try:
        result = ask_ollama(MODELS["planner"], planner_messages, stream=False)
        data = extract_json(result["message"]["content"]) # type: ignore
        if not data:
            return {"plan": [], "notes": ""}
        return {
            "plan": data.get("plan", []),
            "notes": str(data.get("notes", "")).strip(),
        }
    except Exception as e:
        log(f"[PLANNER] error: {e}")
        return {"plan": [], "notes": ""}