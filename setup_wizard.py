import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()

ENV_FILE = Path(".env")
ENV_TEMPLATE = {
    "GEMINI_API_KEY": {
        "description": "Required for the Main Architect Agent (Google Gemini).",
        "help_url": "https://aistudio.google.com/app/apikey"
    },
    "OPENAI_API_KEY": {
        "description": "Optional. Used for fallback or specific sub-agents.",
        "help_url": "https://platform.openai.com/api-keys"
    },
    # Add other keys your manifest needs here
}

def run_setup():
    console.print(Panel.fit("[bold cyan]NexusArbiter First-Time Setup[/bold cyan]", border_style="cyan"))
    
    if ENV_FILE.exists():
        if not Confirm.ask(f"[yellow]{ENV_FILE} already exists. Overwrite?[/yellow]"):
            console.print("[green]Setup skipped. Using existing configuration.[/green]")
            return

    new_env_content = []
    
    console.print("[dim]We need to set up your API keys to get started.[/dim]\n")

    for key, info in ENV_TEMPLATE.items():
        console.print(f"[bold]{key}[/bold]")
        console.print(f"[dim]{info['description']}[/dim]")
        console.print(f"[blue link={info['help_url']}]Get Key Here: {info['help_url']}[/blue]")
        
        value = Prompt.ask(f"Enter {key}", password=True)
        
        if value:
            new_env_content.append(f"{key}={value}")
        else:
            console.print(f"[yellow]Skipping {key} (some features may not work)[/yellow]")
            new_env_content.append(f"{key}=")
        console.print()

    # Write file
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(new_env_content))

    console.print(Panel(f"[bold green]Success![/bold green] Configuration saved to {ENV_FILE}.\n[dim]You can edit this file manually later if needed.[/dim]", border_style="green"))

if __name__ == "__main__":
    run_setup()