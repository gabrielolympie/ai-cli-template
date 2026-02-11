from mirascope import llm
import subprocess

from base_cli.tools._validators import validate_git_repo


@llm.tool
def git_history(limit: int = 10, show_hashes: bool = True, show_author: bool = True, show_date: bool = True) -> str:
    """Get git commit history.

    Args:
        limit: Maximum number of commits to show (default: 10)
        show_hashes: Include commit hashes (default: True)
        show_author: Include author names (default: True)
        show_date: Include commit dates (default: True)

    Returns:
        Formatted list of recent commits.
    """
    is_valid, error_message = validate_git_repo()
    if not is_valid:
        return error_message

    try:
        format_parts = []
        if show_hashes:
            format_parts.append("%h")
        format_parts.append("%s")
        if show_author:
            format_parts.append("%an")
        if show_date:
            format_parts.append("%ad")

        fmt = " | ".join(format_parts)
        result = subprocess.run(
            ["git", "log", f"--format={fmt}", "--date=short", f"-n{limit}"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip() or "No commits found."
    except subprocess.TimeoutExpired:
        return "Error: git log timed out after 30 seconds"
    except Exception as e:
        return f"Error getting git history: {str(e)}"


__tool_category__ = "git"
__tools__ = [git_history]
