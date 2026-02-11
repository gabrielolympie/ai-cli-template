from mirascope import llm
import os
import json
from pathlib import Path
from datetime import datetime

# Get the current working directory (hard constraint: operations limited to this folder)
# Use CWD as the root to avoid accidentally accessing files elsewhere
PROJECT_ROOT = os.getcwd()

# State file location
STATE_FILE = Path(PROJECT_ROOT) / ".cli_state.json"

# Compact state file location (stores compressed context)
COMPACT_STATE_FILE = Path(PROJECT_ROOT) / ".cli_compact_state.json"


@llm.tool
def compact_state():
    """Compact the current CLI state by summarizing recent activity.
    
    This tool is used when approaching the total context limit. It:
    1. Reads the current state from .cli_state.json
    2. Creates a compact summary of recent work
    3. Saves the summary to .cli_compact_state.json
    4. Clears the current state, keeping only essential information
    
    The compact state includes:
    - Summary of recent tasks completed
    - Key decisions made
    - Current working context
    - Any pending work items
    
    Use this tool when:
    - Context is approaching the token limit
    - You need to preserve progress before a long break
    - The conversation history is getting too long
    
    Returns:
        A summary of what was compacted and what was preserved.
    """
    try:
        # Load current state
        current_state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                current_state = json.load(f)
        
        # Build compact summary
        compact_summary = {
            "compacted_at": datetime.now().isoformat(),
            "summary": "Context compacted. Key information preserved below.",
            "preserved_keys": [],
            "recent_summary": "No recent activity summary available."
        }
        
        # Extract and preserve key information
        if "last_instruction" in current_state:
            compact_summary["recent_summary"] = f"Last instruction: {current_state['last_instruction']}"
            compact_summary["preserved_keys"].append("last_instruction")
            del current_state["last_instruction"]
        
        # Preserve any other important keys (customizable based on use case)
        for key in ["current_file", "pending_tasks", "project_context"]:
            if key in current_state:
                compact_summary[f"_{key}"] = current_state[key]
                compact_summary["preserved_keys"].append(key)
                del current_state[key]
        
        # Save compact state
        with open(COMPACT_STATE_FILE, 'w') as f:
            json.dump(compact_summary, f, indent=2)
        
        # Clear current state (keep only minimal info)
        current_state["last_compacted"] = datetime.now().isoformat()
        if compact_summary["preserved_keys"]:
            current_state["compacted_info"] = compact_summary["recent_summary"]
        
        with open(STATE_FILE, 'w') as f:
            json.dump(current_state, f, indent=2)
        
        # Build response
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
    
    This returns the summary saved when compact_state() was called.
    Use this to understand what work was in progress before a compact.
    
    Returns:
        The compacted state summary or message if none exists.
    """
    try:
        if not COMPACT_STATE_FILE.exists():
            return "No compacted state found. The CLI may be running for the first time or state has not been compacted."
        
        with open(COMPACT_STATE_FILE, 'r') as f:
            compact_state = json.load(f)
        
        # Format the response
        lines = [
            f"Compacted at: {compact_state.get('compacted_at', 'Unknown')}",
            f"Summary: {compact_state.get('summary', 'N/A')}",
        ]
        
        if 'recent_summary' in compact_state:
            lines.append(f"Recent work: {compact_state['recent_summary']}")
        
        if 'preserved_keys' in compact_state and compact_state['preserved_keys']:
            lines.append(f"Preserved information: {', '.join(compact_state['preserved_keys'])}")
        
        # Include any custom preserved data
        for key in compact_state:
            if key.startswith('_'):
                lines.append(f"{key[1:]}: {compact_state[key]}")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"Error reading compacted state: {str(e)}"


@llm.tool
def clear_compact_state():
    """Clear the compacted state file.
    
    Use this when you want to completely reset the compact state.
    
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
