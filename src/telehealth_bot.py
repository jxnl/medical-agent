#!/usr/bin/env python3
"""
Streamlined Telehealth Chatbot CLI
Uses TelehealthService for agent logic.
"""

import asyncio
import argparse
import logging
import uuid
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.telehealth_service import TelehealthService

console = Console()

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def list_sessions(service: TelehealthService):
    """List available sessions"""
    sessions_dir = Path(service.sessions_dir)
    if not sessions_dir.exists():
        return []
    
    session_files = list(sessions_dir.glob("*.json"))
    sessions = []
    
    for session_file in session_files:
        session_id = session_file.stem
        session = service.load_session(session_id)
        sessions.append({
            "id": session_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": len(session.messages)
        })
    
    return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)


def display_session_history(session):
    """Display previous conversation history"""
    console.print(Panel(
        "[bold]Previous Conversation[/bold]",
        border_style="cyan"
    ))
    
    for msg in session.messages:
        if msg["role"] == "user":
            console.print(f"\n[bold green]You:[/bold green] {msg['content']}")
        elif msg["role"] == "assistant":
            console.print(f"\n[bold blue]Assistant:[/bold blue] {msg['content']}")


async def chat_loop(session_id: str = None):
    """Main chat loop"""
    # Initialize service
    service = TelehealthService()
    
    # Handle session selection
    if session_id:
        # Load existing session
        session = service.load_session(session_id)
        if session.messages:
            display_session_history(session)
            console.print("\n[dim]Continuing conversation...[/dim]\n")
        else:
            console.print("[yellow]Session not found, starting new conversation[/yellow]\n")
            session_id = str(uuid.uuid4())
    else:
        # Check if there are existing sessions
        sessions = list_sessions(service)
        
        if sessions:
            console.print(Panel(
                "[bold]Available Sessions[/bold]",
                border_style="cyan"
            ))
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", width=4)
            table.add_column("Session ID", width=38)
            table.add_column("Messages", width=10)
            table.add_column("Last Updated", width=25)
            
            for i, sess in enumerate(sessions[:5], 1):  # Show last 5 sessions
                table.add_row(
                    str(i),
                    sess["id"][:36],
                    str(sess["message_count"]),
                    sess["updated_at"]
                )
            
            console.print(table)
            console.print("\n[dim]Start a new conversation or use --session <id> to continue[/dim]\n")
        
        # Create new session
        session_id = str(uuid.uuid4())
    
    console.print(Panel.fit(
        "[bold cyan]Telehealth Assistant[/bold cyan]\n"
        "Hello! I'm here to help you with:\n\n"
        "- Refilling prescriptions that are already on file\n"
        "- Checking in for appointments or canceling them\n"
        "- Connecting you with healthcare providers for other needs\n\n"
        "[bold yellow]Important:[/bold yellow] For medical questions, symptoms, or health concerns, "
        "I'll connect you with a healthcare professional right away.\n\n"
        "Type 'quit' or 'exit' when you're done.",
        border_style="cyan"
    ))
    
    console.print(f"\n[dim]Session ID: {session_id}[/dim]\n")

    while True:
        # Get user input
        user_input = console.input("\n[bold green]You:[/bold green] ").strip()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            console.print(Panel(
                "Thank you for using our telehealth service. Take care!",
                title="[bold cyan]Goodbye[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            ))
            break

        if not user_input:
            continue

        try:
            # Stream message from service
            response_text = ""
            tool_calls = []
            escalated = False
            
            console.print("\n[bold blue]Assistant:[/bold blue] ", end="")
            
            async for chunk in service.stream_message(session_id, user_input):
                if chunk["type"] == "text":
                    # Print text as it streams
                    console.print(chunk["text"], end="")
                    response_text += chunk["text"]
                
                elif chunk["type"] == "tool_use":
                    tool_calls.append({
                        "name": chunk["tool_name"],
                        "input": chunk["tool_input"]
                    })
                    
                    # Check if it's an escalation
                    if chunk["tool_name"] == "mcp__telehealth-tools__escalate_to_human":
                        escalated = True
                        console.print("\n")
                        console.print(Panel(
                            "Escalating to healthcare provider",
                            title="[bold red]Escalation[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        console.print("[bold blue]Assistant:[/bold blue] ", end="")
                
                elif chunk["type"] == "done":
                    console.print("\n")
                    if not response_text:
                        console.print(Panel(
                            "I received your request but couldn't generate a response.",
                            title="[bold yellow]Assistant[/bold yellow]",
                            border_style="yellow",
                            padding=(1, 2)
                        ))

        except Exception as e:
            import traceback
            console.print(Panel(
                f"Error: {str(e)}\n\n[dim]{traceback.format_exc()}[/dim]",
                title="[bold red]Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))


async def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Telehealth Assistant CLI")
    parser.add_argument(
        "--session",
        "-s",
        type=str,
        help="Continue a previous session by providing the session ID"
    )
    parser.add_argument(
        "--list-sessions",
        "-l",
        action="store_true",
        help="List all available sessions"
    )
    
    args = parser.parse_args()
    
    if args.list_sessions:
        service = TelehealthService()
        sessions = list_sessions(service)
        
        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold magenta", title="Available Sessions")
        table.add_column("Session ID", width=40)
        table.add_column("Messages", width=10)
        table.add_column("Created", width=25)
        table.add_column("Last Updated", width=25)
        
        for sess in sessions:
            table.add_row(
                sess["id"],
                str(sess["message_count"]),
                sess["created_at"],
                sess["updated_at"]
            )
        
        console.print(table)
        console.print(f"\n[dim]Use --session <id> to continue a conversation[/dim]")
        return
    
    await chat_loop(session_id=args.session)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(Panel(
            "Goodbye!",
            title="[bold cyan]Interrupted[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))
