# Telehealth Agent

A telehealth chatbot built with Claude Agent SDK that handles prescription refills, appointment management, and provides general health information.

## Features

- Prescription refill requests with safety checks
- Appointment check-in and cancellation
- General health information for routine questions
- Automatic escalation to healthcare providers when needed
- Session-based conversation storage
- Real-time streaming responses

## Installation

```bash
uv sync
```

## Usage

### Interactive CLI

Run the chatbot in interactive mode:

```bash
# Start a new conversation
uv run python src/telehealth_bot.py

# List all previous sessions
uv run python src/telehealth_bot.py --list-sessions

# Continue a previous session
uv run python src/telehealth_bot.py --session <session-id>
```

The CLI supports:
- **Streaming responses** that appear in real-time
- **Session persistence** - conversations are saved automatically
- **Session resumption** - continue previous conversations
- **Session history** - view all messages from previous sessions

### Programmatic Use

You can use the `TelehealthService` class directly in your code:

```python
from src.telehealth_service import TelehealthService

service = TelehealthService()

# Non-streaming
result = await service.send_message(session_id, "I need to refill my prescription")

# Streaming
async for chunk in service.stream_message(session_id, "I have a cold"):
    if chunk["type"] == "text":
        print(chunk["text"], end="")
    elif chunk["type"] == "done":
        print("\nDone!")
```

### Sessions

Sessions are automatically created and stored in `.sessions/` directory as JSON files. Each session maintains the full conversation history.

## Evaluation

### Running Evals

Test the escalation behavior with the evaluation framework:

```bash
uv run python src/run_evals.py
```

This will:
- Load test cases from `evals/escalation_tests.json`
- Run all tests in parallel for faster execution
- Check if escalation behavior matches expectations using `escalation_scorer`
- Display results with pass/fail summary
- Save results to:
  - JSON: `evals/results.json`
  - CSV: `evals/data/escalation_eval_<timestamp>.csv`

### Adding Test Cases

Edit `evals/escalation_tests.json` to add new test cases:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Your test message here"
    }
  ],
  "should_escalate": false,
  "description": "Description of what this tests"
}
```

### Eval Framework

The evaluation framework consists of:
- `Dataset`: Contains test cases with messages and expected behavior
- `run_function`: Executes the agent on test messages
- `scorer`: Compares actual behavior to expected behavior

## Project Structure

```
telehealth-agent/
├── src/                     # Source code
│   ├── telehealth_service.py    # Core service with session management
│   ├── telehealth_bot.py         # Interactive CLI
│   └── run_evals.py             # Evaluation runner
├── evals/                   # Evaluation framework
│   ├── framework.py         # Eval framework (Dataset, scorer)
│   ├── escalation_tests.json # Test cases for escalation behavior
│   └── data/                # Eval results (gitignored)
├── docs/                    # Documentation
│   ├── CLAUDE.md            # Claude Code guidance
│   ├── DESIGN.md            # Design philosophy
│   ├── FEATURES.md          # Feature documentation
│   ├── IMPLEMENTATION.md    # Implementation details
│   └── TESTING_GUIDE.md     # Testing guide
├── .sessions/               # Session storage (gitignored)
├── .eval_sessions/          # Eval session storage (gitignored)
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## Escalation Policy

The agent follows these escalation rules:

**Handles without escalation:**
- Common illnesses (colds, minor injuries, basic self-care)
- General wellness and prevention questions
- Prescription refills (when eligible)
- Appointment check-in and cancellation
- General guidance on when to seek care

**Escalates immediately for:**
- Specific diagnosis requests
- Serious or concerning symptoms
- Treatment plans requiring medical judgment
- New medication requests
- Controlled substances
- Prescription issues (expired, no refills, etc.)
- Insurance or billing questions

