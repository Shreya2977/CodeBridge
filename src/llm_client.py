"""
llm_client.py
-------------
Thin wrapper around a local Ollama server so every agent calls one place.

Setup:
    1. Install Ollama: https://ollama.com/download
    2. Pull a model:   ollama pull qwen2.5-coder:7b
       (less RAM: qwen2.5-coder:3b or qwen2.5-coder:1.5b)
    3. Ollama runs its own local server automatically on http://localhost:11434
       -- nothing else to start.

Config (optional, has sane defaults):
    export OLLAMA_MODEL=qwen2.5-coder:7b
    export OLLAMA_HOST=http://localhost:11434
"""

import os
import re
import requests

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def ask(system: str, user: str, max_tokens: int = 2000, temperature: float = 0.2) -> str:
    """Single-turn call to the local Ollama server, returns plain text response."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
            timeout=300,  # local inference on CPU can be slow, give it room
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not reach Ollama at {OLLAMA_HOST}. "
            "Is Ollama installed and running? (it should start automatically after install; "
            "otherwise run `ollama serve`)"
        )
    data = response.json()
    return data["message"]["content"]


def extract_code_block(text: str, lang_hint: str = "") -> str:
    """
    Pull code out of a markdown fence if the model wrapped it in one.
    Falls back to returning the raw text if no fence is found.
    Local models are more likely to add stray commentary before/after the
    fence (e.g. "Here's the translated code:"), so this matters more here
    than it would calling a hosted frontier model.
    """
    pattern = rf"```(?:{lang_hint})?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


if __name__ == "__main__":
    print(f"Model: {OLLAMA_MODEL}  |  Host: {OLLAMA_HOST}")
    print(ask("You are a helpful assistant.", "Say hello in one sentence."))


