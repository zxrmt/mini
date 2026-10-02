from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import PromptSession

from minisweagent import global_config_dir

SLASH_COMMANDS = {
    "/help": "show available commands",
    "/setup": "change provider, model, reasoning effort or API key",
    "/compact": "summarize the conversation into a smaller context",
    "/new": "start a new conversation",
    "/resume": "list saved conversations and continue one",
    "/y": "switch to yolo mode",
    "/c": "switch to confirm mode",
    "/u": "switch to human mode",
    "/m": "enter multiline comment",
}


class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/") and " " not in text and "\n" not in text:
            for command, description in SLASH_COMMANDS.items():
                if command.startswith(text):
                    yield Completion(command, start_position=-len(text), display_meta=description)


_history = FileHistory(global_config_dir / "interactive_history.txt")
_completion = {"completer": SlashCommandCompleter(), "complete_while_typing": True}
prompt_session = PromptSession(history=_history, **_completion)

# Escape is only a submit prefix while it is still ambiguous: pause between Esc and Enter and
# prompt_toolkit flushes the lone Escape, so Enter would just add another line and nothing submits.
_multiline_bindings = KeyBindings()
_multiline_bindings.add("enter")(lambda event: event.current_buffer.validate_and_handle())
_multiline_bindings.add("c-j")(lambda event: event.current_buffer.insert_text("\n"))

_multiline_prompt_session = PromptSession(
    history=_history, multiline=True, key_bindings=_multiline_bindings, **_completion
)


def _multiline_prompt() -> str:
    return _multiline_prompt_session.prompt("")
