# Telehealth Agent

A telehealth chatbot built with Claude Agent SDK that handles prescription refills, appointment management, and provides general health information.

## Features

- Prescription refill requests with safety checks
- Appointment check-in and cancellation
- General health information for routine questions
- **Knowledge base search** for insurance, medication, and billing information
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

## Knowledge Base Search

The agent can search a knowledge base of insurance, medication, and billing information to answer common questions. The search uses fuzzy string matching to handle typos and variations in phrasing.

### What's in the Knowledge Base

- **Insurance information**: PPO vs HMO, referrals, emergency coverage, out-of-network providers, prescription tiers, preventive care
- **Medication guides**: Side effects, drug interactions, taking medications with food, storage, missed doses, antibiotics, generics vs brand names
- **Billing information**: Copays vs deductibles, coinsurance, payment plans, disputing bills, claim submission, financial assistance, explanation of benefits

### How It Works

1. The agent uses the `search_knowledge_base` tool for insurance, medication, or billing questions
2. The search returns results with confidence scores
3. High-confidence matches (85+) are presented as reliable information
4. Low-confidence or account-specific questions trigger escalation to a human

### Manual Verification Questions

Test these queries to verify the search feature is working correctly:

#### High-Confidence Matches (should return clear answers)

- "What's the difference between PPO and HMO insurance?"
- "Tell me about statin side effects"
- "How do copays work?"
- "What's covered in the emergency room?"
- "What are generic medications?"
- "How do I store my medications?"

#### Fuzzy Matching (tests typo tolerance)

- "side affects of cholestrol meds" (typos should still match statin information)
- "ppo vs hmo" (abbreviations and informal language)
- "disputing bills" (different word forms should match dispute process)

#### Should Return Partial Information

- "What medications interact badly?" (returns general drug interaction guidance)
- "How do I pay my bill?" (returns general payment options)
- "What if I miss a dose?" (returns general missed dose guidance)

#### Should Escalate (insufficient information)

These should either escalate immediately or provide general info then escalate:

- "Does my plan cover physical therapy?" (too specific to individual plan)
- "What's my deductible amount?" (requires account lookup)
- "Can Dr. Smith prescribe this medication?" (needs provider-specific information)
- "What's the copay for Dr. Johnson?" (needs account and provider details)
- "Can I get reimbursed for my visit last week?" (needs specific records)

#### Edge Cases

- "coverage" (too vague - should ask for clarification or return multiple matches)
- "I need help with everything" (unclear intent - should ask what they need)
- "When is my appointment?" (unrelated to knowledge base - should use appointment tools instead)

### Expected Behavior

- The agent should cite the source (insurance, medications, or billing) when providing information
- General information should be clearly marked as such, with a note that personal situations may differ
- When search returns results but the question is account-specific, the agent should provide the general information and then offer to escalate for personal details
- When no results are found, the agent should gracefully escalate to a human

## Evaluation

### Running Evals

The evaluation framework supports separate test suites with a CLI:

```bash
# Run all evaluations (escalation + tool_call)
uv run python src/run_evals.py run

# Run only escalation evaluation
uv run python src/run_evals.py run --eval-type escalation

# Run only tool call evaluation
uv run python src/run_evals.py run --eval-type tool_call

# Use a custom run ID
uv run python src/run_evals.py run --run-id my-test-run
```

Each evaluation will:
- Load test cases from the appropriate JSON file
- Run all tests in parallel for faster execution
- Score behavior against expectations
- Display detailed results with pass/fail summary
- Save results to run-specific directory `evals/data/<run_id>/`

### Evaluation Types

**Escalation Evaluation** (`evals/escalation_tests.json`)
- Tests when the agent escalates to humans
- Validates safety-critical behavior
- Checks controlled substance handling
- 75 test cases covering common to emergency scenarios
- Output: `escalation_results.json`, `escalation_eval.csv`

**Tool Call Evaluation** (`evals/tool_call_tests.json`)
- Tests whether correct tools are called for specific requests
- Validates all 8 available tools are used appropriately
- Checks tool selection logic and parameter handling
- 30 test cases covering all tool scenarios
- Output: `tool_call_results.json`, `tool_call_eval.csv`

### Adding Test Cases

**For escalation tests**, edit `evals/escalation_tests.json`:

```json
{
  "messages": [{"role": "user", "content": "Your test message"}],
  "should_escalate": false,
  "description": "Description of what this tests"
}
```

**For tool call tests**, edit `evals/tool_call_tests.json`:

```json
{
  "messages": [{"role": "user", "content": "Your test message"}],
  "expected_tools": ["mcp__telehealth-tools__tool_name"],
  "description": "Description of what this tests"
}
```

### Eval Framework

The evaluation framework consists of:
- `Dataset`: Contains test cases with messages and expected behavior
- `agent`: Executes the telehealth service on test messages
- `escalation_scorer`: Compares escalation behavior to expected behavior
- `tool_call_scorer`: Validates correct tools are called for each scenario

## Project Structure

```
telehealth-agent/
├── src/                     # Source code
│   ├── telehealth_service.py    # Core service with session management and tools
│   ├── telehealth_bot.py        # Interactive CLI
│   ├── knowledge_base.py        # Knowledge base documents and fuzzy search
│   └── run_evals.py             # Evaluation runner (Typer CLI)
├── evals/                   # Evaluation framework
│   ├── framework.py         # Eval framework (Dataset, scorers)
│   ├── escalation_tests.json # Test cases for escalation behavior (75 tests)
│   ├── tool_call_tests.json # Test cases for tool call validation (30 tests)
│   └── data/                # Evaluation results organized by run ID
│       └── <run_id>/        # Each evaluation run gets its own directory
│           ├── escalation_results.json
│           ├── escalation_tests.json
│           ├── escalation_eval.csv
│           ├── tool_call_results.json
│           ├── tool_call_tests.json
│           └── tool_call_eval.csv
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
- **General insurance, medication, and billing questions** (via knowledge base search)

**Escalates immediately for:**
- Specific diagnosis requests
- Serious or concerning symptoms
- Treatment plans requiring medical judgment
- New medication requests
- Controlled substances
- Prescription issues (expired, no refills, etc.)
- **Account-specific insurance, billing, or coverage questions** (requires personal records)
- Medical record access requests

