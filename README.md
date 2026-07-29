# Test-Driven Code Translation: Fortran → Python

**Category:** Software Evolution, DevOps & Migration Engineering

A closed-loop system for automated legacy code migration. Instead of trusting
a single AI translation, the framework:

1. Generates a test suite from the **original** program's real behavior (not
   an LLM's guess at behavior — actual execution is the test oracle).
2. Translates the source into the target language.
3. Runs the translated candidate against the tests inside an isolated Docker
   sandbox.
4. If tests fail, a repair agent reads the structured failure and patches the
   code, then the loop retests — up to a capped number of iterations.

It also runs a single-shot baseline translation (no repair loop) so the two
can be compared head-to-head.

Current language pair: **Fortran → Python**. See "Extending" below to add
another pair.

---

## Why this approach

LLMs are decent single-shot code translators but routinely produce code that
*compiles and looks plausible but behaves incorrectly* — wrong array
indexing (Fortran is 1-indexed, Python is 0-indexed), wrong loop bounds,
subtle floating-point or control-flow drift. A compiler error would catch
some of this; it won't catch silent behavioral bugs. Only actually *running*
the translated code against real test cases catches those — which is the
whole premise of this project.

---

## Architecture

```
Source (Fortran)
      │
      ▼
┌─────────────────────┐
│ Test Generator        │  LLM proposes input cases; ORIGINAL source is
│ (test_generator.py)   │  executed in the sandbox to capture real expected
└──────────┬────────────┘  output (the test oracle — never an LLM guess)
           │ test_suite (list of input → expected_output)
           ▼
┌─────────────────────┐
│ Translator Agent      │  Agent 1 — converts Fortran → Python
│ (translator_agent.py) │
└──────────┬────────────┘
           ▼
┌─────────────────────┐
│ Sandbox Executor      │  Runs candidate against every test case inside an
│ (sandbox.py/executor) │  isolated, network-disabled, resource-limited
└──────────┬────────────┘  Docker container
           │
     ┌─────┴─────┐
     │ all pass? │───yes──▶ done
     └─────┬─────┘
           │ no
           ▼
┌─────────────────────┐
│ Repair Agent          │  Agent 2 — gets a structured failure report
│ (repair_agent.py)     │  (input, expected, actual, error) and makes a
└──────────┬────────────┘  minimal targeted fix
           │
           └──────────▶ back to Sandbox Executor (loop, capped at
                          max_iterations)
```

---

## Tech stack

| Component | Choice | Why |
|---|---|---|
| Orchestration | Plain Python state loop | Explicit, debuggable translate → test → repair cycle; no framework overhead needed for this shape of loop |
| LLM backend | [Ollama](https://ollama.com) + `qwen2.5-coder` | Free, runs locally, strong on code tasks relative to its size |
| Sandbox | Docker (long-lived container + `exec`) | Isolated, network-disabled, resource-limited execution of AI-generated code |
| Source compiler | `gfortran` | Compiles the original Fortran and (for the oracle step) re-runs it with generated inputs |
| Test comparison | Exact string match (whitespace-normalized) | Simple default; swap for float-tolerance comparison on numeric-heavy scripts (see Extending) |

---

## Project layout

```
docker/Dockerfile          sandbox image: gfortran + python3
src/sandbox.py             manages the long-lived container, runs code via `docker exec`
src/llm_client.py          wrapper around the local Ollama server
src/test_generator.py      LLM proposes inputs; source execution is the ground-truth oracle
src/translator_agent.py    Agent 1 — Fortran -> Python translation (also the baseline)
src/repair_agent.py        Agent 2 — reads failure report, patches candidate
src/executor.py            runs a candidate against the test suite, structured pass/fail
src/orchestrator.py        the closed loop + baseline comparison + saves all code to disk
main.py                    runs the whole experiment over scripts/, writes results.csv
scripts/*.f90               sample Fortran programs to translate
results/results.csv        summary metrics, one row per script (created after a run)
results/translations/      every translated candidate, saved per script (created after a run)
```

---

## Setup

### 1. Docker
Install [Docker Desktop](https://www.docker.com/products/docker-desktop) and
make sure it's actually running (check the whale icon in your system tray /
menu bar) before doing anything else. Verify:
```
docker version
```
should print both a **Client** and a **Server** section.

### 2. Ollama + model
Install [Ollama](https://ollama.com/download), then pull a model — pick based
on available RAM:
```
ollama pull qwen2.5-coder:7b     # ~6GB RAM, best quality of the local options
ollama pull qwen2.5-coder:3b     # ~3GB RAM, lighter, still reasonable
ollama pull qwen2.5-coder:1.5b   # ~2GB RAM, lightest, noticeably weaker reasoning
```
Ollama runs its own local server automatically after install
(`http://localhost:11434`) — nothing else to start.

Optional overrides (defaults shown):
```
export OLLAMA_MODEL=qwen2.5-coder:7b
export OLLAMA_HOST=http://localhost:11434
```
(Windows PowerShell: `$env:OLLAMA_MODEL="qwen2.5-coder:7b"`)

### 3. Python environment
```
python3 -m venv venv
source venv/bin/activate        # Windows (PowerShell): venv\Scripts\Activate.ps1
                                 # Windows (cmd.exe):    venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 4. Build the sandbox image
```
docker build -t codetranslate-sandbox -f docker/Dockerfile docker/
```

### 5. Sanity-check before the full run
```
python src/llm_client.py     # should print a one-line greeting from the model
python src/sandbox.py        # should print output from a Fortran + Python hello-world
```

---

## Running the experiment

```
python main.py
```

For every `.f90` file in `scripts/`, this:
1. Generates a test suite (LLM-proposed inputs, real Fortran-execution outputs).
2. Runs the single-shot baseline translation and tests it.
3. Runs the closed-loop translate → test → repair cycle (capped at 5 iterations).
4. Saves results and code to disk (see Outputs below).

A summary — baseline vs. framework success rate, average repair iterations —
prints at the end.

---

## Outputs

**`results/results.csv`** — one row per script:

| column | meaning |
|---|---|
| `script` | filename |
| `num_tests` | number of valid test cases generated |
| `baseline_passed` | did the single-shot translation pass all tests |
| `baseline_pass_rate` | fraction of tests the baseline passed |
| `framework_passed` | did the closed-loop framework converge |
| `framework_iterations` | how many repair iterations it took |
| `wall_clock_seconds` | total time for that script |

**`results/translations/<script_name>/`** — the actual translated code, per script:
```
baseline.py               single-shot baseline candidate
framework_iter_0.py        first framework attempt (pre-repair)
framework_iter_1.py        after 1st repair, etc.
framework_final.py         last candidate produced (whether or not it passed)
iteration_summary.txt      pass-rate per iteration, at a glance
```
This is what you want open during a demo — it lets you show, concretely, a
bug the baseline shipped silently and the exact iteration where the
framework's repair loop fixed it.

---

## Validating the approach (suggested experiment)

- Translate a batch of algorithmic scripts (start with the 3 in `scripts/`,
  scale to ~50 for a full evaluation) from Fortran to Python.
- Compare **Functional Success Rate** (baseline vs. framework) — percentage
  of translations passing all functional test cases.
- Track **average repair iterations** needed to reach functional equivalence.
- Consider a second baseline: repair using only compiler-error feedback (no
  test-driven failure report) — isolates how much value comes specifically
  from test-driven repair vs. any feedback loop at all.
- Report cost-normalized success rate too, since the framework makes several
  LLM calls per script vs. one for the baseline — raw success rate alone
  doesn't account for that.

---

## Known limitations

- **Test-input format guessing**: the test generator relies on the LLM
  correctly inferring the source program's stdin format. Fortran's
  line-based `read(*,*)` semantics (each separate `read` statement consumes
  its own line) trips up smaller local models — the prompt in
  `test_generator.py` explicitly documents this rule, but expect occasional
  skipped/invalid test inputs, especially with `qwen2.5-coder:1.5b` or `:3b`.
- **Exact-match comparison**: `executor.py`'s `normalize()` does whitespace-
  trimmed exact string comparison. Floating-point-heavy scripts may need a
  tolerance-based comparator instead (see Extending).
- **Local model variability**: smaller models add more stray commentary
  around code blocks and need more repair iterations to converge than a
  frontier hosted model would — this is expected, and arguably an
  interesting result to report rather than a bug to hide.

---

## Extending

- **Add more scripts**: drop more `.f90` files into `scripts/`. Keep them
  stdin/stdout based (no file I/O) so the sandbox comparison stays simple.
- **Numeric tolerance**: swap `executor.py`'s exact string comparison for a
  tolerance-based comparator (parse floats, compare with `abs(a - b) < 1e-6`)
  for floating-point-heavy scripts.
- **New language pair**: add a `run_<language>` method to `Sandbox`
  (mirroring `run_fortran`/`run_python`), add the compiler to the
  Dockerfile, and point `translator_agent.py` / `repair_agent.py` prompts at
  the new target.
- **Second baseline** (compiler-error-only repair, no test-driven feedback):
  add a variant of `run_closed_loop` that only shows the repair agent
  stderr/exit code, not the full test failure report.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ConnectionError` from `llm_client.py` | Ollama isn't running — try `ollama serve` in a separate terminal |
| `failed to connect to the docker API` | Docker Desktop isn't running — open it and wait ~1 min for the engine to start, verify with `docker version` |
| PowerShell: `venv\Scripts\Activate.ps1 cannot be loaded` | Run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, then open a fresh terminal |
| `ERROR: Could not open requirements file` | You're not in the project root — `cd` into the folder containing `requirements.txt` first |
| Fortran source itself fails with `End of file` during test generation | The LLM guessed a bad stdin format; this is skipped automatically and logged — a few skips per script is normal |
| First `python src/llm_client.py` call takes a long time | Normal — first call loads the model into memory; subsequent calls are faster |
