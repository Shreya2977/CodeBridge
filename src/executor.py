"""
executor.py
-----------
Runs a candidate Python translation against a test suite inside the sandbox
and returns structured results the repair agent can act on.
"""

from dataclasses import dataclass, field
from sandbox import Sandbox


@dataclass
class TestOutcome:
    input: str
    expected: str
    actual: str
    passed: bool
    error: str = ""


@dataclass
class ExecutionReport:
    outcomes: list = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return len(self.outcomes) > 0 and all(o.passed for o in self.outcomes)

    @property
    def pass_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(o.passed for o in self.outcomes) / len(self.outcomes)

    def first_failure_text(self) -> str:
        """Human-readable failure report for the repair agent -- just the first
        failure, since fixing one at a time keeps repairs focused."""
        for o in self.outcomes:
            if not o.passed:
                return (
                    f"Input: {o.input!r}\n"
                    f"Expected stdout: {o.expected!r}\n"
                    f"Actual stdout:   {o.actual!r}\n"
                    f"Error (if any):  {o.error}"
                )
        return "All tests passed."


def normalize(s: str) -> str:
    """Loose comparison: strip trailing whitespace per line, ignore trailing blank lines.
    For numeric-heavy code, consider swapping this for a float-tolerance comparator."""
    lines = [line.rstrip() for line in s.strip().splitlines()]
    return "\n".join(lines)


def run_tests(candidate_python: str, test_suite: list[dict], sandbox: Sandbox) -> ExecutionReport:
    report = ExecutionReport()
    for case in test_suite:
        result = sandbox.run_python(candidate_python, stdin_input=case["input"])
        passed = (
            result.exit_code == 0
            and normalize(result.stdout) == normalize(case["expected_stdout"])
        )
        report.outcomes.append(TestOutcome(
            input=case["input"],
            expected=case["expected_stdout"],
            actual=result.stdout,
            passed=passed,
            error=result.stderr if result.exit_code != 0 else "",
        ))
    return report
