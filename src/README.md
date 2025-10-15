# Source (`src/`)

This directory contains the application code for the Telehealth Agent.

## Components

- `telehealth_service.py`: Core async service. Defines tools, system prompt, and session storage. Exposes `send_message` and `stream_message`.
- `telehealth_bot.py`: Rich terminal chat app. Streams responses and shows tool calls/results.
- `run_evals.py`: Typer CLI to run evaluations (`escalation`, `tool_call`, or `all`). Saves results under `evals/data/<run_id>/`.
- `__init__.py`: Package initializer.

## Run the chatbot

```bash
uv run python src/telehealth_bot.py
```

Optional flags:
- `--prefill "I need to refill my prescription"`
- `--verbose`

## Run evaluations

See `../evals/README.md` for details, or:

```bash
uv run python src/run_evals.py run --eval-type all
```

## Notes

- Code is async-first; prefer `await` and async iteration.
- Sessions live in `.sessions/`. Eval sessions use `.eval_sessions/`.
