from mirascope import llm
import subprocess


@llm.tool
def execute_bash(command: str):
    """Execute a bash command and return the output.
    
    Args:
        command: The bash command to execute (single string, no shell interpretation of arguments)
    
    Returns:
        The combined stdout and stderr output from the command.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = []
        if result.stdout:
            output.append(result.stdout.rstrip('\n'))
        if result.stderr:
            output.append(f"stderr: {result.stderr.rstrip('\n')}")
        
        if result.returncode != 0:
            output.append(f"[Command exited with code {result.returncode}]")
        
        return "\n".join(output) if output else "Command executed successfully (no output)"
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"
