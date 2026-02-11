from mirascope import llm
import os

from base_cli.tools._validators import validate_path


@llm.tool
def file_create(path: str, content: str):
    """Create a new file with the given content.

    Args:
        path: The file path (can be relative to current directory or absolute)
        content: The content to write to the file

    Returns:
        A message confirming the file creation or an error if it failed.
    """
    is_valid, error_message = validate_path(path)
    if not is_valid:
        return error_message

    try:
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"File created successfully at: {path}"
    except Exception as e:
        return f"Error creating file at {path}: {str(e)}"


__tool_category__ = "file_ops"
__tools__ = [file_create]
