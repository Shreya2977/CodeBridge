"""
orchestrator.py
----------------
The closed-loop system: translate -> test -> repair -> retest, until tests
pass or max_iterations is hit. Also runs the single-shot baseline for
comparison. This is what main.py calls per script in the experiment.
"""

import os
import time
from dataclasses import dataclass, field

from sandbox import Sandbox
from test_generator import build_test_suite
from translator_agent import translate
from repair_agent import repair
from executor import run_tests, ExecutionReport


@dataclass
class RunLog:
    script_name: str
    baseline_passed: bool = False
    framework_passed: bool = False
    iterations_used: int = 0
    history: list = field(default_factory=list)  # code + pass_rate per iteration
    wall_clock_seconds: float = 0.0


def run_baseline(fortran_source: str, test_suite: list[dict], sandbox: Sandbox) -> tuple[bool, ExecutionReport, str]:
    """Single-shot translation, no repair loop -- the control condition."""
    candidate = translate(fortran_source)
    report = run_tests(candidate, test_suite, sandbox)
    return report.all_passed, report, candidate


def run_closed_loop(
    fortran_source: str,
    test_suite: list[dict],
    sandbox: Sandbox,
    max_iterations: int = 5,
) -> RunLog:
    log = RunLog(script_name="", iterations_used=0)

    candidate = translate(fortran_source)
    report = run_tests(candidate, test_suite, sandbox)
    log.history.append({"iteration": 0, "pass_rate": report.pass_rate, "code": candidate})

    iteration = 0
    while not report.all_passed and iteration < max_iterations:
        iteration += 1
        failure_text = report.first_failure_text()
        candidate = repair(fortran_source, candidate, failure_text)
        report = run_tests(candidate, test_suite, sandbox)
        log.history.append({"iteration": iteration, "pass_rate": report.pass_rate, "code": candidate})

    log.iterations_used = iteration
    log.framework_passed = report.all_passed
    return log


def process_script(script_path: str, max_iterations: int = 5, output_dir: str = "results/translations") -> dict:
    """Full pipeline for one script: generate tests, run baseline, run closed loop.
    Also saves every translated candidate to disk under output_dir/<script_name>/."""
    with open(script_path) as f:
        fortran_source = f.read()

    script_name = script_path.split("/")[-1].split("\\")[-1]  # handle both / and \ paths
    script_stem = script_name.rsplit(".", 1)[0]
    start = time.time()

    with Sandbox() as sandbox:
        print(f"[{script_name}] generating test suite...")
        test_suite = build_test_suite(fortran_source, sandbox)
        if not test_suite:
            print(f"[{script_name}] WARNING: empty test suite, skipping")
            return {"script": script_name, "error": "empty test suite"}

        print(f"[{script_name}] running baseline (single-shot)...")
        baseline_passed, baseline_report, baseline_code = run_baseline(fortran_source, test_suite, sandbox)

        print(f"[{script_name}] running closed-loop framework...")
        loop_log = run_closed_loop(fortran_source, test_suite, sandbox, max_iterations)

    elapsed = time.time() - start

    # --- save all translated code to disk ---
    script_out_dir = os.path.join(output_dir, script_stem)
    os.makedirs(script_out_dir, exist_ok=True)

    with open(os.path.join(script_out_dir, "baseline.py"), "w") as f:
        f.write(baseline_code)

    for entry in loop_log.history:
        fname = f"framework_iter_{entry['iteration']}.py"
        with open(os.path.join(script_out_dir, fname), "w") as f:
            f.write(entry["code"])

    # convenience copy: the final framework candidate, clearly labeled
    final_code = loop_log.history[-1]["code"]
    with open(os.path.join(script_out_dir, "framework_final.py"), "w") as f:
        f.write(final_code)

    # small per-script summary so you can see pass_rate progression per iteration
    with open(os.path.join(script_out_dir, "iteration_summary.txt"), "w") as f:
        f.write(f"Script: {script_name}\n")
        f.write(f"Baseline passed: {baseline_passed} (pass_rate={baseline_report.pass_rate:.2f})\n")
        f.write(f"Framework passed: {loop_log.framework_passed}\n\n")
        f.write("Iteration | Pass rate\n")
        for entry in loop_log.history:
            f.write(f"{entry['iteration']:9d} | {entry['pass_rate']:.2f}\n")

    result = {
        "script": script_name,
        "num_tests": len(test_suite),
        "baseline_passed": baseline_passed,
        "baseline_pass_rate": baseline_report.pass_rate,
        "framework_passed": loop_log.framework_passed,
        "framework_iterations": loop_log.iterations_used,
        "wall_clock_seconds": round(elapsed, 2),
    }
    print(f"[{script_name}] done: baseline={baseline_passed} framework={loop_log.framework_passed} "
          f"iters={loop_log.iterations_used} time={elapsed:.1f}s")
    print(f"[{script_name}] translated code saved to {script_out_dir}/")
    return result
