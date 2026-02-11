"""Skill listing tool for Mirascope CLI.

This module provides tools for listing skills and getting skill information.
"""

from mirascope import llm
from ..skills.manager import get_skill_manager, get_skill_info as manager_get_skill_info


@llm.tool
def list_skills() -> str:
    """List all available skills in the system.
    
    Use this tool when the user asks about available capabilities or wants to
    see what skills are loaded in the system.
    
    Returns:
        Formatted list of available skills with descriptions
    """
    manager = get_skill_manager()
    return manager.list_all_skills()


@llm.tool
def get_skill_info(skill_name: str) -> str:
    """Get detailed information about a specific skill.
    
    Use this tool when the user wants to understand how to use a particular
    skill or what commands it supports.
    
    Args:
        skill_name: Name of the skill to look up
        
    Returns:
        Detailed skill information including description, allowed tools,
        and preview of available references
    """
    return manager_get_skill_info(skill_name)


@llm.tool
def skill_search(keyword: str) -> str:
    """Search for skills by keyword.
    
    Use this tool when the user describes a capability but doesn't know
    which skill provides it.
    
    Args:
        keyword: Keyword to search for in skill names and descriptions
        
    Returns:
        List of matching skills with descriptions
    """
    manager = get_skill_manager()
    results = manager.find_skills_by_keyword(keyword)
    
    if not results:
        return f"No skills found matching '{keyword}'. Try a different keyword."
    
    output = f"Skills matching '{keyword}':\n\n"
    for skill in results:
        output += f"  - {skill['name']}: {skill.get('description', 'N/A')}\n"
    
    return output
