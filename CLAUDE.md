# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a telehealth chatbot built with the Claude Agent SDK that handles prescription refills, appointment management, and escalates complex medical issues to healthcare providers. The codebase emphasizes patient safety through strict escalation policies and comprehensive safety checks.

## Development Commands

### Running the Application

```bash
# Interactive CLI with streaming responses
uv run python telehealth_bot.py
```

### Running Tests

```bash
# Run evaluation framework on escalation behavior
uv run python run_evals.py
```

### Dependencies

```bash
# Install/sync dependencies
uv sync
```

## Architecture

### Core Components

**TelehealthService** (`telehealth_service.py`)
- Reusable service class that manages agent interactions
- Session-based conversation storage in `.sessions/` directory
- Two modes: `send_message()` for complete responses, `stream_message()` for real-time streaming
- Handles tool orchestration and conversation history persistence
- All tool definitions are in this file (7 total tools)

**CLI** (`telehealth_bot.py`)
- Thin wrapper around TelehealthService
- Provides interactive interface with streaming support
- Visual escalation indicators for user feedback

**Evaluation Framework** (`evals/framework.py`)
- `Dataset`: Loads test cases from JSON
- `run_function`: Executes agent on test messages using isolated sessions in `.eval_sessions/`
- `scorer`: Validates escalation behavior against expectations
- `run_eval`: Orchestrates full evaluation run

### Tool Categories

1. **Escalation** (1 tool): `escalate_to_human`
2. **Prescription Refills** (3 tools): `find_prescriptions`, `check_refill_eligibility`, `submit_refill_request`
3. **Appointments** (3 tools): `find_appointments`, `check_in_for_appointment`, `cancel_appointment`

## Critical Safety Logic

### Controlled Substances Detection
Located in `telehealth_service.py:18-24` - The `CONTROLLED_SUBSTANCES` set contains all DEA-scheduled medications that MUST trigger immediate escalation. This list is checked in `check_refill_eligibility` before any refill processing.

### Refill Eligibility Checks (in order)
1. Controlled substance detection - immediate escalation
2. Refills remaining > 0 - escalates if none left
3. Prescription expiration - escalates if expired
4. 80% timing rule - prevents too-soon refills (e.g., 30-day supply can refill on day 24)

### Appointment Policies
- Check-in: Only within 24 hours before appointment
- Cancellation: Must be >24 hours notice to avoid fees, otherwise escalates

## System Prompt Philosophy

Located in `telehealth_service.py:505-555` - The system prompt defines the agent's personality and escalation policy:

**Tone**: 9th-grade reading level, warm and conversational, explains "why" not just "no"

**Escalation Triggers**:
- Specific diagnosis requests or serious symptoms
- New medication requests (only refills allowed)
- Controlled substances
- Prescription issues (expired, no refills, too soon)
- Billing/insurance questions
- Anything requiring medical judgment

**Can Handle Without Escalation**:
- Common illness information (colds, minor injuries, basic self-care)
- Routine prescription refills (when eligible)
- Appointment check-in and cancellation
- General wellness questions

## Testing Strategy

### Evaluation Framework
The eval framework specifically tests escalation behavior correctness:
- Should NOT escalate: routine questions, general health info, eligible refills
- Should escalate: controlled substances, diagnosis requests, serious symptoms

### Escalation Detection
Scorer looks for indicators in responses: "connect you with", "healthcare provider", "ticket number", "support ticket", "let me connect", "i'm connecting you"

### Adding Test Cases
Edit `evals/escalation_tests.json`:
```json
{
  "messages": [{"role": "user", "content": "Your test message"}],
  "should_escalate": false,
  "description": "What this tests"
}
```

## Session Management

- Sessions auto-create on first message
- Stored as JSON in `.sessions/` (CLI) or `.eval_sessions/` (evals)
- Each session contains: session_id, messages array, created_at, updated_at
- Sessions persist across runs - conversations can be resumed

## Mock Data Reference

### Prescriptions
- **RX-001**: Lisinopril 10mg - eligible for refill (last filled 2024-09-15)
- **RX-002**: Metformin 500mg - has 0 refills remaining
- **RX-003**: Atorvastatin 20mg - too soon (last filled 2024-10-01, current date 2024-10-15)

### Appointments
- **APT-2024-1001**: Oct 18, 10:00 AM - Annual Physical with Dr. Chen
- **APT-2024-1002**: Oct 25, 2:30 PM - Follow-up with Dr. Park
- **APT-2024-1003**: Nov 5, 9:00 AM - Lab Work at LabCorp

## Key Implementation Details

### Date Validation
All date/time checks use Python's datetime module with proper timezone handling. The 80% refill rule calculation: `int(days_supply * 0.8)` gives the earliest eligible refill day.

### Streaming Implementation
`stream_message()` yields chunks as they arrive from Claude:
- `type: "text"` - text chunks to display incrementally
- `type: "tool_use"` - when tools are called
- `type: "done"` - final result with full conversation history

### Tool Return Structure
Tools return dicts with:
- `content`: array with text/resource blocks
- `requires_escalation`: bool (optional) - flags need for human handoff
- `escalation_reason`: str (optional) - why escalation needed
- `eligible`: bool (optional) - for refill eligibility checks

## Common Development Tasks

### Modifying Safety Checks
All safety logic is in `check_refill_eligibility` (lines 125-228). Add new checks as sequential if-statements before the final "eligible" return.

### Adding New Tools
1. Define tool with `@tool` decorator in `telehealth_service.py`
2. Add to `telehealth_server` tools list (line 493)
3. Add to `allowed_tools` list in both `send_message` and `stream_message` (lines 613-621 and 691-699)
4. Update system prompt if behavior changes

### Updating Escalation Policy
Modify `SYSTEM_PROMPT` in `telehealth_service.py:505-555`. Test changes by running evals to ensure no regressions in escalation behavior.

## Documentation Files

- **DESIGN.md**: Detailed design philosophy, safety checks, escalation triggers, and future enhancements
- **IMPLEMENTATION.md**: Architecture overview, component descriptions, and refactoring history
- **TESTING_GUIDE.md**: Manual testing scenarios with expected behaviors and mock data reference
- **README.md**: User-facing documentation for installation and usage
