"""
test_generator.py
------------------
Builds a test_suite.json for a given source script:
  1. LLM proposes a set of stdin inputs covering typical + edge cases.
  2. Each input is actually run through the ORIGINAL Fortran source in the
     sandbox -> that real output becomes the ground-truth "expected".
     (This is the test oracle. We never trust an LLM's guessed output.)
"""

import json
from llm_client import ask
from sandbox import Sandbox

TEST_GEN_SYSTEM_PROMPT = """You are a test-input generator for legacy scientific code.
Given a Fortran program, propose a JSON list of stdin input strings that exercise:
- typical/normal cases
- boundary values (0, 1, negative numbers, empty-ish inputs where valid)
- at least one edge case likely to expose off-by-one or indexing bugs

CRITICAL Fortran stdin formatting rule, get this exactly right or the program
will crash with "End of file" errors:
- Count how many separate `read(*,*)` STATEMENTS exist (including ones inside loops).
  Each SEPARATE read(*,*) statement consumes its own line -- values for different
  read statements must each be on their OWN line, never combined on one line.
- If ONE read(*,*) statement reads multiple values (e.g. `read(*,*) a, b, c`),
  those values CAN be space or comma separated on the same line.
- Example: a program that does `read(*,*) n` then loops `do i=1,n; read(*,*) arr(i); end do`
  needs input like "3\\n10\\n20\\n30\\n" (n=3, then each array value on its own line)
  -- NOT "3\\n10 20 30\\n" (that will fail).

Read the program's source carefully to count read statements before generating inputs.
Respond with ONLY a JSON array of strings, nothing else. Each string is exactly what
would be typed as stdin for one run. Example: ["5\\n", "0\\n", "-3\\n"]
Aim for 6-10 inputs."""


def generate_test_inputs(fortran_source: str) -> list[str]:
    response = ask(
        system=TEST_GEN_SYSTEM_PROMPT,
        user=f"Fortran program:\n\n{fortran_source}",
        max_tokens=1000,
    )
    # strip markdown fences if present
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        inputs = json.loads(text)
        assert isinstance(inputs, list)
        return inputs
    except (json.JSONDecodeError, AssertionError):
        # fallback: minimal safe default so the pipeline doesn't crash
        print(f"[test_generator] WARNING: could not parse LLM output, got:\n{response}")
        return ["1\n", "5\n", "0\n"]


def build_test_suite(fortran_source: str, sandbox: Sandbox) -> list[dict]:
    """
    Returns a list of {"input": ..., "expected_stdout": ..., "expected_exit_code": ...}
    by executing the real source code as the ground-truth oracle.
    """
    inputs = generate_test_inputs(fortran_source)
    suite = []
    for stdin_val in inputs:
        result = sandbox.run_fortran(fortran_source, stdin_input=stdin_val)
        if result.exit_code != 0:
            # skip inputs that don't even run on the original -- not a valid test case
            print(f"[test_generator] skipping input {stdin_val!r}: source itself failed ({result.stderr[:100]})")
            continue
        suite.append({
            "input": stdin_val,
            "expected_stdout": result.stdout,
            "expected_exit_code": result.exit_code,
        })
    return suite


def save_test_suite(suite: list[dict], path: str):
    with open(path, "w") as f:
        json.dump(suite, f, indent=2)


if __name__ == "__main__":
    sample = open("../scripts/bubble_sort.f90").read()
    with Sandbox() as sb:
        suite = build_test_suite(sample, sb)
        print(json.dumps(suite, indent=2))


# """
# test_generator.py
# ------------------
# Builds a test_suite.json for a given source script:
#   1. LLM proposes a set of stdin inputs covering typical + edge cases.
#   2. Each input is actually run through the ORIGINAL Fortran source in the
#      sandbox -> that real output becomes the ground-truth "expected".
#      (This is the test oracle. We never trust an LLM's guessed output.)
# """

# import json
# from llm_client import ask
# from sandbox import Sandbox

# TEST_GEN_SYSTEM_PROMPT = """You are a test-input generator for legacy scientific code.
# Given a Fortran program, propose a JSON list of stdin input strings that exercise:
# - typical/normal cases
# - boundary values (0, 1, negative numbers, empty-ish inputs where valid)
# - at least one edge case likely to expose off-by-one or indexing bugs

# Read the program to determine what it expects from stdin (number of values, format).
# Respond with ONLY a JSON array of strings, nothing else. Each string is exactly what
# would be typed as stdin for one run. Example: ["5\\n", "0\\n", "-3\\n"]
# Aim for 6-10 inputs."""


# def generate_test_inputs(fortran_source: str) -> list[str]:
#     response = ask(
#         system=TEST_GEN_SYSTEM_PROMPT,
#         user=f"Fortran program:\n\n{fortran_source}",
#         max_tokens=1000,
#     )
#     # strip markdown fences if present
#     text = response.strip()
#     if text.startswith("```"):
#         text = text.split("```")[1]
#         if text.startswith("json"):
#             text = text[4:]
#     try:
#         inputs = json.loads(text)
#         assert isinstance(inputs, list)
#         return inputs
#     except (json.JSONDecodeError, AssertionError):
#         # fallback: minimal safe default so the pipeline doesn't crash
#         print(f"[test_generator] WARNING: could not parse LLM output, got:\n{response}")
#         return ["1\n", "5\n", "0\n"]


# def build_test_suite(fortran_source: str, sandbox: Sandbox) -> list[dict]:
#     """
#     Returns a list of {"input": ..., "expected_stdout": ..., "expected_exit_code": ...}
#     by executing the real source code as the ground-truth oracle.
#     """
#     inputs = generate_test_inputs(fortran_source)
#     suite = []
#     for stdin_val in inputs:
#         result = sandbox.run_fortran(fortran_source, stdin_input=stdin_val)
#         if result.exit_code != 0:
#             # skip inputs that don't even run on the original -- not a valid test case
#             print(f"[test_generator] skipping input {stdin_val!r}: source itself failed ({result.stderr[:100]})")
#             continue
#         suite.append({
#             "input": stdin_val,
#             "expected_stdout": result.stdout,
#             "expected_exit_code": result.exit_code,
#         })
#     return suite


# def save_test_suite(suite: list[dict], path: str):
#     with open(path, "w") as f:
#         json.dump(suite, f, indent=2)


# if __name__ == "__main__":
#     sample = open("../scripts/bubble_sort.f90").read()
#     with Sandbox() as sb:
#         suite = build_test_suite(sample, sb)
#         print(json.dumps(suite, indent=2))
