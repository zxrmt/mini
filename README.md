<div align="center">
<a href="https://mini-swe-agent.com/latest/"><img src="https://github.com/SWE-agent/mini-swe-agent/raw/main/docs/assets/mini-swe-agent-banner.svg" alt="mini banner" style="height: 7em"/></a>
</div>

# mini — the minimal AI software engineering agent

`mini` is a tiny, hackable AI agent that gets real work done on a computer the same way you do: by running shell commands and editing files.

The whole idea is to keep the *scaffold* minimal and let the language model do the heavy lifting. There are no tool schemas, no stateful shell session and no framework to learn — just a linear loop between the model and bash.

- **Minimal** — roughly 100 lines of Python for the agent loop, plus a few small modules for the environment, the model and the CLI, with very few dependencies beyond the model client.
- **Bash-only** — the agent needs nothing but a shell. It does not depend on the tool-calling API of the model, so it works with essentially any chat model.
- **Model agnostic** — multiple interchangeable model backends (Litellm, OpenRouter, Portkey, Requesty), including OpenAI-compatible, Anthropic and Ollama endpoints, as well as the Responses API.
- **Runs anywhere** — execute in your local shell, or sandboxed in Docker/Podman, Singularity/Apptainer, bubblewrap, SWE-ReX (Docker/Modal) or Contree.
- **Interactive by default** — a terminal chat loop with confirm / yolo / human modes, live streamed output, conversation history, resume and compaction.
- **Practical** — an onboarding config wizard, cost tracking, reasoning-effort control, completion notifications and saved trajectories.

## How it works

`mini` runs the simplest possible agentic loop:

1. The model is shown the task and the entire message history.
2. It replies with a short piece of reasoning and **exactly one bash command**.
3. The command runs in the configured environment; its output is appended to the history as an observation.
4. Steps 1–3 repeat until the agent submits its final answer.

Every step simply appends a message, so the trajectory *is* the message history — easy to read, debug, replay and fine-tune.

## Features

- **Three interaction modes**
  - `human` — commands you type are executed immediately.
  - `confirm` — commands proposed by the model are confirmed by you before they run (unless whitelisted).
  - `yolo` — model-proposed commands run immediately.
- **Slash commands** in the interactive session: `/h` help, `/new` start a fresh conversation, `/resume` continue a saved one, `/compact` summarize the history to shrink the context, `/setup` reconfigure provider/model/key, and `/y` `/c` `/u` to switch modes.
- **Live streaming** of the model's reasoning and answer, with time-to-first-token and output speed shown for each step.
- **Persistent conversations** — runs are saved to a trajectory file and (optionally) a conversations directory, so interrupted work can be resumed.
- **Compaction** — collapse a long conversation into a model-written summary while keeping the system and task messages.
- **Setup wizard** — `/setup` (or `mini-extra config setup`) walks you through provider, model, reasoning effort and API key and writes them to your global config.
- **Model controls** — reasoning effort, drop-params compatibility, retries, multimodal content and provider-specific tweaks.
- **Cost tracking** and an optional global call limit (`MSWEA_GLOBAL_CALL_LIMIT`).
- **Notifications** — ring the terminal bell when a task completes (`--notify-channel terminal_bell`).

## Architecture

The project favors polymorphism: every core component is a small protocol with interchangeable implementations.

```
minisweagent/
├── __init__.py      # Version, global config paths and the core protocols
├── agents/          # Agent control flow (default) + human-in-the-loop (interactive)
├── environments/    # Where actions run (local, docker, singularity, ...)
├── models/          # Language-model interfaces (litellm, openrouter, portkey, ...)
├── config/          # Built-in YAML configuration
└── run/             # Entry points: the `mini` CLI, example scripts and utilities
```

A *run script* wires together one **agent**, one **environment** and one **model**:

```python
agent = DefaultAgent(
    LitellmModel(model_name="openai/gpt-5"),
    LocalEnvironment(),
)
agent.run("Write a sudoku game")
```

## Installation

**Option 1 — run without installing (isolated environment):**

```bash
pip install uv && uvx mini-swe-agent
# or
pip install pipx && pipx ensurepath && pipx run mini-swe-agent
```

**Option 2 — install the CLI and Python bindings:**

```bash
pip install mini-swe-agent
mini   # start the CLI
```

**Option 3 — install from source:**

```bash
git clone https://github.com/SWE-agent/mini-swe-agent.git
cd mini-swe-agent
pip install -e .
mini
```

Optional extras:

```bash
pip install "mini-swe-agent[modal]"    # Modal + boto3
pip install "mini-swe-agent[contree]"  # Contree sandbox
pip install "mini-swe-agent[dev]"      # tests, linting, docs
```

## Quickstart

Set up a model and API key once, then start the agent:

```bash
mini   # launch the interactive agent; it prompts for anything that is missing
```

The first run walks you through configuration and stores it in
`~/.config/mini-swe-agent/.env`. You can reconfigure at any time with the in-session
`/setup` command or with `mini-extra config setup`.

Give it a task directly:

```bash
mini -t "Find and fix the bug in src/foo.py"
mini -m openai/gpt-5 -t "Explain what this repository does"
mini -t "Write a sudoku game in Python" -c mini.yaml
```

## The `mini` CLI

```bash
mini [options] [resume_path]
```

Common options:

| Option | Description |
| --- | --- |
| `-t`, `--task` | Task / problem statement. If omitted, `mini` prompts for it. |
| `-m`, `--model` | Model to use (defaults to `MSWEA_MODEL_NAME`). |
| `-c`, `--config` | Config files, names or `key=value` overrides (merged). |
| `-o`, `--output` | Where to save the trajectory (default: `last_mini_run.traj.json`). |
| `-y`, `--yolo` / `--no-yolo` | Run without confirmation. |
| `-q`, `--quiet` / `--no-quiet` | Hide the system prompt and observation metadata. |
| `-r`, `--resume` | Continue the run saved at the output path. |
| `--reasoning-effort` | `low`, `medium`, `high`, ... |
| `--tokens` | API key that replaces `ANTHROPIC_API_KEY` in the global config for this run. |
| `--exit-immediately` | Do not ask for confirmation when the model finishes. |
| `--agent-class` / `--model-class` / `--environment-class` | Pick alternative implementations. |
| `--notify-channel` | `terminal_bell` or `none`. |

A second entry point, `mini-extra`, bundles the auxiliary commands:

```bash
mini-extra config setup   # onboarding / edit the global config
mini-extra inspect        # browse saved trajectories
```

## Python bindings

Everything the CLI does is available as a small library. Compose an agent from a model
and an environment, then run it:

```python
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

agent = DefaultAgent(
    LitellmModel(model_name="openai/gpt-5"),
    LocalEnvironment(),
)
agent.run("Write a sudoku game")
```

See `src/minisweagent/run/hello_world.py` for the minimal working example.

## Configuration

Global settings (API keys, default model and other `MSWEA_*` options) live in an `.env`
file. By default it is read from `~/.config/mini-swe-agent/.env`; override the directory
with `MSWEA_GLOBAL_CONFIG_DIR`.

Common variables:

| Variable | Purpose |
| --- | --- |
| `MSWEA_MODEL_NAME` | Default model name. |
| `MSWEA_REASONING_EFFORT` | Default reasoning effort. |
| `MSWEA_GLOBAL_CONFIG_DIR` | Where the global `.env` lives. |
| `MSWEA_NOTIFY_CHANNEL` | Completion alert (`terminal_bell` / `none`). |
| `MSWEA_COST_TRACKING` | Cost-tracking behaviour. |
| `MSWEA_GLOBAL_CALL_LIMIT` | Maximum number of model calls. |
| `MSWEA_DOCKER_EXECUTABLE` / `MSWEA_SINGULARITY_EXECUTABLE` / `MSWEA_BUBBLEWRAP_EXECUTABLE` | Sandbox executables. |

Provider keys use the usual names, e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and
`OPENROUTER_API_KEY`, plus base-URL variables such as `OPENAI_BASE_URL`,
`ANTHROPIC_BASE_URL` and `OLLAMA_API_BASE`.

Behaviour is also driven by YAML config files under `src/minisweagent/config/`. The
default for the interactive CLI is `mini.yaml`. Multiple configs are recursively merged,
and any value can be overridden on the command line:

```bash
mini -c mini.yaml -c model.model_kwargs.temperature=0.5
```

## Documentation

Full documentation is at <https://mini-swe-agent.com/latest/>:

* [Quick start](https://mini-swe-agent.com/latest/quickstart/)
* [The `mini` CLI](https://mini-swe-agent.com/latest/usage/mini/)
* [Global configuration](https://mini-swe-agent.com/latest/advanced/global_configuration/)
* [YAML configuration](https://mini-swe-agent.com/latest/advanced/yaml_configuration/)
* [Cookbook](https://mini-swe-agent.com/latest/advanced/cookbook/)
* [FAQ](https://mini-swe-agent.com/latest/faq/)
* [Contributing](https://mini-swe-agent.com/latest/contributing/)

## License and attribution

Released under the MIT license — see [LICENSE.md](LICENSE.md).

The agent approach grew out of the SWE-agent research project. If you find it useful,
please consider citing:

```bibtex
@inproceedings{yang2024sweagent,
  title={{SWE}-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
  author={John Yang and Carlos E Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik R Narasimhan and Ofir Press},
  booktitle={The Thirty-eighth Annual Conference on Neural Information Processing Systems},
  year={2024},
  url={https://arxiv.org/abs/2405.15793}
}
```
