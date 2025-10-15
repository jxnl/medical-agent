# Evaluation Results (`evals/data/`)

This directory stores outputs from evaluation runs. Each run creates a timestamped (or custom) subdirectory containing:

- For escalation: `escalation_results.json`, `escalation_eval.csv`, and a copy of `escalation_tests.json`.
- For tool calls: `tool_call_results.json`, `tool_call_eval.csv`, and a copy of `tool_call_tests.json`.

Subdirectory name is the `run_id` shown by the CLI. You can safely delete old run folders.
