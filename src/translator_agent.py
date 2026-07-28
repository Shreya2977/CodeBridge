"""
translator_agent.py
--------------------
Agent 1: translates source code (Fortran) into target code (Python).
Also used standalone as the "baseline single-shot" condition in your experiment.
"""

from llm_client import ask, extract_code_block

TRANSLATE_SYSTEM_PROMPT = """You are an expert code migration engineer specializing in
translating legacy Fortran into modern, idiomatic Python 3.

Rules:
- Preserve exact functional behavior, including numeric precision where it matters.
- Watch for Fortran 1-indexed arrays -> Python 0-indexed arrays.
- Preserve the program's stdin/stdout interface exactly: read the same inputs in the
  same order, print the same outputs in the same format the original does.
- Output ONLY the Python code in a single ```python fenced block. No explanation."""


def translate(fortran_source: str) -> str:
    """Single-shot baseline translation (no feedback loop)."""
    response = ask(
        system=TRANSLATE_SYSTEM_PROMPT,
        user=f"Translate this Fortran program to Python:\n\n{fortran_source}",
        max_tokens=2000,
        temperature=0.2,
    )
    return extract_code_block(response, lang_hint="python")
