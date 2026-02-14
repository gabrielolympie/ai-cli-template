from mirascope import llm
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import utilities for model and prompt loading
from src.utils.load_model import get_model
from src.utils.load_prompts import load_base_prompt, load_model_config_section, load_claude_md
from src.utils.multiline_input import multiline_input

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.tools.screenshot import screenshot
from src.tools.plan import plan
from src.tools.summarize_conversation import summarize_conversation, generate_conversation_summary
from src.tools.browse_internet import browse_internet
from src.tools.estimate_tokens import estimate_tokens_from_messages, format_token_estimate
from src.tools.clarify import clarify

# Skill Management
from src.utils.skills.manager import get_skill_manager, SkillManager

# Initialize skill manager on startup
skill_manager: SkillManager = get_skill_manager()
skill_manager.load_skills()

# Generate skill inventory for system prompt
skill_inventory = skill_manager.generate_prompt_context()
skill_writer_guide = skill_manager.generate_skill_writer_guide()

# Load configuration and model using utils
model, config = get_model()

def cli():
    """Main CLI loop for the assistant."""
    # Load base prompt (includes PERSONA, AGENT, and SYSTEM)
    base_prompt = load_base_prompt()
    claude_md = load_claude_md()

    # Build system prompt with all components
    system_prompt = base_prompt + claude_md + "\n\n" + load_model_config_section(config)

    # Add skill inventory if available
    if skill_inventory:
        system_prompt += "\n\n" + skill_inventory

    # Add skill writer guide for documentation
    if skill_writer_guide:
        system_prompt += "\n\n" + skill_writer_guide

    print("Welcome to the Custom CLI Assistant! Type your commands below.")
    print("  - Press Alt + Enter for new lines")
    print("  - Press Enter to submit")
    print("  - Press Ctrl+C to cancel input")
    print("  - Type '/quit', '/exit', or '/q' to exit")
    print("  - Type '/reset' to clear conversation history and restart")
    print("  - Type '/compact' to summarize conversation, clear history, and preserve context")
    print()

    messages = [
        llm.messages.system(system_prompt),
    ]

    while True:
        try:
            user_input = multiline_input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower().strip() in ['/quit', '/exit', '/q']:
            print("Goodbye!")
            break


        if user_input.lower().strip() == '/reset':
            print("\n🔄 Conversation history cleared. Restarting with initial configuration...\n")
            messages = [
                llm.messages.system(system_prompt),
            ]
            continue

        if user_input.lower().strip() == '/compact':
            print("\n🔄 Compacting conversation history...\n")
            
            # Generate summary of conversation
            summary = generate_conversation_summary(messages)
            
            print("📝 Conversation summary:")
            print(summary)
            print()
            
            # Reset messages with system prompt and summary
            messages = [
                llm.messages.system(system_prompt),
                llm.messages.user(f"Previous conversation compacted. Here's a summary of what we've discussed so far:\n\n{summary}\n\nYou can now continue the conversation from this point.")
            ]
            print("✅ Conversation compacted and history cleared.\n")
            continue
        messages.append(llm.messages.user(user_input))

        response = model.stream(
            messages,
            tools=[
                file_create,
                file_read,
                file_edit,
                execute_bash,
                plan,
                screenshot,
                browse_internet,
                clarify,
                summarize_conversation,
                # Skill tools will be added dynamically
            ],
        )

        while True:  # The Agent Loop
            # Process tool calls
            clarify_responses = []  # Collect clarify tool responses
            interrupted = False

            try:
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

                            # Handle clarify tool specially - prompt user for input
                            if tool_call.name == "clarify":
                                # Parse args if it's a JSON string
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                question = args.get("question", "Clarifying question?")
                                print(f"\n❓ CLARIFYING QUESTION:")
                                print(f"{question}")
                                print()
                                try:
                                    user_response = multiline_input("Your answer: ")
                                    clarify_responses.append(
                                        llm.ToolOutput(id=tool_call.id, name=tool_call.name, result=f"User response: {user_response}")
                                    )
                                except (EOFError, KeyboardInterrupt):
                                    print("\nClarification cancelled.")
                                    clarify_responses.append(
                                        llm.ToolOutput(id=tool_call.id, name=tool_call.name, result="Clarification cancelled by user.")
                                    )
                            else:
                                # Print other tool calls normally
                                border = "=" * 80
                                tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                                # Parse args if it's a JSON string
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                tool_args = json.dumps(args, indent=2, ensure_ascii=False)
                                print(f"\n{border}")
                                print(f"{tool_header}")
                                print(f"Args:")
                                print(f"{tool_args}")
                                print(f"{border}\n")
            except KeyboardInterrupt:
                interrupted = True
                print("\n\n⚠️  Generation interrupted by user.\n")

            if interrupted:
                # Preserve partial context: response.messages contains
                # whatever was accumulated before the interruption
                try:
                    messages = response.messages
                except Exception:
                    # If messages aren't available from partial response,
                    # add a synthetic assistant message with what we had
                    messages.append(llm.messages.assistant("[Response interrupted by user]"))
                break

            # Execute clarify responses if any
            if clarify_responses:
                response = response.resume(clarify_responses)
                continue  # Continue the loop with the clarified response

            # Check if there are any tool calls to execute
            if response.tool_calls:
                tool_outputs = response.execute_tools()

                # Check for screenshot tools with image data and LLM supports images
                llm_config = config.get("llm", {})
                supports_images = llm_config.get("support_image", False)

                response = response.resume(tool_outputs)
            else:
                break

        if not interrupted:
            messages = response.messages

        # Display token estimate at the end of each turn
        if not interrupted:
            token_count = estimate_tokens_from_messages(messages)
            max_tokens = config["llm"]["context_size"]
            print()
            print(f"📊 Context window usage: {format_token_estimate(token_count, max_tokens)}")
            print()

if __name__ == "__main__":
    cli()
