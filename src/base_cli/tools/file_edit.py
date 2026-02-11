from mirascope import llm
import os

from base_cli.tools._validators import validate_path


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
    is_valid, error_message = validate_path(path)
    if not is_valid:
        return error_message

    try:
        if not os.path.exists(path):
            return f"Error: File not found at {path}"

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start_idx = start_line - 1

        if start_idx < 0 or start_idx >= len(lines):
            return f"Error: start_line {start_line} is out of range (file has {len(lines)} lines)"

        if end_line is None:
            end_idx = start_idx + 1
        else:
            end_idx = end_line

        end_idx = min(end_idx, len(lines))

        if start_idx >= end_idx:
            return f"Error: Invalid range - start_line {start_line} must be before end_line {end_idx}"

        new_lines = new_content.split('\n')

        if new_content.endswith('\n') and new_lines and new_lines[-1] == '':
            new_lines = new_lines[:-1]

        new_lines_list = lines[:start_idx] + [line + '\n' for line in new_lines] + lines[end_idx:]

        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines_list)

        return f"File edited successfully at {path}: replaced lines {start_line}-{end_idx} with new content."

    except Exception as e:
        return f"Error editing file at {path}: {str(e)}"


__tool_category__ = "file_ops"
__tools__ = [file_edit]
