"""
Evaluation Framework for Telehealth Agent

Provides Dataset, function runner, and scorer components for testing agent behavior.
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Callable, Any
from src.telehealth_service import TelehealthService


@dataclass
class Dataset:
    """Dataset containing test cases for evaluation"""
    name: str
    test_cases: list[dict]  # Each test case has messages + metadata
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Dataset':
        """Create Dataset from dictionary"""
        return cls(
            name=data['name'],
            test_cases=data['test_cases']
        )


async def agent(messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
    """Run telehealth service on messages

    Args:
        messages: List of message dicts with role and content

    Returns:
        Tuple of (full conversation history including agent responses, agent version, tool_calls)
    """
    async with TelehealthService(sessions_dir=".eval_sessions") as service:
        # Process each message in sequence
        all_messages = []
        all_tool_calls = []
        for msg in messages:
            if msg["role"] == "user":
                # Add user message to history
                all_messages.append({"role": "user", "content": msg["content"]})

                # Send message and get response
                result = await service.send_message(msg["content"])

                # Add assistant response to history
                all_messages.append({
                    "role": "assistant",
                    "content": result["response"]
                })
                
                # Collect tool calls
                all_tool_calls.extend(result.get("tool_calls", []))

        return all_messages, service.version, all_tool_calls


def escalation_scorer(test_case: dict, output_messages: list[dict], tool_calls: list[dict] = None) -> float:
    """Score based on escalation behavior
    
    Args:
        test_case: Dict containing:
            - messages: input messages
            - should_escalate: expected behavior (bool)
        output_messages: Full conversation history from agent
        tool_calls: List of tool calls made (optional, not used for this scorer)
        
    Returns:
        1.0 for pass, 0.0 for fail
    """
    should_escalate = test_case.get("should_escalate", False)
    
    # Check if escalation occurred by looking for escalation in the conversation
    # We'll use a simple heuristic: check if the response contains escalation indicators
    escalated = False
    
    for msg in output_messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "").lower()
            # Look for escalation indicators in the response
            escalation_indicators = [
                "connect you with",
                "healthcare provider",
                "ticket number",
                "support ticket",
                "let me connect",
                "i'm connecting you"
            ]
            if any(indicator in content for indicator in escalation_indicators):
                escalated = True
                break
    
    # Score is 1.0 if behavior matches expectation, 0.0 otherwise
    return 1.0 if escalated == should_escalate else 0.0


def tool_call_scorer(test_case: dict, output_messages: list[dict], tool_calls: list[dict] = None) -> float:
    """Score based on whether expected tools were called
    
    Args:
        test_case: Dict containing:
            - messages: input messages
            - expected_tools: list of tool names that should be called
        output_messages: Full conversation history from agent (not used)
        tool_calls: List of tool calls made during execution
        
    Returns:
        1.0 for pass (at least one expected tool was called), 0.0 for fail
    """
    expected_tools = test_case.get("expected_tools", [])
    
    if not expected_tools:
        # If no tools are expected, pass if no tools were called
        return 1.0 if not tool_calls else 0.0
    
    if not tool_calls:
        # Expected tools but none were called
        return 0.0
    
    # Get list of tool names that were called
    called_tool_names = [call.get("name") for call in tool_calls]
    
    # Check if at least one expected tool was called
    for expected_tool in expected_tools:
        if expected_tool in called_tool_names:
            return 1.0
    
    return 0.0


async def run_eval(dataset: Dataset, 
                   function: Callable = agent,
                   scorer_fn: Callable = escalation_scorer) -> dict[str, Any]:
    """Run evaluation on a dataset in parallel
    
    Args:
        dataset: Dataset to evaluate
        function: Function to run (default: agent)
        scorer_fn: Scoring function (default: escalation_scorer)
        
    Returns:
        Dict with results:
            - total: total number of test cases
            - passed: number of passed test cases
            - failed: number of failed test cases
            - accuracy: pass rate (0.0 to 1.0)
            - results: list of individual test results
    """
    total = len(dataset.test_cases)
    
    async def run_single_test(i: int, test_case: dict):
        """Run a single test case"""
        print(f"Running test case {i+1}/{total}...")
        
        # Run the function
        result = await function(test_case["messages"])
        
        # Handle both old and new function signatures
        if isinstance(result, tuple):
            if len(result) == 3:
                output_messages, agent_version, tool_calls = result
            elif len(result) == 2:
                output_messages, agent_version = result
                tool_calls = []
            else:
                output_messages = result[0]
                agent_version = "unknown"
                tool_calls = []
        else:
            output_messages = result
            agent_version = "unknown"
            tool_calls = []
        
        # Score the output (pass tool_calls to scorer)
        score = scorer_fn(test_case, output_messages, tool_calls)
        
        # Record result
        return {
            "test_case_index": i,
            "input": test_case["messages"],
            "expected_escalation": test_case.get("should_escalate", False),
            "expected_tools": test_case.get("expected_tools", []),
            "tool_calls": tool_calls,
            "output": output_messages,
            "score": score,
            "passed": score == 1.0,
            "agent_version": agent_version
        }
    
    # Run all tests in parallel
    tasks = [
        run_single_test(i, test_case) 
        for i, test_case in enumerate(dataset.test_cases)
    ]
    results = await asyncio.gather(*tasks)
    
    # Calculate summary
    passed = sum(1 for r in results if r["passed"])
    
    # Get agent version from first result (all should be the same)
    agent_version = results[0]["agent_version"] if results else "unknown"
    
    return {
        "dataset_name": dataset.name,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": passed / total if total > 0 else 0.0,
        "agent_version": agent_version,
        "results": results
    }

