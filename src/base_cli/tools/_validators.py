"""Shared validation utilities for CLI tools."""
import os
import subprocess

PROJECT_ROOT = os.getcwd()


def validate_path(path: str) -> tuple[bool, str]:
    """Validate that a path is within the project root directory.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    normalized_path = os.path.normpath(path)
    normalized_root = os.path.normpath(PROJECT_ROOT)

    if not normalized_path.startswith(normalized_root + os.sep) and normalized_path != normalized_root:
        return False, f"Access denied: path '{path}' is outside the project directory '{PROJECT_ROOT}'"

    return True, ""


def validate_git_repo() -> tuple[bool, str]:
    """Validate that we're inside a git repository.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, "Not inside a git repository."
        return True, ""
    except Exception as e:
        return False, f"Error checking git repo: {str(e)}"
