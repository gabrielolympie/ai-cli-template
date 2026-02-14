---
name: tool-dev
description: Complete guide for creating, removing, and editing tools in the CLI. Use when modifying tool functionality, adding new tools, or understanding tool architecture.
allowed-tools: None
---

# Tool Development Guide

This guide covers everything about creating, modifying, and managing tools in the CLI.

## Quick Start

```bash
# View existing tools
ls src/tools/

# Create a new tool
# 1. Create the file in src/tools/
# 2. Register in config.yaml
# 3. Add to ALL_TOOLS in mirascope_cli.py
```

---

## Tool Architecture

### How Tools Work

1. **Tool Definition**: Each tool is a Python function in `src/tools/` decorated with mirascope
2. **Tool Registration**: Tools are registered in `config.yaml` under the `tools` section
3. **Tool Filtering**: The `ALL_TOOLS` dict maps tool names to their functions
4. **Dynamic Loading**: `get_enabled_tools()` filters tools based on config

### Key Files

| File | Purpose |
|------|---------|
| [`src/tools/*.py`](src/tools/) | Individual tool implementations |
| [`mirascope_cli.py`](mirascope_cli.py) | Main CLI, tool filtering, and ALL_TOOLS dict |
| [`src/utils/load_model.py`](src/utils/load_model.py) | Config loading with default tool settings |

---

## Creating a New Tool

### Step 1: Create the Tool File

Create a new file in `src/tools/your_tool.py`:

```python
from mirascope import BaseTool
from pydantic import Field

class YourTool(BaseTool):
    """Tool description that appears in system prompt."""

    # Tool parameters (use Field for validation)
    parameter: str = Field(
        description="Description of what this parameter does"
    )

    # The actual tool implementation
    def call(self) -> str:
        """Execute the tool logic."""
        result = do_something(self.parameter)
        return f"Tool executed successfully: {result}"

# Export for mirascope_cli.py
your_tool = YourTool
```

### Step 2: Update config.yaml

Add your tool to the default config in [`src/utils/load_model.py`](src/utils/load_model.py:26-36):

```python
"tools": {
    "your_tool": True,  # <-- Add this
    # ... existing tools
}
```

### Step 3: Register in ALL_TOOLS

Import and register in [`mirascope_cli.py`](mirascope_cli.py:42-53):

```python
from src.tools.your_tool import your_tool

ALL_TOOLS = {
    "your_tool": your_tool,  # <-- Add this
    # ... existing tools
}
```

### Step 4: Pass to model.stream()

The tool is now automatically included via `get_enabled_tools()`:

```python
response = model.stream(
    messages,
    tools=get_enabled_tools(),  # Includes your tool if enabled in config
)
```

---

## Tool Configuration

### Enable/Disable Tools

Edit `config.yaml`:

```yaml
tools:
  file_create: true    # Enabled
  screenshot: false     # Disabled
  your_tool: true       # Enabled
```

### Default Tool Settings

Default tool states are defined in [`src/utils/load_model.py`](src/utils/load_model.py:26-36):

```python
"tools": {
    "file_create": True,
    "file_read": True,
    "file_edit": True,
    "execute_bash": True,
    "screenshot": True,
    "plan": True,
    "browse_internet": True,
    "clarify": True,
    "summarize_conversation": True,
}
```

---

## Removing a Tool

### Complete Removal

1. **Delete the tool file**: `rm src/tools/unwanted_tool.py`
2. **Remove from ALL_TOOLS**: Delete the entry in [`mirascope_cli.py`](mirascope_cli.py)
3. **Remove import**: Delete the import statement
4. **(Optional) Remove from defaults**: Delete from [`src/utils/load_model.py`](src/utils/load_model.py)

### Temporary Disabling

Easier - just disable in `config.yaml`:

```yaml
tools:
  unwanted_tool: false  # Disabled but code remains
```

---

## Editing an Existing Tool

### Modify Tool Logic

Edit the tool file in `src/tools/your_tool.py`:

```python
# Before
def call(self, query: str) -> str:
    return f"Search: {query}"

# After - add a parameter
def call(self, query: str, limit: int = 10) -> str:
    results = search(query, max_results=limit)
    return f"Found {len(results)} results"
```

### Change Tool Description

Update the docstring - this appears in the system prompt:

```python
class YourTool(BaseTool):
    """New, improved description that the LLM will see."""
```

### Add Parameter Validation

Use pydantic Field for validation:

```python
from pydantic import Field, field_validator

class YourTool(BaseTool):
    count: int = Field(
        description="Number of items",
        ge=1,  # Must be >= 1
        le=100  # Must be <= 100
    )

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v > 50:
            raise ValueError("count must be <= 50 for this operation")
        return v
```

---

## Tool Naming Conventions

| Pattern | Example | When to Use |
|---------|----------|--------------|
| `verb_noun` | `file_read`, `file_edit` | Operations on resources |
| `noun_verb` | `screenshot` | Primary action is clear |
| `concept` | `plan`, `clarify` | Abstract capabilities |

---

## Common Tool Patterns

### File Operations

```python
class file_create(BaseTool):
    """Create or overwrite a file with content."""

    file_path: str = Field(description="Absolute path to the file")
    content: str = Field(description="Content to write to the file")

    def call(self) -> str:
        from pathlib import Path
        Path(self.file_path).write_text(self.content)
        return f"Created {self.file_path}"
```

### Shell Commands

```python
class execute_bash(BaseTool):
    """Execute a bash command in the terminal."""

    command: str = Field(description="Command to execute")
    timeout: int = Field(default=120, description="Timeout in seconds")

    def call(self) -> str:
        import subprocess
        result = subprocess.run(
            self.command,
            shell=True,
            capture_output=True,
            timeout=self.timeout
        )
        return result.stdout or result.stderr
```

### Data Processing

```python
class estimate_tokens(BaseTool):
    """Estimate token count from messages."""

    def call(self, messages: list) -> str:
        total = sum(len(str(m)) for m in messages) // 4
        return f"Estimated tokens: {total}"
```

---

## Testing Tools

```bash
# Test the CLI with your tool
python mirascope_cli.py

# Test via Python
python -c "from src.tools.your_tool import your_tool; print(your_tool().call(param='value'))"
```

---

## Troubleshooting

### Tool Not Appearing

1. Check `config.yaml` has `tool_name: true`
2. Verify tool is in `ALL_TOOLS` dict
3. Ensure tool file imports without errors

### Tool Parameters Not Working

1. Check Field descriptions are clear
2. Verify parameter types match (str, int, etc.)
3. Add validation errors are descriptive

### Import Errors

1. Check file is in `src/tools/`
2. Verify file name matches import (underscores for hyphens)
3. Check for circular dependencies

---

## See Also

- [Skill Development Guide](skill-doc:) - Creating skills vs tools
- [config.yaml](config.yaml) - Tool configuration
- [mirascope_cli.py](mirascope_cli.py:42-87) - Tool registration and filtering
