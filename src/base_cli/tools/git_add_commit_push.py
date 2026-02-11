from mirascope import llm
import subprocess

from base_cli.tools._validators import validate_path, validate_git_repo


@llm.tool
def git_add_commit_push(files: list[str], message: str) -> str:
    """Add, commit, and push changes to git.

    Args:
        files: List of file paths to add and commit
        message: The commit message

    Returns:
        Summary of the git operations or error message.
    """
    is_valid, error_message = validate_git_repo()
    if not is_valid:
        return error_message

    # Validate all file paths
    for file_path in files:
        is_valid, error_message = validate_path(file_path)
        if not is_valid:
            return f"Invalid file path '{file_path}': {error_message}"

    try:
        # git add
        add_result = subprocess.run(
            ["git", "add"] + files,
            capture_output=True, text=True, timeout=30
        )
        if add_result.returncode != 0:
            return f"Error during git add: {add_result.stderr.strip()}"

        # git commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=30
        )
        if commit_result.returncode != 0:
            return f"Error during git commit: {commit_result.stderr.strip()}"

        # git push
        push_result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=60
        )
        if push_result.returncode != 0:
            return f"Committed but push failed: {push_result.stderr.strip()}"

        return f"Successfully added {len(files)} file(s), committed with message '{message}', and pushed."
    except subprocess.TimeoutExpired:
        return "Error: Git operation timed out"
    except Exception as e:
        return f"Error during git operations: {str(e)}"


__tool_category__ = "git"
__tools__ = [git_add_commit_push]
