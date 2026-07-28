"""
main.py
-------
Entry point. Runs the full experiment over every .f90 file in scripts/
and writes results/results.csv for your report/dashboard.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    docker build -t codetranslate-sandbox -f docker/Dockerfile docker/
    python main.py
"""

import csv
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from orchestrator import process_script  # noqa: E402


def main():
    scripts = sorted(glob.glob("scripts/*.f90"))
    if not scripts:
        print("No .f90 scripts found in scripts/. Add some first.")
        return

    results = []
    for script_path in scripts:
        try:
            result = process_script(script_path, max_iterations=5)
            results.append(result)
        except Exception as e:
            print(f"[{script_path}] FAILED: {e}")
            results.append({"script": script_path, "error": str(e)})

    os.makedirs("results", exist_ok=True)
    out_path = "results/results.csv"
    fieldnames = ["script", "num_tests", "baseline_passed", "baseline_pass_rate",
                  "framework_passed", "framework_iterations", "wall_clock_seconds", "error"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    # quick summary
    valid = [r for r in results if "error" not in r]
    n = len(valid)
    if n:
        baseline_rate = sum(r["baseline_passed"] for r in valid) / n
        framework_rate = sum(r["framework_passed"] for r in valid) / n
        avg_iters = sum(r["framework_iterations"] for r in valid) / n
        print("\n=== SUMMARY ===")
        print(f"Scripts run:              {n}")
        print(f"Baseline success rate:    {baseline_rate:.0%}")
        print(f"Framework success rate:   {framework_rate:.0%}")
        print(f"Avg repair iterations:    {avg_iters:.1f}")
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
