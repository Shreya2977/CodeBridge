# Test-Driven Code Translation: Fortran → Python

Closed-loop system: generate tests from source behavior → translate →
execute in sandbox → self-repair on failure → retest, until tests pass
or max iterations reached. Compares against a single-shot baseline.

## Setup

1. Install Docker Desktop (or Docker Engine) and make sure it's running.
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Build the sandbox image:
   ```
   docker build -t codetranslate-sandbox -f docker/Dockerfile docker/
   ```
4. Choose an LLM backend (pick one):

   ** Ollama (free, runs locally, no API key) **
   ```
   # 1. Install Ollama: https://ollama.com/download
   # 2. Pull a model (pick based on available RAM):
   ollama pull qwen2.5-coder:7b     # ~6GB RAM, best quality of the local options
   # or: ollama pull qwen2.5-coder:3b   (~3GB RAM, lighter)
   # or: ollama pull qwen2.5-coder:1.5b (~2GB RAM, lightest, weakest reasoning)

   export LLM_BACKEND=ollama
   export OLLAMA_MODEL=qwen2.5-coder:7b
   ```
   Ollama runs its own local server automatically after install — nothing else to start.
   Local models are more likely to add stray text around code blocks; the fence-extraction
   in `llm_client.py` handles this, but keep an eye on `results/results.csv` for a run
   or two to make sure candidates are actually being extracted cleanly.

## Run the experiment

```
python main.py
```

This will, for every `.f90` file in `scripts/`:
1. Generate a test suite by asking an LLM for input cases, then running the
   ORIGINAL Fortran source in Docker to capture real expected outputs.
2. Run a single-shot baseline translation and test it.
3. Run the closed-loop translate → test → repair cycle (up to 5 iterations).
4. Log everything to `results/results.csv`.

A summary (baseline vs framework success rate, avg repair iterations)
prints at the end.

## Project layout

```
docker/Dockerfile          sandbox image: gfortran + python3
src/sandbox.py             manages the long-lived container, runs code via `exec`
src/llm_client.py          thin wrapper around the Anthropic API
src/test_generator.py      LLM proposes inputs; source run is the ground-truth oracle
src/translator_agent.py    Agent 1 — Fortran -> Python translation
src/repair_agent.py        Agent 2 — reads failure report, patches candidate
src/executor.py            runs a candidate against the test suite, structured pass/fail
src/orchestrator.py        the closed loop + baseline comparison for one script
main.py                    runs the whole experiment over scripts/, writes results.csv
scripts/*.f90              sample Fortran programs to translate
```

## Extending

- **Add more scripts**: drop more `.f90` files into `scripts/`. Keep them
  stdin/stdout based (no file I/O) so the sandbox comparison stays simple.
- **Numeric tolerance**: `executor.py`'s `normalize()` does exact string
  comparison after whitespace trimming. For floating-point-heavy scripts,
  swap in a tolerance-based comparator (e.g. parse floats, compare with
  `abs(a - b) < 1e-6`) instead of exact string match.
- **New language pair**: add a `run_<language>` method to `Sandbox`
  (mirroring `run_fortran`/`run_python`), add the compiler to the
  Dockerfile, and point `translator_agent.py` / `repair_agent.py` prompts
  at the new target.
- **Second baseline** (compiler-error-only feedback, no test-driven repair):
  add a variant of `run_closed_loop` that only shows the repair agent the
  stderr/exit code, not the test failure report — this isolates how much
  value comes specifically from test-driven feedback.
