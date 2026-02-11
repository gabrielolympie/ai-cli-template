from mirascope import llm
import os
import json
from pathlib import Path

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.tools.restart_cli import restart_cli, STATE_FILE
from src.tools.compact_state import compact_state, get_compact_state, clear_compact_state, COMPACT_STATE_FILE
from src.tools.git_history import git_history
from src.tools.git_add_commit_push import git_add_commit_push
from src.tools.plan import plan
from src.tools.git_revert_to_commit import git_revert_to_commit

os.environ['OPENAI_API_KEY'] = "sk-010101"
os.environ['OPENAI_API_BASE'] = "http://localhost:5000/v1"  # Point to the local vLLM server

llm.register_provider(
    "openai:completions",
    scope="vllm/",
    base_url="http://localhost:5000/v1",
    api_key="vllm",  # required by client but unused
)

model = llm.Model(
    "vllm/vllm",
    # temperature=0.2,
    max_tokens=8196,
    # top_p=0.95,
    # top_k=20,
    thinking={"level": "high", "include_thoughts": True}
)


def _get_state_info() -> str:
    """Get information about stored state for display on startup."""
    if not STATE_FILE.exists():
        return ""
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        if state:
            keys = ", ".join(state.keys())
            return f"Keys: {keys}"
    except Exception:
        pass
    return ""


def load_base_prompt(prompt_path: str = "prompts/cli.md") -> str:
    """Load the base system prompt from a markdown file."""
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def load_claude_md() -> str:
    """Load CLAUDE.md if present at the project root."""
    claude_path = os.path.join(os.getcwd(), "CLAUDE.md")
    if os.path.exists(claude_path):
        with open(claude_path, "r", encoding="utf-8") as f:
            return f"\n\n## ADDITIONAL PROJECT GUIDANCE\n{f.read()}"
    return ""


def _check_auto_mode() -> tuple[bool, str | None]:
    """Check if CLI should run in auto mode from stored state.
    
    Returns:
        Tuple of (is_auto_mode, instruction)
    """
    if not STATE_FILE.exists():
        return False, None
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        if "last_instruction" in state:
            return True, state["last_instruction"]
    except Exception:
        pass
    
    return False, None


def _run_auto_mode(instruction: str, system_prompt: str):
    """Run the agent loop automatically with a given instruction (no user input)."""
    print(f"*** Auto mode: Processing instruction from state ***\n")
    print(f"Instruction: {instruction}\n")
    
    messages = [
        llm.messages.system(system_prompt),
        llm.messages.user(instruction),
    ]

    response = model.stream(
        messages,
        tools=[file_create, file_read, file_edit, execute_bash, restart_cli, compact_state, get_compact_state, clear_compact_state, git_history, git_add_commit_push, git_revert_to_commit, plan],
    )

    while True:  # The Agent Loop
        for stream in response.streams():
            match stream.content_type:
                case "text":
                    for chunk in stream:
                        print(chunk, flush=True, end="")
                    print("\n")
                case "thought":
                    border = "~" * 80
                    print(f"\n{border}")
                    print(f"🧠 THOUGHT")
                    print(f"{border}")
                    for chunk in stream:
                        print(chunk, flush=True, end="")
                    print(f"\n{border}\n")
                case "tool_call":
                    tool_call = stream.collect()
                    border = "=" * 80
                    tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                    tool_args = json.dumps(tool_call.args, indent=2, ensure_ascii=False)
                    print(f"\n{border}")
                    print(f"{tool_header}")
                    print(f"Args:")
                    print(f"{tool_args}")
                    print(f"{border}\n")

        if not response.tool_calls:
            break  # Agent is finished.

        response = response.resume(response.execute_tools())


def cli():
    """Main CLI loop for the assistant."""
    # Check for and display stored state
    state_info = _get_state_info()
    if state_info:
        print(f"*** Found stored state from previous session: {state_info} ***\n")

    # Check for auto mode (non-interactive execution from state)
    is_auto_mode, instruction = _check_auto_mode()
    
    # Build system prompt with optional CLAUDE.md
    system_prompt = load_base_prompt() + load_claude_md()
    
    # If auto mode, execute the instruction but continue to interactive mode
    if is_auto_mode:
        _run_auto_mode(instruction, system_prompt)
        print("\n*** Auto mode completed. Returning to interactive mode. ***")
        # Clear the last_instruction to prevent auto mode on next run
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            if "last_instruction" in state:
                del state["last_instruction"]
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
    
    print("Welcome to the Custom CLI Assistant! Type your commands below.")

    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        messages = [
            llm.messages.system(system_prompt),
            llm.messages.user(user_input),
        ]

        response = model.stream(
            messages,
            tools=[file_create, file_read, file_edit, execute_bash, restart_cli, compact_state, get_compact_state, clear_compact_state, git_history, git_add_commit_push, git_revert_to_commit, plan],
        )

        while True:  # The Agent Loop
            for stream in response.streams():
                match stream.content_type:
                    case "text":
                        for chunk in stream:
                            print(chunk, flush=True, end="")
                        print("\n")
                    case "thought":
                        border = "~" * 80
                        print(f"\n{border}")
                        print(f"🧠 THOUGHT")
                        print(f"{border}")
                        for chunk in stream:
                            print(chunk, flush=True, end="")
                        print(f"\n{border}\n")
                    case "tool_call":
                        tool_call = stream.collect()
                        border = "=" * 80
                        tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                        tool_args = json.dumps(tool_call.args, indent=2, ensure_ascii=False)
                        print(f"\n{border}")
                        print(f"{tool_header}")
                        print(f"Args:")
                        print(f"{tool_args}")
                        print(f"{border}\n")

            if not response.tool_calls:
                break  # Agent is finished.

            response = response.resume(response.execute_tools())


if __name__ == "__main__":
    cli()
