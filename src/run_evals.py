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
from evals.framework import Dataset, run_eval, agent, escalation_scorer

console = Console()
app = typer.Typer()


def search_scorer(test_case: dict, output_messages: list[dict]) -> float:
    """
    Score search behavior based on whether the agent:
    1. Uses search_knowledge_base tool when appropriate
    2. Returns results when they exist
    3. Escalates when information is insufficient
    """
    expected_behavior = test_case.get("expected_behavior", "should_search")
    should_find_results = test_case.get("should_find_results", True)
    should_escalate = test_case.get("should_escalate", False)
    
    # Check if search was used
    used_search = False
    found_results = False
    escalated = False
    
    for msg in output_messages:
        content = str(msg.get('content', '')).lower()
        
        # Check for search tool use
        if 'search_knowledge_base' in content or 'found information about' in content:
            used_search = True
            if 'found information about' in content or 'i found' in content:
                found_results = True
        
        # Check for escalation indicators
        if any(ind in content for ind in [
            'connect you with', 'healthcare provider', 'ticket number',
            'support ticket', 'let me connect', "i'm connecting you"
        ]):
            escalated = True
    
    # Determine if behavior matches expectations
    if expected_behavior == "should_search":
        # Should use search and find results, no escalation needed
        if used_search and found_results == should_find_results and not escalated:
            return 1.0
        elif used_search and found_results:
            # Found something but maybe escalated unnecessarily
            return 0.8 if not should_escalate else 0.5
        else:
            return 0.0
    
    elif expected_behavior == "should_search_and_escalate":
        # May search but should eventually escalate
        if escalated:
            return 1.0
        else:
            return 0.0
    
    elif expected_behavior == "should_escalate":
        # Should escalate directly or after finding insufficient info
        if escalated:
            return 1.0
        else:
            return 0.0
    
    elif expected_behavior == "should_search_ambiguous":
        # Should search, may ask for clarification
        if used_search:
            return 1.0
        else:
            return 0.5
    
    elif expected_behavior == "should_clarify":
        # Should ask for clarification
        if not escalated and not found_results:
            return 1.0
        else:
            return 0.5
    
    # Default: partial credit if used search appropriately
    return 0.5 if used_search else 0.0


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


async def run_search_eval(run_dir: Path, git_branch: str, git_commit: str, run_id: str) -> bool:
    """Run search evaluation and return True if passed"""
    console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Search Knowledge Base Evaluation[/bold cyan]")
    console.print("[bold cyan]══════════════════════════════════════[/bold cyan]\n")
    
    search_dataset_path = Path("evals/search_tests.json")
    
    if not search_dataset_path.exists():
        console.print(f"[yellow]Skipping: {search_dataset_path} not found[/yellow]")
        return True
    
    with open(search_dataset_path) as f:
        search_data = json.load(f)
    
    search_dataset = Dataset(
        name="Search Knowledge Base Tests",
        test_cases=search_data
    )
    
    console.print(f"[bold]Dataset:[/bold] {search_dataset.name}")
    console.print(f"[bold]Test Cases:[/bold] {len(search_dataset.test_cases)}\n")
    
    console.print("[yellow]Running evaluation...[/yellow]\n")
    results = await run_eval(
        dataset=search_dataset,
        function=agent,
        scorer_fn=search_scorer
    )
    
    # Add metadata
    results["run_id"] = run_id
    results["eval_type"] = "search"
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
        title="[bold]Search Summary[/bold]",
        border_style="green" if results['accuracy'] >= 0.8 else "yellow"
    ))
    
    # Detailed table
    table = Table(title="\nSearch Test Details", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Query", width=40)
    table.add_column("Expected Behavior", width=20)
    table.add_column("Score", width=8)
    table.add_column("Status", width=8)
    
    for result in results['results']:
        test_num = result['test_case_index'] + 1
        query = result['input'][0]['content'][:37] + "..." if len(result['input'][0]['content']) > 40 else result['input'][0]['content']
        test_case = search_data[result['test_case_index']]
        expected = test_case.get('expected_behavior', 'should_search')
        
        score = result['score']
        status = "✓" if result['passed'] else "✗"
        status_style = "green" if result['passed'] else "red"
        
        table.add_row(
            str(test_num),
            query,
            expected.replace('_', ' '),
            f"{score:.2f}",
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)
    
    # Show failed cases
    failed_cases = [r for r in results['results'] if not r['passed']]
    if failed_cases:
        console.print("\n[bold red]Failed Search Test Cases:[/bold red]\n")
        for result in failed_cases:
            test_num = result['test_case_index'] + 1
            test_case = search_data[result['test_case_index']]
            console.print(f"[bold]Test #{test_num}:[/bold] {test_case.get('description', '')}")
            console.print(f"  Query: {result['input'][0]['content']}")
            console.print(f"  Expected: {test_case.get('expected_behavior', 'should_search')}")
            console.print(f"  Score: {result['score']:.2f}")
            console.print()
    
    # Save results
    with open(run_dir / "search_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    with open(run_dir / "search_tests.json", 'w') as f:
        json.dump(search_data, f, indent=2)
    
    # Save CSV
    csv_file = run_dir / "search_eval.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'run_id', 'test_case_index', 'query', 'expected_behavior',
            'should_find_results', 'should_escalate', 'score', 'passed', 'description'
        ])
        writer.writeheader()
        
        for result in results['results']:
            test_case = search_data[result['test_case_index']]
            writer.writerow({
                'run_id': run_id,
                'test_case_index': result['test_case_index'] + 1,
                'query': result['input'][0]['content'],
                'expected_behavior': test_case.get('expected_behavior', 'should_search'),
                'should_find_results': test_case.get('should_find_results', True),
                'should_escalate': test_case.get('should_escalate', False),
                'score': result['score'],
                'passed': result['passed'],
                'description': test_case.get('description', '')
            })
    
    console.print(f"[dim]Results saved to {run_dir}/search_*[/dim]")
    
    return results['accuracy'] >= 0.8


@app.command()
def escalation(
    run_id: Optional[str] = typer.Option(None, help="Custom run ID (default: timestamp)")
):
    """Run only the escalation evaluation"""
    async def main():
        rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        git_branch, git_commit = get_git_info()
        
        run_dir = Path(f"evals/data/{rid}")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(Panel(
            f"Run ID: [yellow]{rid}[/yellow]\n"
            f"Git Branch: [blue]{git_branch}[/blue]\n"
            f"Git Commit: [dim]{git_commit}[/dim]\n"
            f"Eval Type: [magenta]Escalation Only[/magenta]",
            title="[bold]Evaluation Runner[/bold]",
            border_style="cyan"
        ))
        
        passed = await run_escalation_eval(run_dir, git_branch, git_commit, rid)
        
        console.print(f"\n[dim]Results saved to {run_dir}/[/dim]")
        sys.exit(0 if passed else 1)
    
    asyncio.run(main())


@app.command()
def search(
    run_id: Optional[str] = typer.Option(None, help="Custom run ID (default: timestamp)")
):
    """Run only the search knowledge base evaluation"""
    async def main():
        rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        git_branch, git_commit = get_git_info()
        
        run_dir = Path(f"evals/data/{rid}")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(Panel(
            f"Run ID: [yellow]{rid}[/yellow]\n"
            f"Git Branch: [blue]{git_branch}[/blue]\n"
            f"Git Commit: [dim]{git_commit}[/dim]\n"
            f"Eval Type: [magenta]Search Only[/magenta]",
            title="[bold]Evaluation Runner[/bold]",
            border_style="cyan"
        ))
        
        passed = await run_search_eval(run_dir, git_branch, git_commit, rid)
        
        console.print(f"\n[dim]Results saved to {run_dir}/[/dim]")
        sys.exit(0 if passed else 1)
    
    asyncio.run(main())


@app.command()
def all(
    run_id: Optional[str] = typer.Option(None, help="Custom run ID (default: timestamp)")
):
    """Run all evaluations (escalation and search)"""
    async def main():
        rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        git_branch, git_commit = get_git_info()
        
        run_dir = Path(f"evals/data/{rid}")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(Panel(
            f"Run ID: [yellow]{rid}[/yellow]\n"
            f"Git Branch: [blue]{git_branch}[/blue]\n"
            f"Git Commit: [dim]{git_commit}[/dim]\n"
            f"Eval Type: [magenta]All Evaluations[/magenta]",
            title="[bold]Evaluation Runner[/bold]",
            border_style="cyan"
        ))
        
        escalation_passed = await run_escalation_eval(run_dir, git_branch, git_commit, rid)
        search_passed = await run_search_eval(run_dir, git_branch, git_commit, rid)
        
        all_passed = escalation_passed and search_passed
        
        console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
        console.print(f"[dim]All results saved to {run_dir}/[/dim]")
        
        sys.exit(0 if all_passed else 1)
    
    asyncio.run(main())


if __name__ == "__main__":
    app()
