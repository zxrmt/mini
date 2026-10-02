#!/usr/bin/env python3

"""Guided onboarding: pick a provider, model, reasoning effort and API key, then write everything
to the global config file, so the `.env` file never has to be edited by hand.

Used by `mini-extra config setup`, by the first-run prompt and by the `/setup` slash command.
"""

import os
from dataclasses import dataclass, field

from dotenv import dotenv_values, set_key, unset_key
from rich.console import Console
from rich.panel import Panel

from minisweagent import global_config_file

console = Console(highlight=False)

OPENAI_BASE_KEYS = ("OPENAI_BASE_URL", "OPENAI_API_BASE")
ANTHROPIC_BASE_KEYS = ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_BASE")
# Cleared whenever the chosen provider doesn't set them: a base URL left over from a previous
# provider silently redirects the new one to the old endpoint.
MANAGED_BASE_URL_KEYS = (*OPENAI_BASE_KEYS, *ANTHROPIC_BASE_KEYS, "OLLAMA_API_BASE")
EFFORTS = ["(leave unset)", "minimal", "low", "medium", "high"]
OTHER = "Other (enter manually)"
# Written on every run so that a freshly configured `.env` is complete and works out of the box
# instead of relying on the user hand-editing the file afterwards.
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_NOTIFY_CHANNEL = "terminal_bell"
DEFAULT_COST_TRACKING = "ignore_errors"


@dataclass
class Provider:
    name: str
    models: list[str] = field(default_factory=list)
    """Suggestions for the model picker; any other name can always be typed in."""
    key_name: str = ""
    """API key variable, empty when the provider needs none."""
    base_url: str = ""
    """Default endpoint, pre-filled in the base URL question."""
    base_url_keys: tuple[str, ...] = ()
    """Variables that carry the base URL. No keys means the provider's own endpoint is used."""


PROVIDERS = [
    Provider(
        "Anthropic", ["anthropic/claude-opus-4-6-20260205", "anthropic/claude-sonnet-4-5-20250929"], "ANTHROPIC_API_KEY"
    ),
    Provider("OpenAI", ["openai/gpt-5.4", "openai/gpt-5.4-mini"], "OPENAI_API_KEY"),
    Provider("Gemini", ["gemini/gemini-3-pro-preview"], "GEMINI_API_KEY"),
    Provider(
        "OpenRouter", ["openrouter/anthropic/claude-sonnet-4.5", "openrouter/openai/gpt-5.4"], "OPENROUTER_API_KEY"
    ),
    Provider(
        "Kimi (Moonshot)",
        ["openai/kimi-for-coding"],
        "OPENAI_API_KEY",
        "https://api.kimi.com/coding/v1",
        OPENAI_BASE_KEYS,
    ),
    Provider(
        "DeepSeek",
        ["openai/deepseek-chat", "openai/deepseek-reasoner"],
        "OPENAI_API_KEY",
        "https://api.deepseek.com",
        OPENAI_BASE_KEYS,
    ),
    Provider(
        "OpenCode Zen", ["openai/deepseek-flash"], "OPENAI_API_KEY", "https://opencode.ai/zen/go/v1", OPENAI_BASE_KEYS
    ),
    Provider(
        "GLM (Z.ai)", ["anthropic/glm-5.3"], "ANTHROPIC_API_KEY", "https://api.z.ai/api/anthropic", ANTHROPIC_BASE_KEYS
    ),
    Provider(
        "MiniMax",
        ["anthropic/MiniMax-M3.1-Flash-Preview"],
        "ANTHROPIC_API_KEY",
        "https://api.minimax.io/anthropic",
        ANTHROPIC_BASE_KEYS,
    ),
    Provider("Ollama (local)", ["ollama_chat/qwen3-coder"], "", "http://localhost:11434", ("OLLAMA_API_BASE",)),
    Provider(
        "Ollama (cloud)",
        ["ollama_chat/deepseek-v4.1-flash"],
        "OLLAMA_API_KEY",
        "https://ollama.com",
        ("OLLAMA_API_BASE",),
    ),
    Provider("Custom (OpenAI-compatible)", [], "OPENAI_API_KEY", "", OPENAI_BASE_KEYS),
    Provider("Custom (Anthropic-compatible)", [], "ANTHROPIC_API_KEY", "", ANTHROPIC_BASE_KEYS),
]

_INTRO = f"""[bold]Let's set up mini-swe-agent.[/bold]

Your answers are written to [bold green]{global_config_file}[/bold green], so you don't have to edit that file yourself.
Press [bold green]Enter[/bold green] to accept the suggested answer shown in brackets.

Find the best model on the leaderboard at https://swebench.com/, more information at https://mini-swe-agent.com/latest/quickstart/
"""


def prompt(*args, **kwargs):
    # Defer import to avoid slow import module
    from prompt_toolkit.shortcuts.prompt import prompt as _prompt

    return _prompt(*args, **kwargs)


def _choose(title: str, options: list[str], default: str = "", other_prompt: str = "") -> str:
    """Numbered picker. With `other_prompt`, a last entry lets the user type any value instead."""
    if not options:
        return prompt(other_prompt, default=default).strip()
    entries = options + ([OTHER] if other_prompt else [])
    default_index = entries.index(default) + 1 if default in entries else 1
    console.print(f"\n[bold yellow]{title}[/bold yellow]")
    for i, entry in enumerate(entries, 1):
        console.print(
            f"  [bold green]{i}[/bold green]. {entry}" + ("  [dim](current)[/dim]" if entry == default else "")
        )
    while True:
        choice = prompt(f"Select 1-{len(entries)} [{default_index}]: ").strip() or str(default_index)
        if not (choice.isdigit() and 1 <= int(choice) <= len(entries)):
            console.print(f"[bold red]Please enter a number between 1 and {len(entries)}.[/bold red]")
            continue
        if other_prompt and int(choice) == len(entries):
            return prompt(other_prompt, default="" if default in entries else default).strip()
        return entries[int(choice) - 1]


def _detect_provider() -> str:
    """Best guess at the currently configured provider, used as the picker's default."""
    for provider in PROVIDERS:
        if provider.base_url and provider.base_url in {os.getenv(key, "") for key in provider.base_url_keys}:
            return provider.name
    model_name = os.getenv("MSWEA_MODEL_NAME", "")
    for provider in PROVIDERS:
        if not provider.base_url_keys and any(model_name.startswith(m.split("/")[0] + "/") for m in provider.models):
            return provider.name
    return ""


def _mask(value: str) -> str:
    if not value:
        return "[red]not set[/red]"
    return f"{value[:6]}…{value[-4:]}" if len(value) > 14 else "set"


def _apply(settings: dict[str, str], cleared: list[str]) -> None:
    """Persist the settings and make them effective for the running process."""
    existing = dotenv_values(global_config_file) if global_config_file.exists() else {}
    for key in cleared:
        if key not in settings:
            os.environ.pop(key, None)
            if key in existing:
                unset_key(global_config_file, key)
    for key, value in settings.items():
        set_key(global_config_file, key, value)
        os.environ[key] = value


def run_setup_wizard() -> dict[str, str]:
    """Ask for provider/model/reasoning effort/API key and persist them. Returns what was written."""
    console.print(_INTRO)
    # Bind the answer first: inlining `_choose` into the generator would re-ask once per provider.
    provider_name = _choose("Provider", [p.name for p in PROVIDERS], _detect_provider())
    provider = next(p for p in PROVIDERS if p.name == provider_name)
    model_name = _choose(
        "Model",
        provider.models,
        os.getenv("MSWEA_MODEL_NAME", ""),
        "Model name (always include the provider, e.g. openai/gpt-5.4): ",
    )
    effort = _choose("Reasoning effort", EFFORTS, os.getenv("MSWEA_REASONING_EFFORT") or DEFAULT_REASONING_EFFORT)

    settings = {
        "MSWEA_CONFIGURED": "true",
        "MSWEA_NOTIFY_CHANNEL": DEFAULT_NOTIFY_CHANNEL,
        "MSWEA_COST_TRACKING": DEFAULT_COST_TRACKING,
    }
    cleared = list(MANAGED_BASE_URL_KEYS)
    if model_name:
        settings["MSWEA_MODEL_NAME"] = model_name
    if effort in EFFORTS[1:]:
        settings["MSWEA_REASONING_EFFORT"] = effort
    else:
        cleared.append("MSWEA_REASONING_EFFORT")

    base_url = ""
    if provider.base_url_keys:
        console.print(f"\n[bold yellow]Base URL[/bold yellow] for {provider.name}")
        base_url = prompt("Base URL: ", default=provider.base_url or os.getenv(provider.base_url_keys[0], "")).strip()
        settings.update({key: base_url for key in provider.base_url_keys if base_url})

    if provider.key_name:
        console.print(
            f"\n[bold yellow]API key[/bold yellow] ({provider.key_name})\n"
            "[dim]Leave blank to keep whatever is already set, e.g. a shell environment variable.[/dim]"
        )
        if api_key := prompt(f"{provider.key_name}: ", default=os.getenv(provider.key_name, "")).strip():
            settings[provider.key_name] = api_key

    _apply(settings, cleared)
    key_line = (
        f"{provider.key_name}  {_mask(os.getenv(provider.key_name, ''))}" if provider.key_name else "not required"
    )
    console.print(
        Panel(
            f"[bold]Provider[/bold]  {provider.name}\n"
            f"[bold]Model[/bold]     [green]{model_name or '[red]not set[/red]'}[/green]\n"
            f"[bold]Reasoning[/bold] {settings.get('MSWEA_REASONING_EFFORT', 'default')}\n"
            f"[bold]Notify[/bold]    {DEFAULT_NOTIFY_CHANNEL}\n"
            f"[bold]Costs[/bold]     {DEFAULT_COST_TRACKING}\n"
            f"[bold]Base URL[/bold]  {base_url or 'provider default'}\n"
            f"[bold]API key[/bold]   {key_line}\n"
            f"[bold]Saved to[/bold]  [dim]{global_config_file}[/dim]",
            title="Setup complete",
            title_align="left",
            border_style="green",
            expand=False,
        )
    )
    console.print(
        "[dim]Revisit any time with [bold green]/setup[/bold green] or [bold green]mini-extra config setup[/bold green].[/dim]"
    )
    return settings
