from mirascope import llm
import re
import subprocess

from base_cli.tools._validators import validate_git_repo


@llm.tool
def git_revert_to_commit(commit_hash: str) -> str:
    """Hard reset to a specific commit and force push.

    WARNING: This rewrites history and discards all changes after the target commit.
    Use with extreme caution. Always commit current work before reverting.

    Args:
        commit_hash: The commit hash to revert to (7-40 alphanumeric characters)

    Returns:
        Confirmation of the revert or error message.
    """
    is_valid, error_message = validate_git_repo()
    if not is_valid:
        return error_message

    # Validate commit hash format
    if not re.match(r'^[a-fA-F0-9]{7,40}$', commit_hash):
        return f"Error: Invalid commit hash format '{commit_hash}'. Expected 7-40 hex characters."

    try:
        # git reset --hard
        reset_result = subprocess.run(
            ["git", "reset", "--hard", commit_hash],
            capture_output=True, text=True, timeout=30
        )
        if reset_result.returncode != 0:
            return f"Error during git reset: {reset_result.stderr.strip()}"

        # git push --force
        push_result = subprocess.run(
            ["git", "push", "--force"],
            capture_output=True, text=True, timeout=60
        )
        if push_result.returncode != 0:
            return f"Reset succeeded but force push failed: {push_result.stderr.strip()}"

        return f"Successfully reverted to commit {commit_hash} and force pushed."
    except subprocess.TimeoutExpired:
        return "Error: Git operation timed out"
    except Exception as e:
        return f"Error during git revert: {str(e)}"


__tool_category__ = "git"
__tools__ = [git_revert_to_commit]
