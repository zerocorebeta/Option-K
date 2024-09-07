import os
import asyncio
import aiohttp
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer
import aiofiles
import configparser
# Initialize the console
console = Console()

# Command history file
HISTORY_FILE = os.path.expanduser('~/.optionk/history')

config = configparser.ConfigParser()
config.read(os.path.expanduser('~/.optionk/config.ini'))

PORT = config.get('optionk', 'port')

async def save_to_history(command):
    try:
        async with aiofiles.open(HISTORY_FILE, 'a') as f:
            await f.write(f"{command}\n")
    except ImportError:
        # Fallback to synchronous file writing if aiofiles is not available
        with open(HISTORY_FILE, 'a') as f:
            f.write(f"{command}\n")

async def load_history():
    try:
        async with aiofiles.open(HISTORY_FILE, 'r') as f:
            return [line.strip() for line in await f.readlines()]
    except FileNotFoundError:
        return []

async def run_command(command):
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode()
        else:
            return f"Error: {stderr.decode()}"
    except Exception as e:
        return f"Error: {str(e)}"

def apply_color_scheme_html(command):
    parts = command.split()
    colored_parts = []
    for i, part in enumerate(parts):
        if i == 0:
            colored_parts.append(f'<cmd>{part}</cmd>')
        elif part.startswith('-'):
            colored_parts.append(f'<arg>{part}</arg>')
        else:
            colored_parts.append(f'<param>{part}</param>')
    return ' '.join(colored_parts)

async def main():
    parser = argparse.ArgumentParser(description="AI Coding Assistant CLI")
    parser.add_argument("query", nargs="*", help="The task or query to generate a command for")
    parser.add_argument("--quick", action="store_true", help="Get a single best result")
    args = parser.parse_args()

    user_input = " ".join(args.query)

    async with aiohttp.ClientSession() as session:
        if args.quick:
            async with session.post(f'http://localhost:{PORT}/quick_suggest', json={'query': user_input}) as response:
                data = await response.json()
                print(data['result'])
            return

        try:
            while True:
                if not user_input:
                    user_input = console.input(
                        "[bold green]Query?[/bold green] (or 'q' to quit) "
                    )
                    if user_input.lower() in ['exit', 'quit', 'q']:
                        console.print("\n[bold yellow]Exiting...[/bold yellow]")
                        return

                with console.status("[bold blue]Generating response...[/bold blue]"):
                    async with session.post(f'http://localhost:{PORT}/generate', json={'query': user_input}) as response:
                        data = await response.json()
                        response_text = data['response']

                commands = []
                for line in response_text.splitlines():
                    if line.startswith(tuple(f"{i}." for i in range(1, 10))):
                        parts = line.split(' - ', 1)
                        if len(parts) == 2:
                            cmd, explanation = parts
                        else:
                            cmd, explanation = parts[0], ""
                        commands.append((cmd.strip(), explanation.strip()))
                
                commands = commands[:10]  # Limit to 10 commands (0-9)
                
                while commands:
                    table = Table(title="Generated Commands", show_header=True, header_style="bold magenta", expand=True)
                    table.add_column("#", style="dim", width=4, justify="center")
                    table.add_column("Command", style="cyan", no_wrap=True, ratio=30)
                    table.add_column("Explanation", style="green", ratio=70)
                    
                    for i, (cmd, explanation) in enumerate(commands):
                        cmd_parts = cmd.split(None, 1)[1].strip('`*').split()
                        
                        colored_cmd = Text()
                        for j, part in enumerate(cmd_parts):
                            if j == 0:
                                colored_cmd.append(part, style="bold cyan")
                            elif part.startswith('-'):
                                colored_cmd.append(f" {part}", style="yellow")
                            else:
                                colored_cmd.append(f" {part}", style="green")
                        
                        table.add_row(str(i), colored_cmd, Text(explanation, style="green"))
                    
                    console.print(table)

                    kb = KeyBindings()

                    def handle_input(event):
                        char = event.data
                        if char in [str(i) for i in range(10)] + ['n', 'q']:
                            event.app.exit(result=char)

                    for i in range(10):
                        kb.add(str(i))(handle_input)
                    kb.add('n')(handle_input)
                    kb.add('q')(handle_input)

                    buffer = Buffer()
                    text_area = TextArea()
                    application = Application(
                        layout=Layout(Window(BufferControl(buffer=buffer))),
                        key_bindings=kb,
                        full_screen=False,
                    )

                    console.print("Select a command number (0-9), 'n' for a new query, or 'q' to quit: ", end="")
                    choice = await asyncio.to_thread(application.run)

                    if choice == 'q':
                        console.print("\n[bold yellow]Exiting...[/bold yellow]")
                        return
                    elif choice == 'n':
                        console.print()
                        break
                    elif choice in [str(i) for i in range(10)]:
                        command_index = int(choice)
                        if 0 <= command_index < len(commands):
                            command_to_execute = commands[command_index][0].split(None, 1)[1].strip('`*')
                            
                            console.print("[italic]Edit the command or press Enter to execute. Use Ctrl+C to cancel.[/italic]")

                            colored_command = apply_color_scheme_html(command_to_execute)
                            
                            edit_session = PromptSession(
                                history=InMemoryHistory([command_to_execute]),
                                auto_suggest=AutoSuggestFromHistory(),
                                style=Style.from_dict({
                                    'prompt': '#00FFFF bold',
                                    'cmd': '#00FFFF bold',
                                    'arg': '#FFFF00',
                                    'param': '#00FF00',
                                })
                            )

                            try:
                                edited_command = await asyncio.to_thread(
                                    edit_session.prompt,
                                    HTML(f'<prompt>&gt;</prompt> {colored_command}'),
                                )
                                command_to_execute = edited_command if edited_command.strip() else command_to_execute
                            except KeyboardInterrupt:
                                console.print("\n[bold yellow]Command execution cancelled.[/bold yellow]")
                                continue

                            with console.status("[bold green]Executing command...[/bold green]"):
                                output = await run_command(command_to_execute)
                            
                            if output.strip():
                                console.print(Panel(output, title="Command Output", expand=False, border_style="green"))
                            else:
                                console.print("[yellow]Command executed successfully, but produced no output.[/yellow]")
                            await save_to_history(command_to_execute)
                        else:
                            console.print("[bold red]Invalid selection. Please try again.[/bold red]")
                    else:
                        console.print("[bold red]Invalid input. Please try again.[/bold red]")

                user_input = ""  # Reset user_input to prompt for a new query

        except Exception as e:
            console.print(f"[bold red]An error occurred:[/bold red] {str(e)}")
            if "project" in str(e).lower():
                console.print("[bold yellow]Please check your PROJECT_ID and ensure it's correctly set in your environment variables.[/bold yellow]")

if __name__ == "__main__":
    asyncio.run(main())