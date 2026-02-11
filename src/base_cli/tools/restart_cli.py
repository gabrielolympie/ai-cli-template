from mirascope import llm
import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = os.getcwd()

STATE_FILE = Path(PROJECT_ROOT) / ".cli_state.json"


def _load_state() -> dict:
    """Load state from the state file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    """Save state to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


@llm.tool
def restart_cli(state_instruction: str = "") -> str:
    """Restart the CLI application.

    Re-executes the CLI process. Optionally saves an instruction
    to be automatically executed on startup.

    Args:
        state_instruction: Optional instruction to execute after restart.
            Must describe actual work, not just "restart" or "continue".

    Returns:
        This function does not return if restart succeeds.
    """
    try:
        if state_instruction:
            state = _load_state()
            state["last_instruction"] = state_instruction
            _save_state(state)

        os.execv(sys.executable, [sys.executable] + sys.argv)
        return "Restart initiated..."  # Should not reach here
    except Exception as e:
        return f"Error restarting CLI: {str(e)}"


@llm.tool
def set_restart_state(key: str, value: str | int | float | bool | None) -> str:
    """Store a key-value pair in state for persistence across restarts.

    Args:
        key: The key to store
        value: The value (string, number, boolean, or null)

    Returns:
        Confirmation message.
    """
    try:
        state = _load_state()
        state[key] = value
        _save_state(state)
        return f"State saved: {key} = {value}"
    except Exception as e:
        return f"Error saving state: {str(e)}"


@llm.tool
def get_restart_state(key: str | None = None) -> str:
    """Retrieve stored state.

    Args:
        key: Specific key to retrieve, or None to list all keys.

    Returns:
        The value for the key, or a list of all available keys.
    """
    try:
        state = _load_state()
        if not state:
            return "No stored state found."

        if key is None:
            keys = ", ".join(state.keys())
            return f"Available keys: {keys}"

        if key in state:
            return f"{key} = {json.dumps(state[key])}"
        else:
            return f"Key '{key}' not found. Available: {', '.join(state.keys())}"
    except Exception as e:
        return f"Error reading state: {str(e)}"


@llm.tool
def clear_restart_state() -> str:
    """Clear all stored state.

    Returns:
        Confirmation message.
    """
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            return "All stored state cleared."
        return "No state to clear."
    except Exception as e:
        return f"Error clearing state: {str(e)}"


__tool_category__ = "state"
__tools__ = [restart_cli, set_restart_state, get_restart_state, clear_restart_state]
