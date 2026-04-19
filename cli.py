"""Command-line interface for AgentMind.

Provides a simple CLI for running multi-agent collaborations from the terminal.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown

from agentmind import Agent, AgentMind
from agentmind.llm import OllamaProvider, LiteLLMProvider
from agentmind.utils.observability import Tracer

console = Console()
logging.basicConfig(level=logging.WARNING)


def create_llm_provider(provider: str, model: str, temperature: float):
    """Create an LLM provider."""
    if provider == "ollama":
        return OllamaProvider(model=model, temperature=temperature)
    else:
        return LiteLLMProvider(model=model, temperature=temperature)


def create_default_agents(llm_provider, num_agents: int) -> List[Agent]:
    """Create default agents for collaboration."""
    roles = [
        ("Analyst", "Analyze the problem and break it down into components"),
        ("Researcher", "Research relevant information and provide context"),
        ("Strategist", "Develop strategies and approaches to solve the problem"),
        ("Implementer", "Propose concrete implementation steps"),
        ("Reviewer", "Review solutions and provide feedback")
    ]

    agents = []
    for i in range(min(num_agents, len(roles))):
        name, role = roles[i]
        agent = Agent(name=name, role=role, llm_provider=llm_provider)
        agents.append(agent)

    return agents


@click.group()
@click.version_option(version="0.3.0")
def cli():
    """AgentMind CLI - Multi-agent collaboration framework.

    Run AI agent teams to solve complex tasks collaboratively.
    """
    pass


@cli.command()
@click.option("--task", "-t", required=True, help="Task description for agents to collaborate on")
@click.option("--agents", "-a", default=3, type=int, help="Number of agents (1-5)")
@click.option("--rounds", "-r", default=5, type=int, help="Maximum collaboration rounds")
@click.option("--provider", "-p", default="ollama", help="LLM provider (ollama, openai, anthropic)")
@click.option("--model", "-m", default="llama3.2", help="LLM model name")
@click.option("--temperature", default=0.7, type=float, help="LLM temperature (0.0-2.0)")
@click.option("--trace/--no-trace", default=True, help="Enable tracing")
@click.option("--trace-file", type=click.Path(), help="Save trace to file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(
    task: str,
    agents: int,
    rounds: int,
    provider: str,
    model: str,
    temperature: float,
    trace: bool,
    trace_file: Optional[str],
    verbose: bool
):
    """Run a multi-agent collaboration.

    Example:
        agentmind run --task "Design a REST API for a todo app" --agents 3
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Validate inputs
    if agents < 1 or agents > 5:
        console.print("[red]Error: Number of agents must be between 1 and 5[/red]")
        sys.exit(1)

    if rounds < 1 or rounds > 20:
        console.print("[red]Error: Rounds must be between 1 and 20[/red]")
        sys.exit(1)

    # Display configuration
    console.print(Panel.fit(
        f"[bold cyan]AgentMind Collaboration[/bold cyan]\n\n"
        f"Task: {task}\n"
        f"Agents: {agents}\n"
        f"Max Rounds: {rounds}\n"
        f"Provider: {provider}\n"
        f"Model: {model}",
        border_style="cyan"
    ))

    # Run collaboration
    asyncio.run(run_collaboration(
        task=task,
        num_agents=agents,
        max_rounds=rounds,
        provider=provider,
        model=model,
        temperature=temperature,
        enable_trace=trace,
        trace_file=trace_file,
        verbose=verbose
    ))


async def run_collaboration(
    task: str,
    num_agents: int,
    max_rounds: int,
    provider: str,
    model: str,
    temperature: float,
    enable_trace: bool,
    trace_file: Optional[str],
    verbose: bool
):
    """Run the collaboration asynchronously."""
    import time
    start_time = time.time()

    try:
        # Create LLM provider
        with console.status("[bold green]Initializing LLM provider..."):
            llm_provider = create_llm_provider(provider, model, temperature)

        # Create AgentMind
        mind = AgentMind(llm_provider=llm_provider)

        # Create agents
        console.print("\n[bold]Creating agents:[/bold]")
        agent_list = create_default_agents(llm_provider, num_agents)
        for agent in agent_list:
            mind.add_agent(agent)
            console.print(f"  ✓ {agent.name} ({agent.role})")

        # Create tracer if enabled
        tracer = None
        if enable_trace:
            import uuid
            session_id = str(uuid.uuid4())[:8]
            tracer = Tracer(session_id=session_id, metadata={"task": task})
            tracer.start()

        # Run collaboration with progress indicator
        console.print("\n[bold green]Starting collaboration...[/bold green]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task_id = progress.add_task("Collaborating...", total=None)

            result = await mind.collaborate(task=task, max_rounds=max_rounds)

            progress.update(task_id, completed=True)

        # End tracing
        if tracer:
            tracer.end()

        # Calculate duration
        duration = time.time() - start_time

        # Display result
        console.print("\n" + "=" * 80 + "\n")
        console.print(Panel(
            Markdown(result),
            title="[bold green]Collaboration Result[/bold green]",
            border_style="green"
        ))

        # Display statistics
        console.print("\n[bold]Statistics:[/bold]")
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("Duration", f"{duration:.2f}s")
        stats_table.add_row("Rounds", str(len(mind.conversation_history) // num_agents))
        stats_table.add_row("Messages", str(len(mind.conversation_history)))

        if tracer:
            summary = tracer.get_summary()
            token_usage = summary.get("token_usage", {})
            cost_estimate = summary.get("cost_estimate", {})

            if token_usage.get("total_tokens"):
                stats_table.add_row("Total Tokens", str(token_usage["total_tokens"]))

            if cost_estimate.get("total_cost"):
                stats_table.add_row("Estimated Cost", f"${cost_estimate['total_cost']:.4f}")

        console.print(stats_table)

        # Save trace if requested
        if tracer and trace_file:
            tracer.save_jsonl(trace_file)
            console.print(f"\n[green]✓ Trace saved to {trace_file}[/green]")

        # Display conversation history if verbose
        if verbose:
            console.print("\n[bold]Conversation History:[/bold]")
            for i, msg in enumerate(mind.conversation_history, 1):
                console.print(f"\n[cyan]{i}. {msg.sender}:[/cyan]")
                console.print(f"   {msg.content[:200]}...")

    except KeyboardInterrupt:
        console.print("\n[yellow]Collaboration interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("trace_file", type=click.Path(exists=True))
def analyze(trace_file: str):
    """Analyze a trace file and display statistics.

    Example:
        agentmind analyze traces/session-abc123.jsonl
    """
    try:
        # Load trace file
        events = []
        metadata = {}

        with open(trace_file, "r") as f:
            for line in f:
                data = json.loads(line)
                if data["type"] == "header":
                    metadata = data["data"]
                elif data["type"] == "event":
                    events.append(data["data"])

        # Display metadata
        console.print(Panel.fit(
            f"[bold cyan]Trace Analysis[/bold cyan]\n\n"
            f"Session ID: {metadata.get('session_id', 'N/A')}\n"
            f"Start Time: {metadata.get('start_time', 'N/A')}\n"
            f"Duration: {metadata.get('total_duration_ms', 0) / 1000:.2f}s",
            border_style="cyan"
        ))

        # Event statistics
        console.print("\n[bold]Event Statistics:[/bold]")
        event_types = {}
        agent_events = {}

        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

            agent_name = event.get("agent_name")
            if agent_name:
                agent_events[agent_name] = agent_events.get(agent_name, 0) + 1

        # Event types table
        events_table = Table(title="Events by Type")
        events_table.add_column("Event Type", style="cyan")
        events_table.add_column("Count", style="white", justify="right")

        for event_type, count in sorted(event_types.items()):
            events_table.add_row(event_type, str(count))

        console.print(events_table)

        # Agent activity table
        if agent_events:
            console.print("\n[bold]Agent Activity:[/bold]")
            agents_table = Table(title="Events by Agent")
            agents_table.add_column("Agent", style="cyan")
            agents_table.add_column("Events", style="white", justify="right")

            for agent, count in sorted(agent_events.items()):
                agents_table.add_row(agent, str(count))

            console.print(agents_table)

        # Token usage and cost
        token_usage = metadata.get("token_usage", {})
        cost_estimate = metadata.get("cost_estimate", {})

        if token_usage or cost_estimate:
            console.print("\n[bold]Resource Usage:[/bold]")
            usage_table = Table(show_header=False, box=None)
            usage_table.add_column("Metric", style="cyan")
            usage_table.add_column("Value", style="white")

            if token_usage.get("total_tokens"):
                usage_table.add_row("Total Tokens", str(token_usage["total_tokens"]))
                usage_table.add_row("Prompt Tokens", str(token_usage.get("prompt_tokens", 0)))
                usage_table.add_row("Completion Tokens", str(token_usage.get("completion_tokens", 0)))

            if cost_estimate.get("total_cost"):
                usage_table.add_row("Estimated Cost", f"${cost_estimate['total_cost']:.4f}")

            console.print(usage_table)

    except Exception as e:
        console.print(f"[red]Error analyzing trace: {e}[/red]")
        sys.exit(1)


@cli.command()
def examples():
    """Show example commands and use cases."""
    examples_text = """
# AgentMind CLI Examples

## Basic Usage

Run a simple collaboration with 3 agents:
```bash
agentmind run --task "Design a REST API for a todo app" --agents 3
```

## Custom Configuration

Use a specific model and provider:
```bash
agentmind run --task "Analyze this codebase" --provider openai --model gpt-4 --agents 4
```

## With Tracing

Save trace for later analysis:
```bash
agentmind run --task "Plan a marketing campaign" --trace-file traces/campaign.jsonl
```

## Analyze Traces

View statistics from a previous collaboration:
```bash
agentmind analyze traces/campaign.jsonl
```

## Verbose Mode

See detailed conversation history:
```bash
agentmind run --task "Debug this error" --verbose
```

## Advanced

More agents and rounds for complex tasks:
```bash
agentmind run --task "Design a distributed system" --agents 5 --rounds 10
```
    """

    console.print(Markdown(examples_text))


@cli.command()
def version():
    """Show version information."""
    console.print("[bold cyan]AgentMind CLI[/bold cyan]")
    console.print("Version: 0.3.0")
    console.print("Framework: AgentMind")
    console.print("\nFor more information, visit: https://github.com/cym3118288-afk/AgentMind-Framework")


if __name__ == "__main__":
    cli()
