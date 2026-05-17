# CODAMA AI

CODAMA is a modular AI agent system built around a multi-model pipeline.

It includes:
- Router model (decides what to do)
- Planner model (breaks tasks into steps)
- Code model (generates programming solutions)
- Web scraping + retrieval system
- Multi-model execution pipeline

Inspired by Codex-style agent architectures.

---

## Features

- Auto routing between fast / deep / code models
- Web search + scraping (allowed domains only)
- Planning system for complex tasks
- Critic model for code validation
- Streaming responses

---

## Important

CODAMA runs fully locally.

That means:
- No usage limits
- No API keys
- No subscriptions
- No rate caps

Everything runs on your machine through Ollama.
But since CODAMA runs locally, performance depends on your hardware.

- Smaller models run fast on most systems
- Larger models (like 8B+) may use more RAM and CPU/GPU
- First response may be slower while models load

For best performance, a system with a decent CPU/GPU and at least 8–16GB RAM is recommended.

---

## Requirements (Backend)

CODAMA requires Ollama running locally.

### 1. Install Ollama
https://ollama.com

### 2. Start Ollama

Make sure it is running in the background.

### 3. Pull required models

```bash
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
```

## The executable
If you use the executable rather than source code than you don't need to pull these models. This means:
-  You don't have to wait 5 million years for install times
and
-  More portable
You can redistribute your own versions of Codama if you really want to I don't really care.
Just give me credits if you want to do that.
