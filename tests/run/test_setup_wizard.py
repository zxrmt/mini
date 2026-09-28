import os
from unittest.mock import patch

import pytest

from minisweagent.run.utilities.setup_wizard import _detect_provider, run_setup_wizard


def _run_wizard(
    config_file, answers: list[str], env: dict[str, str] | None = None
) -> tuple[dict[str, str], dict[str, str]]:
    """Returns what the wizard wrote and the process environment it left behind."""
    with (
        patch("minisweagent.run.utilities.setup_wizard.global_config_file", config_file),
        patch("minisweagent.run.utilities.setup_wizard.prompt", side_effect=answers),
        patch("minisweagent.run.utilities.setup_wizard.console.print"),
        patch.dict(os.environ, env or {}, clear=True),
    ):
        return run_setup_wizard(), dict(os.environ)


def test_wizard_writes_provider_model_effort_and_key(tmp_path):
    """Picking Kimi (5) -> its only model (1) -> high effort (5) writes every variable it needs."""
    config_file = tmp_path / ".env"

    settings, _ = _run_wizard(config_file, ["5", "1", "5", "https://api.kimi.com/coding/v1", "sk-kimi"])

    assert settings == {
        "MSWEA_CONFIGURED": "true",
        "MSWEA_MODEL_NAME": "openai/kimi-for-coding",
        "MSWEA_REASONING_EFFORT": "high",
        "OPENAI_BASE_URL": "https://api.kimi.com/coding/v1",
        "OPENAI_API_BASE": "https://api.kimi.com/coding/v1",
        "OPENAI_API_KEY": "sk-kimi",
    }
    content = config_file.read_text()
    assert "MSWEA_MODEL_NAME='openai/kimi-for-coding'" in content
    assert "MSWEA_REASONING_EFFORT='high'" in content
    assert "OPENAI_API_BASE='https://api.kimi.com/coding/v1'" in content
    assert "OPENAI_API_KEY='sk-kimi'" in content
    assert "MSWEA_CONFIGURED='true'" in content


def test_switching_provider_clears_stale_base_url_but_keeps_other_api_keys(tmp_path):
    """The old provider's base URL would silently redirect the new one, so it has to go."""
    config_file = tmp_path / ".env"
    config_file.write_text(
        "MSWEA_MODEL_NAME='anthropic/glm-5.3'\n"
        "ANTHROPIC_BASE_URL='https://api.z.ai/api/anthropic'\n"
        "ANTHROPIC_API_BASE='https://api.z.ai/api/anthropic'\n"
        "ANTHROPIC_API_KEY='sk-glm'\n"
        "MSWEA_REASONING_EFFORT='high'\n"
    )
    env = {
        "MSWEA_MODEL_NAME": "anthropic/glm-5.3",
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "ANTHROPIC_API_BASE": "https://api.z.ai/api/anthropic",
        "ANTHROPIC_API_KEY": "sk-glm",
        "MSWEA_REASONING_EFFORT": "high",
    }

    # Provider 2 (OpenAI, no base URL of its own) -> first model -> medium effort (4) -> key.
    settings, process_env = _run_wizard(config_file, ["2", "1", "4", "sk-openai"], env)

    # The current process must not keep using the endpoint we just removed.
    assert "ANTHROPIC_BASE_URL" not in process_env
    assert process_env["OPENAI_API_KEY"] == "sk-openai"
    assert process_env["MSWEA_MODEL_NAME"] == "openai/gpt-5.4"
    assert "ANTHROPIC_BASE_URL" not in settings
    content = config_file.read_text()
    assert "ANTHROPIC_BASE_URL" not in content
    assert "ANTHROPIC_API_BASE" not in content
    assert "MSWEA_MODEL_NAME='openai/gpt-5.4'" in content
    assert "MSWEA_REASONING_EFFORT='medium'" in content
    # API keys are additive: the Anthropic one stays available for a later switch back.
    assert "ANTHROPIC_API_KEY='sk-glm'" in content


def test_leaving_effort_unset_removes_a_previously_configured_one(tmp_path):
    config_file = tmp_path / ".env"
    config_file.write_text("MSWEA_REASONING_EFFORT='high'\n")

    settings, _ = _run_wizard(config_file, ["1", "1", "1", "sk-ant"], {"MSWEA_REASONING_EFFORT": "high"})

    assert "MSWEA_REASONING_EFFORT" not in settings
    assert "MSWEA_REASONING_EFFORT" not in config_file.read_text()


def test_custom_model_name_via_other_entry(tmp_path):
    """Anthropic offers 2 models, so entry 3 is 'Other' and the next answer is free text."""
    config_file = tmp_path / ".env"

    settings, _ = _run_wizard(config_file, ["1", "3", "anthropic/claude-haiku-4-5-20251001", "3", ""])

    assert settings["MSWEA_MODEL_NAME"] == "anthropic/claude-haiku-4-5-20251001"
    assert settings["MSWEA_REASONING_EFFORT"] == "low"
    # A blank API key keeps whatever is already configured instead of writing an empty one.
    assert "ANTHROPIC_API_KEY" not in settings


def test_custom_provider_asks_for_the_model_name_directly(tmp_path):
    """Provider 12 has no suggestions, so the model question is a plain text prompt."""
    config_file = tmp_path / ".env"

    settings, _ = _run_wizard(config_file, ["12", "openai/my-model", "1", "https://my.host/v1", "sk-custom"])

    assert settings["MSWEA_MODEL_NAME"] == "openai/my-model"
    assert settings["OPENAI_BASE_URL"] == settings["OPENAI_API_BASE"] == "https://my.host/v1"


def test_invalid_selection_is_rejected_until_a_valid_one_is_given(tmp_path):
    config_file = tmp_path / ".env"

    settings, _ = _run_wizard(config_file, ["99", "abc", "3", "1", "1", ""])

    assert settings["MSWEA_MODEL_NAME"] == "gemini/gemini-3-pro-preview"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic"}, "GLM (Z.ai)"),
        ({"OPENAI_API_BASE": "https://api.deepseek.com"}, "DeepSeek"),
        ({"OLLAMA_API_BASE": "http://localhost:11434"}, "Ollama (local)"),
        ({"ANTHROPIC_API_BASE": "https://api.minimax.io/anthropic"}, "MiniMax"),
        # A base URL wins over the model name: `anthropic/` here is GLM, not Anthropic.
        (
            {"MSWEA_MODEL_NAME": "anthropic/glm-5.3", "ANTHROPIC_API_BASE": "https://api.z.ai/api/anthropic"},
            "GLM (Z.ai)",
        ),
        ({"MSWEA_MODEL_NAME": "anthropic/claude-opus-4-6-20260205"}, "Anthropic"),
        ({"MSWEA_MODEL_NAME": "openai/gpt-5.4"}, "OpenAI"),
        ({"MSWEA_MODEL_NAME": "ollama_chat/whatever"}, ""),
        ({}, ""),
    ],
)
def test_detect_provider(env, expected):
    with patch.dict(os.environ, env, clear=True):
        assert _detect_provider() == expected
