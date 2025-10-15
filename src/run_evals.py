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
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from evals.framework import Dataset, run_eval, agent, escalation_scorer

console = Console()


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


async def main():
    """Run evaluations and display results"""
    
    # Generate run ID
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get git information
    git_branch, git_commit = get_git_info()
    
    # Load escalation dataset
    dataset_path = Path("evals/escalation_tests.json")
    
    if not dataset_path.exists():
        console.print(f"[red]Error: Dataset not found at {dataset_path}[/red]")
        sys.exit(1)
    
    console.print(Panel(
        f"Loading dataset from [cyan]{dataset_path}[/cyan]\n"
        f"Run ID: [yellow]{run_id}[/yellow]\n"
        f"Git Branch: [blue]{git_branch}[/blue]\n"
        f"Git Commit: [dim]{git_commit}[/dim]",
        title="[bold]Evaluation Runner[/bold]",
        border_style="cyan"
    ))
    
    with open(dataset_path) as f:
        dataset_data = json.load(f)
    
    escalation_dataset = Dataset.from_dict(dataset_data)
    
    console.print(f"\n[bold]Dataset:[/bold] {escalation_dataset.name}")
    console.print(f"[bold]Test Cases:[/bold] {len(escalation_dataset.test_cases)}\n")
    
    # Run evaluation with explicit function and scorer
    console.print("[yellow]Running evaluation...[/yellow]\n")
    results = await run_eval(
        dataset=escalation_dataset,
        function=agent,
        scorer_fn=escalation_scorer
    )
    
    # Add run metadata
    results["run_id"] = run_id
    results["run_timestamp"] = datetime.now().isoformat()
    results["git_branch"] = git_branch
    results["git_commit"] = git_commit
    
    # Calculate average score
    total_score = sum(r["score"] for r in results["results"])
    average_score = total_score / len(results["results"]) if results["results"] else 0.0
    results["average_score"] = average_score
    
    # Display results
    console.print("\n" + "="*80 + "\n")
    console.print(Panel(
        f"[bold yellow]Run ID:[/bold yellow] {run_id}\n"
        f"[bold blue]Agent Version:[/bold blue] {results.get('agent_version', 'unknown')}\n"
        f"[bold green]Git Branch:[/bold green] {git_branch}\n"
        f"[bold dim]Git Commit:[/bold dim] {git_commit}\n"
        f"[bold green]Passed:[/bold green] {results['passed']}/{results['total']}\n"
        f"[bold red]Failed:[/bold red] {results['failed']}/{results['total']}\n"
        f"[bold cyan]Accuracy:[/bold cyan] {results['accuracy']:.1%}\n"
        f"[bold magenta]Average Score:[/bold magenta] {results['average_score']:.3f}",
        title="[bold]Summary[/bold]",
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
    
    # Show failed cases in detail
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
    
    # Save results to JSON
    results_file = Path("evals/results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    console.print(f"\n[dim]Full results saved to {results_file}[/dim]")
    
    # Save results to CSV
    csv_file = Path(f"evals/data/escalation_eval_{run_id}.csv")
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'run_id',
            'agent_version',
            'git_branch',
            'git_commit',
            'test_case_index',
            'input_message',
            'expected_escalation',
            'actual_escalation',
            'score',
            'passed',
            'response_preview'
        ])
        writer.writeheader()
        
        for result in results['results']:
            # Determine if escalation occurred
            escalated = False
            response_text = ""
            for msg in result['output']:
                if msg.get('role') == 'assistant':
                    response_text = msg.get('content', '')
                    content_lower = response_text.lower()
                    escalation_indicators = [
                        "connect you with", "healthcare provider", 
                        "ticket number", "support ticket",
                        "let me connect", "i'm connecting you"
                    ]
                    if any(indicator in content_lower for indicator in escalation_indicators):
                        escalated = True
                    break
            
            writer.writerow({
                'run_id': run_id,
                'agent_version': result.get('agent_version', 'unknown'),
                'git_branch': git_branch,
                'git_commit': git_commit,
                'test_case_index': result['test_case_index'] + 1,
                'input_message': result['input'][0]['content'],
                'expected_escalation': result['expected_escalation'],
                'actual_escalation': escalated,
                'score': result['score'],
                'passed': result['passed'],
                'response_preview': response_text[:200] + '...' if len(response_text) > 200 else response_text
            })
    
    console.print(f"[dim]CSV results saved to {csv_file}[/dim]")
    
    # Exit with appropriate code
    sys.exit(0 if results['accuracy'] >= 0.8 else 1)


if __name__ == "__main__":
    asyncio.run(main())

