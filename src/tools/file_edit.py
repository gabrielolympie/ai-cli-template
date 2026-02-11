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
def file_edit(path: str, start_line: int, end_line: int | None, new_content: str):
    """Edit a file by replacing lines with new content.
    
    Args:
        path: The file path (can be relative to current directory or absolute)
        start_line: The first line to replace (1-indexed)
        end_line: The last line to replace (1-indexed, inclusive; if None, replaces only start_line)
        new_content: The new content to insert (can span multiple lines)
    
    Returns:
        A message confirming the edit or an error if it failed.
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

        if start_idx < 0 or start_idx >= len(lines):
            return f"Error: start_line {start_line} is out of range (file has {len(lines)} lines)"

        # Handle end_line
        if end_line is None:
            end_idx = start_idx + 1
        else:
            end_idx = end_line

        # Clamp end_idx
        end_idx = min(end_idx, len(lines))

        if start_idx >= end_idx:
            return f"Error: Invalid range - start_line {start_line} must be before end_line {end_idx}"

        # Split new content into lines
        new_lines = new_content.split('\n')

        # Remove trailing empty line if new_content ended with newline
        if new_content.endswith('\n') and new_lines and new_lines[-1] == '':
            new_lines = new_lines[:-1]

        # Build new file content
        new_lines_list = lines[:start_idx] + [line + '\n' for line in new_lines] + lines[end_idx:]

        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines_list)

        return f"File edited successfully at {path}: replaced lines {start_line}-{end_idx} with new content."
    
    except Exception as e:
        return f"Error editing file at {path}: {str(e)}"
