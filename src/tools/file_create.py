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
def file_create(path: str, content: str):
    """Create a new file with the given content.
    
    Args:
        path: The file path (can be relative to current directory or absolute)
        content: The content to write to the file
    
    Returns:
        A message confirming the file creation or an error if it failed.
    """
    # Validate path is within project root
    is_valid, error_message = _validate_path(path)
    if not is_valid:
        return error_message
    
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"File created successfully at: {path}"
    except Exception as e:
        return f"Error creating file at {path}: {str(e)}"
