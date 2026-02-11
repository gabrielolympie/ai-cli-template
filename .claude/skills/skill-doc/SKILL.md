---
name: skill-doc
description: System documentation for skill management and CLI usage
allowed-tools: Bash(cat:*)
---

# Skill Documentation

This skill provides access to system documentation and skill writing guides.

## Quick Start

```bash
# List available documentation
cat SKILL_SYSTEM_SUMMARY.md

# View skill writer guide
cat SKILL_WRITER_GUIDE.md

# View system documentation
cat README_SKILLS.md 2>/dev/null || cat SKILLS_README.md 2>/dev/null
```

## Available Documentation

| File | Purpose |
|------|---------|
| `SKILL_SYSTEM_SUMMARY.md` | Quick reference for skill system |
| `SKILL_WRITER_GUIDE.md` | Complete guide for writing skills |
| `README_SKILLS.md` | Technical documentation |

## SKILL.md Format

Skills use YAML frontmatter followed by markdown content:

```yaml
---
name: skill-name
description: What it does
allowed-tools: Bash(cli-name:*)
---
```

### Metadata Fields

- **name** (required): Skill identifier
- **description** (required): Short description for the skill inventory
- **allowed-tools** (required): Tools exposed (format: `Bash(tool:*)`)

## How to Write Skills

### Quick Start

1. Create directory: `.claude/skills/your-skill/`
2. Create `SKILL.md` with YAML frontmatter
3. Add markdown documentation
4. (Optional) Create `references/` folder for detailed docs

### Skill Structure

```
.clause/skills/
└── your-skill-name/
    ├── SKILL.md          # Main skill definition (required)
    └── references/       # Reference documentation (optional)
        ├── usage.md
        ├── examples.md
        └── advanced.md
```

### Command Convention

Skills should follow a consistent CLI pattern:
- Use `your-cli command` for core functionality
- Support subcommands for organization
- Use flags for options: `--flag=value`
- Provide `help` and `list` commands

## Best Practices

1. Clear, descriptive names
2. Follow Unix conventions for CLI commands
3. Provide examples in reference docs
4. Document common errors and solutions
5. Consider versioning if needed

## System Architecture

The skill management system includes:
- `src/skills/loader.py` - Skill loading and parsing
- `src/skills/manager.py` - SkillManager class
- `src/tools/skill_list.py` - Skill management tools

## Available Tools

- `list_skills()` - List all skills
- `get_skill_info(skill_name)` - Get skill details
- `skill_search(keyword)` - Search skills

## Testing

```bash
python test_skills.py
```

## Integration

Skills are automatically:
- Loaded from `.claude/skills/` on startup
- Included in system prompt
- Available via skill tools
