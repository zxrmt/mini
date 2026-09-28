#!/usr/bin/env python3

"""Utility to manage the global config file.

You can also directly edit the `.env` file in the config directory.

It is located at [bold green]{global_config_file}[/bold green].
"""

import os
import subprocess

from dotenv import load_dotenv, set_key, unset_key
from rich.console import Console
from rich.rule import Rule
from typer import Argument, Typer

from minisweagent import global_config_file
from minisweagent.run.utilities.setup_wizard import prompt, run_setup_wizard


def _reload_config():
    load_dotenv(dotenv_path=global_config_file, override=True)


app = Typer(
    help=__doc__.format(global_config_file=global_config_file),  # type: ignore
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)
console = Console(highlight=False)


def configure_if_first_time():
    if not os.getenv("MSWEA_CONFIGURED"):
        console.print(Rule())
        setup()
        console.print(Rule())


@app.command()
def setup():
    """Setup the global config file (provider, model, reasoning effort, API key)."""
    run_setup_wizard()
    _reload_config()


@app.command()
def set(
    key: str | None = Argument(None, help="The key to set"),
    value: str | None = Argument(None, help="The value to set"),
):
    """Set a key in the global config file."""
    if key is None:
        key = prompt("Enter the key to set: ")
    if value is None:
        value = prompt(f"Enter the value for {key}: ")
    set_key(global_config_file, key, value)
    _reload_config()


@app.command()
def unset(key: str | None = Argument(None, help="The key to unset")):
    """Unset a key in the global config file."""
    if key is None:
        key = prompt("Enter the key to unset: ")
    unset_key(global_config_file, key)
    _reload_config()


def set_token(token: str, key_name: str = "ANTHROPIC_API_KEY"):
    """Replace an API key in the global config file and apply it to the current process."""
    set_key(global_config_file, key_name, token)
    os.environ[key_name] = token
    console.print(f"Updated [bold green]{key_name}[/bold green] in '{global_config_file}'")


@app.command()
def edit():
    """Edit the global config file."""
    editor = os.getenv("EDITOR", "nano")
    subprocess.run([editor, global_config_file])
    _reload_config()


if __name__ == "__main__":
    app()
