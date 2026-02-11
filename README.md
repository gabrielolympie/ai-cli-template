# Mirascope CLI

A minimal, hackable CLI assistant built with [Mirascope](https://github.com/mirascope/mirascope).

---

## ⚠️ Warning: Sandbox Environment

This CLI executes arbitrary commands with full system access. Use responsibly.

---

## Quick Start

```bash
git clone git@github.com-personal:gabrielolympie/cli-template.git
cd cli-template
./install.sh
python mirascope_cli.py
```

Edit `mirascope_cli.py` to configure your LLM:

```python
os.environ['OPENAI_API_KEY'] = "sk-..."
os.environ['OPENAI_API_BASE'] = "http://localhost:5000/v1"
```

---

## Capabilities

| Feature | Description |
|---------|-------------|
| **File Ops** | Create, read, edit files |
| **Bash** | Execute commands (60s timeout) |
| **Planning** | Break down complex tasks |
| **Browser** | Automate web interactions via Playwright |
| **Web** | Browse and extract webpage content |
| **Skills** | Extend via modular capabilities |

---

## Key Files

```
mirascope_cli.py        # Main entry point
prompts/system.md       # System prompt
src/tools/              # Tool definitions
src/skills/             # Skill system
.claude/skills/         # User skills
```

---

## Skill System

The skill management system (derived from [Claude Code](https://github.com/anthropics/claude-code)) lets you extend capabilities via YAML-configured skills.

**Example skills:**
- `playwright-cli` - Browser automation
- `skill-doc` - Skill documentation

---

## License

MIT
