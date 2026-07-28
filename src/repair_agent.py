"""
repair_agent.py
----------------
Agent 2: given the original source, the current failing candidate translation,
and a structured failure report, produce a corrected candidate.

Encourages minimal, targeted diffs rather than full rewrites -- keeps repairs
interpretable and makes "iterations to converge" a meaningful metric.
"""

from llm_client import ask, extract_code_block

REPAIR_SYSTEM_PROMPT = """You are a debugging agent fixing a Python translation of a
Fortran program. You will be given:
1. The original Fortran source (ground truth behavior)
2. The current Python candidate (which fails one or more tests)
3. A specific failure report (input, expected output, actual output/error)

Diagnose the root cause (common causes: off-by-one indexing, wrong data type,
incorrect output formatting/whitespace, wrong loop bounds, floating point precision).
Make the SMALLEST change that fixes the issue -- do not rewrite unrelated code.
Output ONLY the corrected, complete Python file in a single ```python fenced block."""


def repair(fortran_source: str, candidate_code: str, failure_report: str) -> str:
    user_prompt = f"""ORIGINAL FORTRAN SOURCE:
{fortran_source}

CURRENT PYTHON CANDIDATE (failing):
{candidate_code}

FAILURE REPORT:
{failure_report}

Produce the corrected Python file."""

    response = ask(
        system=REPAIR_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=2000,
        temperature=0.2,
    )
    return extract_code_block(response, lang_hint="python")
