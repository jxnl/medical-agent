# Evaluations (`evals/`)

This directory contains datasets and the evaluation framework for the Telehealth Agent.

## Files

- `framework.py`: Dataset model, agent runner, and scorers (`escalation_scorer`, `tool_call_scorer`). Runs tests in parallel.
- `escalation_tests.json`: 75 test cases for escalation behavior.
- `tool_call_tests.json`: 30 test cases validating correct tool selection.
- `data/`: Output directory for results, organized by run ID.

## Running

From repo root:

```bash
uv run python src/run_evals.py run --eval-type all
uv run python src/run_evals.py run --eval-type escalation
uv run python src/run_evals.py run --eval-type tool_call
```

Results are saved to `evals/data/<run_id>/` (JSON + CSV, with git metadata).
