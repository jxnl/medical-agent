#!/usr/bin/env python3
"""
Evaluation Runner for Telehealth Agent

Loads test datasets and runs evaluations to verify agent behavior.
"""

import asyncio
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from evals.framework import Dataset, run_eval, agent, escalation_scorer, tool_call_scorer

console = Console()
app = typer.Typer()


def get_git_info():
    """Get current git branch and commit hash"""
    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        branch = branch_result.stdout.strip()
        
        # Get current commit hash
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = commit_result.stdout.strip()[:8]  # Short hash
        
        return branch, commit_hash
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"


async def run_escalation_eval(run_dir: Path, git_branch: str, git_commit: str, run_id: str) -> bool:
    """Run escalation evaluation and return True if passed"""
    console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Escalation Evaluation[/bold cyan]")
    console.print("[bold cyan]══════════════════════════════════════[/bold cyan]\n")
    
    escalation_dataset_path = Path("evals/escalation_tests.json")
    
    if not escalation_dataset_path.exists():
        console.print(f"[yellow]Skipping: {escalation_dataset_path} not found[/yellow]")
        return True
    
    with open(escalation_dataset_path) as f:
        escalation_data = json.load(f)
    
    escalation_dataset = Dataset.from_dict(escalation_data)
    
    console.print(f"[bold]Dataset:[/bold] {escalation_dataset.name}")
    console.print(f"[bold]Test Cases:[/bold] {len(escalation_dataset.test_cases)}\n")
    
    console.print("[yellow]Running evaluation...[/yellow]\n")
    results = await run_eval(
        dataset=escalation_dataset,
        function=agent,
        scorer_fn=escalation_scorer
    )
    
    # Add metadata
    results["run_id"] = run_id
    results["eval_type"] = "escalation"
    results["run_timestamp"] = datetime.now().isoformat()
    results["git_branch"] = git_branch
    results["git_commit"] = git_commit
    results["average_score"] = sum(r["score"] for r in results["results"]) / len(results["results"]) if results["results"] else 0.0
    
    # Display results
    console.print(Panel(
        f"[bold green]Passed:[/bold green] {results['passed']}/{results['total']}\n"
        f"[bold red]Failed:[/bold red] {results['failed']}/{results['total']}\n"
        f"[bold cyan]Accuracy:[/bold cyan] {results['accuracy']:.1%}\n"
        f"[bold magenta]Average Score:[/bold magenta] {results['average_score']:.3f}",
        title="[bold]Escalation Summary[/bold]",
        border_style="green" if results['accuracy'] >= 0.8 else "yellow"
    ))
    
    # Detailed results table
    table = Table(title="\nDetailed Results", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Input", width=50)
    table.add_column("Expected", width=12)
    table.add_column("Result", width=12)
    table.add_column("Status", width=8)
    
    for result in results['results']:
        test_num = result['test_case_index'] + 1
        input_text = result['input'][0]['content'][:47] + "..." if len(result['input'][0]['content']) > 50 else result['input'][0]['content']
        expected = "Escalate" if result['expected_escalation'] else "No Escalate"
        
        # Determine if escalation occurred in output
        escalated = False
        for msg in result['output']:
            if msg.get('role') == 'assistant':
                content = msg.get('content', '').lower()
                if any(ind in content for ind in ['connect you with', 'healthcare provider', 'ticket number']):
                    escalated = True
                    break
        
        actual = "Escalate" if escalated else "No Escalate"
        status = "✓" if result['passed'] else "✗"
        status_style = "green" if result['passed'] else "red"
        
        table.add_row(
            str(test_num),
            input_text,
            expected,
            actual,
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)
    
    # Show failed cases
    failed_cases = [r for r in results['results'] if not r['passed']]
    if failed_cases:
        console.print("\n[bold red]Failed Test Cases:[/bold red]\n")
        for result in failed_cases:
            test_num = result['test_case_index'] + 1
            console.print(f"[bold]Test #{test_num}:[/bold]")
            console.print(f"  Input: {result['input'][0]['content']}")
            console.print(f"  Expected: {'Escalate' if result['expected_escalation'] else 'No Escalate'}")
            
            # Show assistant response
            for msg in result['output']:
                if msg.get('role') == 'assistant':
                    console.print(f"  Response: {msg.get('content', '')[:200]}...")
                    break
            console.print()
    
    # Save results
    with open(run_dir / "escalation_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    with open(run_dir / "escalation_tests.json", 'w') as f:
        json.dump(escalation_data, f, indent=2)
    
    # Save CSV
    csv_file = run_dir / "escalation_eval.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'run_id', 'test_case_index', 'input_message', 'expected_escalation',
            'actual_escalation', 'score', 'passed'
        ])
        writer.writeheader()
        
        for result in results['results']:
            # Determine if escalation occurred
            escalated = False
            for msg in result['output']:
                if msg.get('role') == 'assistant':
                    content_lower = msg.get('content', '').lower()
                    if any(ind in content_lower for ind in ['connect you with', 'healthcare provider', 'ticket number']):
                        escalated = True
                        break
            
            writer.writerow({
                'run_id': run_id,
                'test_case_index': result['test_case_index'] + 1,
                'input_message': result['input'][0]['content'],
                'expected_escalation': result['expected_escalation'],
                'actual_escalation': escalated,
                'score': result['score'],
                'passed': result['passed']
            })
    
    console.print(f"[dim]Results saved to {run_dir}/escalation_*[/dim]")
    
    return results['accuracy'] >= 0.8


async def run_tool_call_eval(run_dir: Path, git_branch: str, git_commit: str, run_id: str) -> bool:
    """Run tool call evaluation and return True if passed"""
    console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Tool Call Evaluation[/bold cyan]")
    console.print("[bold cyan]══════════════════════════════════════[/bold cyan]\n")
    
    tool_call_dataset_path = Path("evals/tool_call_tests.json")
    
    if not tool_call_dataset_path.exists():
        console.print(f"[yellow]Skipping: {tool_call_dataset_path} not found[/yellow]")
        return True
    
    with open(tool_call_dataset_path) as f:
        tool_call_data = json.load(f)
    
    tool_call_dataset = Dataset.from_dict(tool_call_data)
    
    console.print(f"[bold]Dataset:[/bold] {tool_call_dataset.name}")
    console.print(f"[bold]Test Cases:[/bold] {len(tool_call_dataset.test_cases)}\n")
    
    console.print("[yellow]Running evaluation...[/yellow]\n")
    results = await run_eval(
        dataset=tool_call_dataset,
        function=agent,
        scorer_fn=tool_call_scorer
    )
    
    # Add metadata
    results["run_id"] = run_id
    results["eval_type"] = "tool_call"
    results["run_timestamp"] = datetime.now().isoformat()
    results["git_branch"] = git_branch
    results["git_commit"] = git_commit
    results["average_score"] = sum(r["score"] for r in results["results"]) / len(results["results"]) if results["results"] else 0.0
    
    # Display results
    console.print(Panel(
        f"[bold green]Passed:[/bold green] {results['passed']}/{results['total']}\n"
        f"[bold red]Failed:[/bold red] {results['failed']}/{results['total']}\n"
        f"[bold cyan]Accuracy:[/bold cyan] {results['accuracy']:.1%}\n"
        f"[bold magenta]Average Score:[/bold magenta] {results['average_score']:.3f}",
        title="[bold]Tool Call Summary[/bold]",
        border_style="green" if results['accuracy'] >= 0.8 else "yellow"
    ))
    
    # Detailed results table
    table = Table(title="\nDetailed Results", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Input", width=40)
    table.add_column("Expected Tool", width=30)
    table.add_column("Called Tools", width=30)
    table.add_column("Status", width=8)
    
    for result in results['results']:
        test_num = result['test_case_index'] + 1
        input_text = result['input'][0]['content'][:37] + "..." if len(result['input'][0]['content']) > 40 else result['input'][0]['content']
        
        expected_tools = result.get('expected_tools', [])
        expected_display = expected_tools[0].replace("mcp__telehealth-tools__", "") if expected_tools else "None"
        
        called_tools = result.get('tool_calls', [])
        called_display = ", ".join([t.get("name", "").replace("mcp__telehealth-tools__", "") for t in called_tools]) if called_tools else "None"
        
        status = "✓" if result['passed'] else "✗"
        status_style = "green" if result['passed'] else "red"
        
        table.add_row(
            str(test_num),
            input_text,
            expected_display,
            called_display,
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)
    
    # Show failed cases
    failed_cases = [r for r in results['results'] if not r['passed']]
    if failed_cases:
        console.print("\n[bold red]Failed Test Cases:[/bold red]\n")
        for result in failed_cases:
            test_num = result['test_case_index'] + 1
            console.print(f"[bold]Test #{test_num}:[/bold]")
            console.print(f"  Input: {result['input'][0]['content']}")
            
            expected_tools = result.get('expected_tools', [])
            console.print(f"  Expected Tools: {', '.join([t.replace('mcp__telehealth-tools__', '') for t in expected_tools])}")
            
            called_tools = result.get('tool_calls', [])
            if called_tools:
                console.print(f"  Called Tools: {', '.join([t.get('name', '').replace('mcp__telehealth-tools__', '') for t in called_tools])}")
            else:
                console.print(f"  Called Tools: None")
            
            console.print()
    
    # Save results
    with open(run_dir / "tool_call_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    with open(run_dir / "tool_call_tests.json", 'w') as f:
        json.dump(tool_call_data, f, indent=2)
    
    # Save CSV
    csv_file = run_dir / "tool_call_eval.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'run_id', 'test_case_index', 'input_message', 'expected_tools',
            'called_tools', 'score', 'passed'
        ])
        writer.writeheader()
        
        for result in results['results']:
            expected_tools = result.get('expected_tools', [])
            called_tools = result.get('tool_calls', [])
            
            writer.writerow({
                'run_id': run_id,
                'test_case_index': result['test_case_index'] + 1,
                'input_message': result['input'][0]['content'],
                'expected_tools': ', '.join(expected_tools),
                'called_tools': ', '.join([t.get('name', '') for t in called_tools]),
                'score': result['score'],
                'passed': result['passed']
            })
    
    console.print(f"[dim]Results saved to {run_dir}/tool_call_*[/dim]")
    
    return results['accuracy'] >= 0.8


@app.command()
def run(
    run_id: Optional[str] = typer.Option(None, help="Custom run ID (default: timestamp)"),
    eval_type: str = typer.Option("all", help="Evaluation type: 'escalation', 'tool_call', or 'all'")
):
    """Run evaluations (escalation, tool_call, or both)"""
    async def main():
        rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        git_branch, git_commit = get_git_info()
        
        run_dir = Path(f"evals/data/{rid}")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        eval_display = eval_type.title() if eval_type != "all" else "All"
        
        console.print(Panel(
            f"Run ID: [yellow]{rid}[/yellow]\n"
            f"Git Branch: [blue]{git_branch}[/blue]\n"
            f"Git Commit: [dim]{git_commit}[/dim]\n"
            f"Eval Type: [magenta]{eval_display}[/magenta]",
            title="[bold]Evaluation Runner[/bold]",
            border_style="cyan"
        ))
        
        results = []
        
        if eval_type in ["escalation", "all"]:
            passed = await run_escalation_eval(run_dir, git_branch, git_commit, rid)
            results.append(("escalation", passed))
        
        if eval_type in ["tool_call", "all"]:
            passed = await run_tool_call_eval(run_dir, git_branch, git_commit, rid)
            results.append(("tool_call", passed))
        
        if eval_type not in ["escalation", "tool_call", "all"]:
            console.print(f"[bold red]Error:[/bold red] Unknown eval type '{eval_type}'")
            console.print("Valid options: 'escalation', 'tool_call', 'all'")
            sys.exit(1)
        
        # Summary
        console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]  Overall Summary[/bold cyan]")
        console.print("[bold cyan]══════════════════════════════════════[/bold cyan]\n")
        
        for eval_name, passed in results:
            status = "[green]✓ PASSED[/green]" if passed else "[red]✗ FAILED[/red]"
            console.print(f"  {eval_name.title()}: {status}")
        
        all_passed = all(passed for _, passed in results)
        console.print(f"\n[dim]Results saved to {run_dir}/[/dim]")
        sys.exit(0 if all_passed else 1)
    
    asyncio.run(main())


if __name__ == "__main__":
    app()
