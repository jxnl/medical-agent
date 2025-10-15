#!/usr/bin/env python3
"""
Streamlined Telehealth Chatbot CLI
Uses TelehealthService for agent logic.
"""

import asyncio
import json
import logging
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON
from rich.text import Text
from rich.markdown import Markdown
from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from src.telehealth_service import TelehealthService

console = Console()
app = typer.Typer()

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def chat_loop(prefilled_message: Optional[str] = None):
    """Main chat loop"""
    # Beautiful welcome screen
    welcome_text = Text()
    welcome_text.append("🏥 ", style="bold cyan")
    welcome_text.append("Telehealth Assistant", style="bold cyan")
    
    console.print()
    console.print(Align.center(welcome_text))
    console.print()
    
    # Features panel
    features = Panel(
        "[bold]I can help you with:[/bold]\n\n"
        "💊 Refilling prescriptions that are already on file\n"
        "📅 Checking in for appointments or canceling them\n"
        "🏥 Connecting you with healthcare providers\n"
        "❓ Answering general health questions",
        title="[bold green]Services[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    
    # Important notice
    notice = Panel(
        "[bold yellow]⚠️  Important:[/bold yellow] For medical questions, symptoms, or health concerns, "
        "I'll connect you with a healthcare professional right away.",
        border_style="yellow",
        padding=(1, 2)
    )
    
    console.print(features)
    console.print(notice)
    console.print()
    console.print("[dim]Type 'quit' or 'exit' when you're done.[/dim]")
    console.print()
    
    async with TelehealthService() as service:
        while True:
            # Get user input
            if prefilled_message:
                user_input = prefilled_message
                console.print(f"\n[bold green]You:[/bold green] {user_input}")
                prefilled_message = None  # Only use prefilled message once
            else:
                user_input = console.input("\n[bold green]You:[/bold green] ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                goodbye_text = Text()
                goodbye_text.append("👋 ", style="bold cyan")
                goodbye_text.append("Thank you for using our telehealth service!", style="bold cyan")
                console.print()
                console.print(Align.center(goodbye_text))
                console.print(Align.center("[dim]Take care and stay healthy![/dim]"))
                console.print()
                break

            if not user_input:
                continue

            try:
                # Stream message from service
                response_text = ""
                tool_calls = []
                escalated = False
                live_display = None
                
                # Show thinking message with spinner
                thinking_text = Text()
                thinking_text.append("🤔 ", style="dim")
                thinking_text.append("Thinking...", style="dim italic")
                console.print(thinking_text)
                
                try:
                    async for chunk in service.stream_message(user_input):
                        if chunk["type"] == "text":
                            # Add text to response
                            response_text += chunk["text"]
                            
                            # Create or update live panel
                            if live_display is None:
                                console.print()  # Add spacing
                                live_display = Live(
                                    Panel(
                                        response_text,
                                        title="[bold blue]🤖 Assistant[/bold blue]",
                                        border_style="blue",
                                        padding=(1, 2)
                                    ),
                                    console=console,
                                    refresh_per_second=20
                                )
                                live_display.start()
                            else:
                                live_display.update(
                                    Panel(
                                        response_text,
                                        title="[bold blue]🤖 Assistant[/bold blue]",
                                        border_style="blue",
                                        padding=(1, 2)
                                    )
                                )
                        
                        elif chunk["type"] == "tool_use":
                            # Stop live display before showing tool execution
                            if live_display is not None:
                                live_display.stop()
                                live_display = None
                            
                            tool_calls.append({
                                "name": chunk["tool_name"],
                                "input": chunk["tool_input"]
                            })
                            
                            # Display tool call info with pretty formatting
                            tool_name = chunk["tool_name"].replace("mcp__telehealth-tools__", "")
                            tool_input = chunk["tool_input"]
                            
                            # Create a beautiful tool call panel
                            is_escalation = chunk["tool_name"] == "mcp__telehealth-tools__escalate_to_human"
                            
                            if is_escalation:
                                tool_panel_content = f"[bold red]🚨 Tool:[/bold red] {tool_name}\n"
                                if tool_input:
                                    tool_panel_content += "[bold red]📋 Parameters:[/bold red]\n"
                                    for key, value in tool_input.items():
                                        if isinstance(value, (dict, list)):
                                            json_str = json.dumps(value, indent=2)
                                            tool_panel_content += f"  [dim]• {key}:[/dim] {json_str}\n"
                                        else:
                                            tool_panel_content += f"  [dim]• {key}:[/dim] {value}\n"
                                
                                tool_panel = Panel(
                                    tool_panel_content.strip(),
                                    title="[bold red]⚠️ Escalation Tool[/bold red]",
                                    border_style="red",
                                    padding=(0, 1)
                                )
                            else:
                                tool_panel_content = f"[bold cyan]🔧 Tool:[/bold cyan] {tool_name}\n"
                                
                                if tool_input:
                                    tool_panel_content += "[bold cyan]📋 Parameters:[/bold cyan]\n"
                                    for key, value in tool_input.items():
                                        if isinstance(value, (dict, list)):
                                            json_str = json.dumps(value, indent=2)
                                            tool_panel_content += f"  [dim]• {key}:[/dim] {json_str}\n"
                                        else:
                                            tool_panel_content += f"  [dim]• {key}:[/dim] {value}\n"
                                
                                tool_panel = Panel(
                                    tool_panel_content.strip(),
                                    title="[bold cyan]Tool Execution[/bold cyan]",
                                    border_style="cyan",
                                    padding=(0, 1)
                                )
                            console.print(tool_panel)
                        
                        elif chunk["type"] == "tool_result":
                            # Display tool response
                            tool_name = chunk["tool_name"].replace("mcp__telehealth-tools__", "")
                            tool_result = chunk["tool_result"]
                            is_escalation = chunk["tool_name"] == "mcp__telehealth-tools__escalate_to_human"

                            console.print(f"Tool result: {tool_result}")
                            
                            # Format tool result content
                            result_content = ""
                            if isinstance(tool_result, list):
                                for item in tool_result:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        result_content += item.get("text", "")
                                    else:
                                        result_content += str(item)
                            else:
                                result_content = str(tool_result)
                            
                            if is_escalation:
                                result_panel = Panel(
                                    f"[bold red]🚨 Escalation Response:[/bold red]\n\n{result_content}",
                                    title=f"[bold red]⚠️ {tool_name} Result[/bold red]",
                                    border_style="red",
                                    padding=(0, 1)
                                )
                            else:
                                result_panel = Panel(
                                    f"[bold green]✅ Tool Response:[/bold green]\n\n{result_content}",
                                    title=f"[bold green]📋 {tool_name} Result[/bold green]",
                                    border_style="green",
                                    padding=(0, 1)
                                )
                            console.print(result_panel)
                            
                            # Check if it's an escalation
                            if chunk["tool_name"] == "mcp__telehealth-tools__escalate_to_human":
                                escalated = True
                                # Stop live display before showing escalation
                                if live_display is not None:
                                    live_display.stop()
                                    live_display = None
                                console.print()
                                escalation_panel = Panel(
                                    "🚨 [bold red]Escalating to healthcare provider[/bold red]\n\n"
                                    "A healthcare professional will be with you shortly.",
                                    title="[bold red]⚠️ Escalation[/bold red]",
                                    border_style="red",
                                    padding=(1, 2)
                                )
                                console.print(escalation_panel)
                        
                        elif chunk["type"] == "done":
                            # Stop live display if active
                            if live_display is not None:
                                live_display.stop()
                            
                            console.print()
                            
                            if not response_text:
                                error_panel = Panel(
                                    "😕 [bold yellow]I received your request but couldn't generate a response.[/bold yellow]\n\n"
                                    "Please try rephrasing your question or contact support if the issue persists.",
                                    title="[bold yellow]⚠️ Error[/bold yellow]",
                                    border_style="yellow",
                                    padding=(1, 2)
                                )
                                console.print(error_panel)
                
                except (KeyboardInterrupt, Exception) as e:
                    # Clean up live display on interrupt or error
                    if live_display is not None:
                        live_display.stop()
                    
                    # Re-raise KeyboardInterrupt to handle it at the outer level
                    if isinstance(e, KeyboardInterrupt):
                        raise

            except Exception as e:
                import traceback
                error_panel = Panel(
                    f"🚨 [bold red]An error occurred:[/bold red] {str(e)}\n\n"
                    f"[dim]Technical details:[/dim]\n{traceback.format_exc()}",
                    title="[bold red]❌ Error[/bold red]",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)


@app.command()
def chat(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    prefilled_message: Optional[str] = typer.Option(None, "--prefill", "-p", help="Prefill chat with this message")
):
    """Start the telehealth chatbot interactive session"""
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    try:
        asyncio.run(chat_loop(prefilled_message))
    except KeyboardInterrupt:
        console.print(Panel(
            "Goodbye!",
            title="[bold cyan]Interrupted[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))


@app.command()
def version():
    """Show version information"""
    console.print("Telehealth Bot v0.1.0")


if __name__ == "__main__":
    app()
