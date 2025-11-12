"""Command-line interface for the fixture fetcher."""

import time

from beaupy import confirm, select, select_multiple
from beaupy.spinners import DOTS, Spinner
from rich.align import Align
from rich.console import Console
from rich.panel import Panel

console = Console()


class CLI:
    """CLI class to interact with the user for fetching football fixtures."""

    def __init__(self):
        """Initialize the CLI."""
        self.console = console
        self.panel_width = console.size.width

    def welcome_message(self):
        """Display a welcome message."""
        welcome_message = "⚽️ [bold green]Welcome to the Football Fixture Fetcher![/bold green] ⚽️"
        self.console.print(
            Panel(
                Align.center(welcome_message),
                padding=(1),
                border_style="dim green",
                width=self.panel_width,
            )
        )

    def interactive_prompt(self):
        """Prompt the user for input interactively."""
        if confirm("Do you want to fetch football fixtures?"):
            teams = [
                "Manchester United",
                "Manchester United Women",
                "Wolverhampton Wanderers",
            ]

            self.console.print("Select a team to fetch fixtures for:")
            selected_team = select(teams, cursor="> ", cursor_style="cyan")
            self.console.print(f"You selected: {selected_team}")

            competitions = [
                "Premier League",
                "FA Cup",
                "EFL Cup",
            ]

            self.console.print("Select competitions to fetch fixtures for:")
            selected_competition = select_multiple(
                competitions, tick_character="⚽️", ticked_indices=[0]
            )
            self.console.print(f"You selected: {', '.join(selected_competition)}")

            spinner = Spinner(DOTS, text="Fetching fixtures...")
            spinner.start()
            time.sleep(2)  # Simulate fetching time
            spinner.stop()

            success_message = f"⚽️ [bold green]Successfully fetched {', '.join(selected_competition)} fixtures for {selected_team}![/bold green] ⚽️"
            self.console.print(
                Panel(
                    Align.center(success_message),
                    padding=(1),
                    border_style="dim green",
                    width=self.panel_width,
                )
            )

    def run(self):
        """Run the CLI application."""
        self.welcome_message()
        self.interactive_prompt()


if __name__ == "__main__":
    cli = CLI()
    cli.run()
