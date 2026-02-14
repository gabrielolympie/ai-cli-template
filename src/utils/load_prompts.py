"""Shared utilities for loading prompt files."""

import os
from pathlib import Path


PROMPTS_DIR = "prompts"


def load_prompt(prompt_path: str) -> str:
    """Load a single prompt file. Returns empty string if file doesn't exist."""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_base_prompt() -> str:
    """Load and integrate PERSONA.md, AGENT.md, and SYSTEM.md into the system prompt."""
    # Load all three prompt components
    persona = load_prompt(os.path.join(PROMPTS_DIR, "PERSONA.md"))
    agent = load_prompt(os.path.join(PROMPTS_DIR, "AGENT.md"))
    system = load_prompt(os.path.join(PROMPTS_DIR, "SYSTEM.md"))

    # Integrate all prompts into a single system prompt
    parts = []
    if system:
        parts.append(system)
    if agent:
        parts.append(f"## AGENT MEMORY\n{agent}")
    if persona:
        parts.append(f"## PERSONA\n{persona}")
    return "\n\n".join(parts)


def load_model_config_section(config: dict) -> str:
    """Generate a model configuration section for the system prompt."""
    llm_config = config.get("llm", {})

    model_name = llm_config.get("model_name", "Unknown")
    provider = llm_config.get("provider", "Unknown")
    max_completion_tokens = llm_config.get("max_completion_tokens", "Unknown")
    context_size = llm_config.get("context_size", "Unknown")
    support_image = llm_config.get("support_image", False)
    support_audio_input = llm_config.get("support_audio_input", False)
    support_audio_output = llm_config.get("support_audio_output", False)

    return f"""
## MODEL CONFIGURATION

Your LLM configuration:
- **Model**: {model_name}
- **Provider**: {provider}
- **Max completion tokens**: {max_completion_tokens}
- **Context window size**: {context_size} tokens
- **Supports images**: {support_image}
- **Supports audio input**: {support_audio_input}
- **Supports audio output**: {support_audio_output}

Use this information to understand your capabilities and limitations.
""".strip()


def load_claude_md() -> str:
    """Load CLAUDE.md if present at the project root."""
    claude_path = os.path.join(os.getcwd(), "CLAUDE.md")
    if os.path.exists(claude_path):
        with open(claude_path, "r", encoding="utf-8") as f:
            return f"\n\n## ADDITIONAL PROJECT GUIDANCE\n{f.read()}"
    return ""


def load_plan_prompt() -> str:
    """Load the plan prompt template from PLAN.md, with fallback to default."""
    # Navigate to prompts/PLAN.md relative to project root
    project_root = os.getcwd()
    prompt_path = Path(project_root) / PROMPTS_DIR / "PLAN.md"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    # Fallback to default prompt if file not found
    return """You are an expert task planner. Create a detailed, step-by-step plan for the following task:

TASK: {task}

CURRENT CONTEXT: {current_context if current_context else "No specific context provided."}

AVAILABLE TOOLS/CAPABILITIES: {available_tools if available_tools else "File operations (create, read, edit), bash execution, git operations, planning."}

Please analyze this task and create a comprehensive plan that:
1. Breaks down the task into specific, actionable steps
2. Considers the current context and constraints
3. Uses the available tools effectively
4. Identifies potential challenges and how to address them
5. Prioritizes steps logically
6. Includes verification points

Format your response as a structured plan with numbered steps, each including:
- Step number and brief title
- Clear description of what needs to be done
- Which tools or approaches to use
- Any dependencies or prerequisites

Include an estimated complexity level (Low/Medium/High) at the end.
"""
