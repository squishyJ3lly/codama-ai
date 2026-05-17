import json
import time

from sys import stdout
from config import MODELS
from utils import timing, ask_ollama, parse_thinking_message
from web import build_web_context
from router import route_request
from planner import create_plan
from critic import critic_review

def stream_response(model: str, messages: list[dict]):
    stream = ask_ollama(model, messages, stream=True)
    full = ""
    
    stdout.write("\nAI: ")
    stdout.flush()

    for chunk in stream:
        text = chunk["message"]["content"] # type: ignore
        full += text
        stdout.write(text)
        stdout.flush()

    stdout.write("\n")
    return full

def answer_with_model(model_name: str, user_text: str, history: list[dict], plan_text: str = "", web_context: str = ""):
    from utils import DEFAULT_SYSTEM_PROMPT

    final_messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]

    if history:
        final_messages.extend(history[-8:])

    if plan_text:
        final_messages.append({"role": "system", "content": f"PLANNING CONTEXT:\n{plan_text}"})

    if web_context:
        final_messages.append({"role": "system", "content": f"WEB CONTEXT:\n{web_context}"})

    final_messages.append({"role": "user", "content": user_text})

    raw = stream_response(model_name, final_messages)
    thinking, message = parse_thinking_message(raw)
    return thinking, message, raw

def process(user_text: str, chat_history: list[dict], debug: bool = True):
    start_total = time.perf_counter()
    stdout.write("Codama is thinking...")

    route_start = time.perf_counter()
    decision = route_request(user_text, chat_history)
    timing("router", route_start)

    stdout.write("\n[ROUTER]")
    stdout.write(f"Action: {decision['action']}")
    stdout.write(f"Model: {decision['model']}")
    stdout.write(f"Web: {decision['use_web']}")
    stdout.write(f"Planning: {decision['use_planning']}")

    plan_text = ""
    if decision["use_planning"]:
        plan_start = time.perf_counter()
        plan = create_plan(user_text, chat_history)
        timing("planner", plan_start)

        print("\n[PLANNER]")
        if plan.get("plan"):
            for i, step in enumerate(plan["plan"], 1):
                stdout.write(f"{i}. {step}")
        else:
            stdout.write("(no plan returned)")

        if plan.get("notes"):
            stdout.write(f"Notes: {plan['notes']}")

        plan_text = json.dumps(plan, indent=2)

    web_context = ""
    if decision["use_web"]:
        web_start = time.perf_counter()
        web_context = build_web_context(decision.get("query", user_text), decision.get("url", ""))
        timing("web", web_start)

        stdout.write("\n[WEB]")
        stdout.write(f"Web context size: {len(web_context)} chars")

    answer_start = time.perf_counter()
    thinking, message, raw = answer_with_model(
        MODELS[decision["model"]],
        user_text,
        chat_history,
        plan_text=plan_text,
        web_context=web_context,
    )
    timing("model_response", answer_start)
    if thinking:
        s = time.perf_counter()
        stdout.write("\n[THINKING]")
        stdout.write(thinking)
        while s < 5:
            if s > 5:
                break
        return

    if decision["action"] == "code":
        critic_start = time.perf_counter()
        critic = critic_review(message)
        timing("critic", critic_start)

        critic_thinking, critic_message = parse_thinking_message(critic)

        stdout.write("\n[CRITIC]")
        if critic_thinking:
            stdout.write(critic_thinking)

        if critic_message and critic_message != "CODE_OK":
            stdout.write("\n[CRITIC FIXED CODE]")
            stdout.write(critic_message)
            message = critic_message
        else:
            stdout.write("Codama Review: CODE_OK")

    stdout.write("FINAL OUTPUT:\n")
    stdout.write(message)

    chat_history.append({"role": "user", "content": user_text})
    chat_history.append({"role": "assistant", "content": message})

    timing("total_pipeline", start_total)