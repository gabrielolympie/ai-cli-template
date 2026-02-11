from mirascope import llm
import os
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = os.getcwd()

STATE_FILE = Path(PROJECT_ROOT) / ".cli_state.json"
COMPACT_STATE_FILE = Path(PROJECT_ROOT) / ".cli_compact_state.json"


@llm.tool
def compact_state():
    """Compact the current CLI state by summarizing recent activity.

    Use when approaching the total context limit. Creates a compact summary
    and clears the current state while preserving essential information.

    Returns:
        A summary of what was compacted and what was preserved.
    """
    try:
        current_state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                current_state = json.load(f)

        compact_summary = {
            "compacted_at": datetime.now().isoformat(),
            "summary": "Context compacted. Key information preserved below.",
            "preserved_keys": [],
            "recent_summary": "No recent activity summary available."
        }

        if "last_instruction" in current_state:
            compact_summary["recent_summary"] = f"Last instruction: {current_state['last_instruction']}"
            compact_summary["preserved_keys"].append("last_instruction")
            del current_state["last_instruction"]

        for key in ["current_file", "pending_tasks", "project_context"]:
            if key in current_state:
                compact_summary[f"_{key}"] = current_state[key]
                compact_summary["preserved_keys"].append(key)
                del current_state[key]

        with open(COMPACT_STATE_FILE, 'w') as f:
            json.dump(compact_summary, f, indent=2)

        current_state["last_compacted"] = datetime.now().isoformat()
        if compact_summary["preserved_keys"]:
            current_state["compacted_info"] = compact_summary["recent_summary"]

        with open(STATE_FILE, 'w') as f:
            json.dump(current_state, f, indent=2)

        response_parts = [
            "State compacted successfully.",
            f"Summary: {compact_summary['recent_summary']}",
            f"Preserved keys: {', '.join(compact_summary['preserved_keys']) or 'none'}"
        ]

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error compacting state: {str(e)}"


@llm.tool
def get_compact_state() -> str:
    """Retrieve the compacted state from previous sessions.

    Returns:
        The compacted state summary or message if none exists.
    """
    try:
        if not COMPACT_STATE_FILE.exists():
            return "No compacted state found."

        with open(COMPACT_STATE_FILE, 'r') as f:
            data = json.load(f)

        lines = [
            f"Compacted at: {data.get('compacted_at', 'Unknown')}",
            f"Summary: {data.get('summary', 'N/A')}",
        ]

        if 'recent_summary' in data:
            lines.append(f"Recent work: {data['recent_summary']}")

        if 'preserved_keys' in data and data['preserved_keys']:
            lines.append(f"Preserved information: {', '.join(data['preserved_keys'])}")

        for key in data:
            if key.startswith('_'):
                lines.append(f"{key[1:]}: {data[key]}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error reading compacted state: {str(e)}"


@llm.tool
def clear_compact_state():
    """Clear the compacted state file.

    Returns:
        Confirmation message.
    """
    try:
        if COMPACT_STATE_FILE.exists():
            COMPACT_STATE_FILE.unlink()
            return "Compacted state cleared."
        else:
            return "No compacted state to clear."
    except Exception as e:
        return f"Error clearing compacted state: {str(e)}"


__tool_category__ = "state"
__tools__ = [compact_state, get_compact_state, clear_compact_state]
