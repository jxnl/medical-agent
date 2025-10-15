# New Features

## Session Management

### CLI Session Support
The CLI now supports session persistence and resumption:

```bash
# Start new conversation (shows recent sessions if available)
uv run python telehealth_bot.py

# List all sessions
uv run python telehealth_bot.py --list-sessions

# Continue a specific session
uv run python telehealth_bot.py --session <session-id>
```

### How It Works
- **Auto-save**: Every conversation is automatically saved to `.sessions/<session-id>.json`
- **Session history**: When loading a session, previous messages are displayed
- **Recent sessions**: Starting a new chat shows your 5 most recent sessions
- **Session metadata**: Tracks creation time, last update, and message count

### Session Structure
```json
{
  "session_id": "abc123...",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "created_at": "2024-10-15T10:30:00",
  "updated_at": "2024-10-15T10:35:00"
}
```

## Parallel Evaluation

### Performance Improvements
Evals now run in parallel using `asyncio.gather`:

```python
# Old: Sequential execution
for test_case in dataset.test_cases:
    result = await run_function(test_case)
    
# New: Parallel execution
tasks = [run_single_test(i, tc) for i, tc in enumerate(test_cases)]
results = await asyncio.gather(*tasks)
```

**Benefits:**
- Faster eval runs (15 test cases now run concurrently)
- Better resource utilization
- Same accuracy, less waiting

### Explicit Naming
The eval framework now uses explicit, descriptive names:

- **escalation_dataset**: Clear that this tests escalation behavior
- **agent**: The function that runs the telehealth service
- **escalation_scorer**: Specifically scores escalation behavior

```python
# Usage in run_evals.py
results = await run_eval(
    dataset=escalation_dataset,
    function=agent,
    scorer_fn=escalation_scorer
)
```

## CSV Export

### Timestamped Results
Eval results are now saved to CSV in addition to JSON:

```
evals/data/escalation_eval_20251015_115619.csv
```

### CSV Format
```csv
test_case_index,input_message,expected_escalation,actual_escalation,score,passed,response_preview
1,I have a cold what should I do,False,False,1.0,True,"I can help you with that! Colds are..."
2,I need a new prescription for Adderall,True,True,1.0,True,"I understand you need..."
```

**Fields:**
- `test_case_index`: Test number (1-based)
- `input_message`: The user's question
- `expected_escalation`: Should the agent escalate? (True/False)
- `actual_escalation`: Did the agent escalate? (True/False)
- `score`: 1.0 for pass, 0.0 for fail
- `passed`: Boolean pass/fail
- `response_preview`: First 200 chars of response

### Benefits
- Easy to analyze in Excel/Google Sheets
- Track performance over time
- Compare different model versions
- Share results with non-technical stakeholders

## Streaming Responses

### Real-time Output
The CLI now streams responses as they're generated:

```python
async for chunk in service.stream_message(session_id, user_input):
    if chunk["type"] == "text":
        console.print(chunk["text"], end="")
    elif chunk["type"] == "tool_use":
        # Handle tool calls
    elif chunk["type"] == "done":
        # Conversation complete
```

**User Experience:**
- Text appears immediately as it's generated
- No more waiting for complete response
- Visual feedback that agent is working
- Natural conversation flow

## File Organization

### New Directories
```
evals/
├── data/                    # CSV results (gitignored)
│   └── escalation_eval_*.csv
├── framework.py             # Eval components
└── escalation_tests.json    # Test cases

.sessions/                   # Session storage (gitignored)
└── <session-id>.json

.eval_sessions/              # Eval sessions (gitignored)
└── <session-id>.json
```

### Updated .gitignore
```
# Session directories
.sessions/
.eval_sessions/

# Eval results
evals/results.json
evals/data/*.csv
```

## Summary of Changes

### telehealth_bot.py
- ✅ Added `--session` flag to continue conversations
- ✅ Added `--list-sessions` flag to view all sessions
- ✅ Display session history when loading
- ✅ Show recent sessions on startup
- ✅ Streaming response display

### run_evals.py
- ✅ Explicit naming: `escalation_dataset`, `agent`, `escalation_scorer`
- ✅ CSV export with timestamp
- ✅ Parallel test execution

### evals/framework.py
- ✅ Renamed `run_function` → `agent`
- ✅ Renamed `scorer` → `escalation_scorer`
- ✅ Parallel test execution with `asyncio.gather`

### telehealth_service.py
- ✅ Session persistence to disk
- ✅ Streaming support via `stream_message()`
- ✅ Both streaming and non-streaming modes

## Usage Examples

### Start a conversation
```bash
uv run python telehealth_bot.py
```

### Continue where you left off
```bash
# List sessions
uv run python telehealth_bot.py -l

# Continue specific session
uv run python telehealth_bot.py -s abc123-def456-...
```

### Run evals
```bash
uv run python run_evals.py
# Results saved to:
# - evals/results.json
# - evals/data/escalation_eval_<timestamp>.csv
```

### Use service programmatically
```python
from telehealth_service import TelehealthService

service = TelehealthService()

# Stream responses
async for chunk in service.stream_message(session_id, "I have a cold"):
    if chunk["type"] == "text":
        print(chunk["text"], end="")
```

