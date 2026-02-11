from mirascope import llm
import os

# Get the current working directory (hard constraint: operations limited to this folder)
# Use CWD as the root to avoid accidentally accessing files elsewhere
PROJECT_ROOT = os.getcwd()


def _validate_path(path: str) -> tuple[bool, str]:
    """Validate that a path is within the project root directory.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Convert relative path to absolute
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    
    # Normalize paths for comparison
    normalized_path = os.path.normpath(path)
    normalized_root = os.path.normpath(PROJECT_ROOT)
    
    # Check if path is within project root
    if not normalized_path.startswith(normalized_root + os.sep) and normalized_path != normalized_root:
        return False, f"Access denied: path '{path}' is outside the project directory '{PROJECT_ROOT}'"
    
    return True, ""


@llm.tool
def file_read(path: str, start_line: int = 1, end_line: int | None = None):
    """Read a file and return its content with line numbers.
    
    Args:
        path: The file path (can be relative to current directory or absolute)
        start_line: The first line to read (1-indexed, default: 1)
        end_line: The last line to read (1-indexed, inclusive; default: None = read to end)
    
    Returns:
        File content with line numbers formatted as "line_number: content".
    """
    # Validate path is within project root
    is_valid, error_message = _validate_path(path)
    if not is_valid:
        return error_message
    
    try:
        if not os.path.exists(path):
            return f"Error: File not found at {path}"

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Convert to 0-indexed
        start_idx = start_line - 1
        if start_idx < 0:
            start_idx = 0

        # Handle end_line
        if end_line is None:
            end_idx = len(lines)
        else:
            end_idx = end_line

        # Clamp indices
        start_idx = max(0, start_idx)
        end_idx = min(len(lines), end_idx)

        if start_idx >= end_idx:
            return f"File is empty or selected range is invalid (lines {start_line}-{end_line})"

        result = []
        for i in range(start_idx, end_idx):
            line_num = i + 1
            line_content = lines[i].rstrip('\n')
            result.append(f"{line_num}: {line_content}")

        return "\n".join(result)
    
    except Exception as e:
        return f"Error reading file at {path}: {str(e)}"
