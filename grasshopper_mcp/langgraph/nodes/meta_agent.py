"""
Meta-Agent Node - 元代理節點

彈性架構師 Agent，動態創建工具和配置。

四種核心操作：
1. search_tool: 搜索 Joseki 和現有工具
2. create_tool: 從描述生成新工具
3. ask_user: 詢問澄清 (單一問題原則)
4. create_agent_config: 組裝 Agent 配置

工具存儲位置：Joseki Library (整合到現有模式庫)
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid
import json

from ..state import (
    DesignState,
    GeneratedTool,
    AgentConfig,
)


class MetaAgentOperation:
    """Meta-Agent operation types"""
    SEARCH_TOOL = "search_tool"
    CREATE_TOOL = "create_tool"
    ASK_USER = "ask_user"
    CREATE_AGENT_CONFIG = "create_agent_config"
    IDLE = "idle"


def meta_agent_node(state: DesignState) -> Dict[str, Any]:
    """
    Meta-Agent main node

    Dynamic tool and agent creation for novel tasks.

    Args:
        state: Current DesignState

    Returns:
        State updates
    """
    if not state.get("meta_agent_active"):
        return {"meta_agent_active": False}

    operation = state.get("meta_agent_operation") or MetaAgentOperation.SEARCH_TOOL
    topic = state.get("topic", "")

    if operation == MetaAgentOperation.SEARCH_TOOL:
        return _search_tool_operation(state, topic)
    elif operation == MetaAgentOperation.CREATE_TOOL:
        return _create_tool_operation(state, topic)
    elif operation == MetaAgentOperation.ASK_USER:
        return _ask_user_operation(state, topic)
    elif operation == MetaAgentOperation.CREATE_AGENT_CONFIG:
        return _create_agent_config_operation(state, topic)
    else:
        return _idle_operation(state)


def _search_tool_operation(state: DesignState, topic: str) -> Dict[str, Any]:
    """
    Search for existing tools and Joseki patterns

    Searches:
    - Joseki library
    - Generated tools
    - Component registry
    """
    # Search Joseki library
    joseki_matches = _search_joseki_library(topic)

    # Search previously generated tools
    generated_tools = state.get("generated_tools", [])
    tool_matches = _search_generated_tools(topic, generated_tools)

    # Combine results
    all_matches = joseki_matches + tool_matches

    if all_matches:
        # Found existing tools
        return {
            "retrieved_tools": all_matches,
            "meta_agent_operation": MetaAgentOperation.IDLE,
            "errors": state.get("errors", []) + [
                f"Meta-Agent: Found {len(all_matches)} relevant tools/patterns"
            ],
            "awaiting_confirmation": True,
            "confirmation_reason": "meta_agent_tool_found",
            "pending_decisions": state.get("pending_decisions", []) + [{
                "id": str(uuid.uuid4()),
                "question": _format_tool_selection(all_matches),
                "options": [
                    f"Use tool: {t.get('name', 'Unknown')}" for t in all_matches[:3]
                ] + ["Create new tool", "Search with different criteria"],
                "importance": "medium",
                "context": "Meta-Agent tool search results",
                "resolved": False,
                "chosen_option": None,
            }],
        }
    else:
        # No matches, need to create
        return {
            "meta_agent_operation": MetaAgentOperation.ASK_USER,
            "errors": state.get("errors", []) + [
                "Meta-Agent: No existing tools found, gathering requirements"
            ],
        }


def _create_tool_operation(state: DesignState, topic: str) -> Dict[str, Any]:
    """
    Create a new tool dynamically

    Generates:
    - Tool definition
    - Input/output schema
    - Implementation (as Joseki pattern)
    """
    requirements = state.get("requirements", "")

    # Generate tool spec
    tool = _generate_tool_spec(topic, requirements)

    # Save to Joseki library
    joseki_id = _save_to_joseki(tool)
    tool["joseki_id"] = joseki_id

    generated_tools = state.get("generated_tools", [])

    return {
        "generated_tools": generated_tools + [tool],
        "meta_agent_operation": MetaAgentOperation.IDLE,
        "meta_agent_active": False,
        "intent_type": "workflow",  # Transition to workflow
        "errors": state.get("errors", []) + [
            f"Meta-Agent: Created tool '{tool['name']}' (joseki: {joseki_id})"
        ],
        "awaiting_confirmation": True,
        "confirmation_reason": "meta_agent_tool_created",
        "pending_decisions": state.get("pending_decisions", []) + [{
            "id": str(uuid.uuid4()),
            "question": f"I've created a new tool:\n\n{_format_tool_details(tool)}\n\nWould you like to use it?",
            "options": ["Use this tool", "Modify tool", "Cancel"],
            "importance": "high",
            "context": "Meta-Agent tool creation",
            "resolved": False,
            "chosen_option": None,
        }],
    }


def _ask_user_operation(state: DesignState, topic: str) -> Dict[str, Any]:
    """
    Ask user for clarification

    Single question principle: one focused question
    """
    # Determine what we need to know
    requirements = state.get("requirements", "")

    if not requirements:
        question = (
            f"I need to create a custom tool for '{topic}'. "
            "Could you describe:\n"
            "1. What inputs should it accept?\n"
            "2. What output should it produce?"
        )
    else:
        question = (
            f"Based on your requirements for '{topic}':\n"
            f"{requirements[:200]}...\n\n"
            "Is this correct? Any adjustments needed?"
        )

    return {
        "meta_agent_operation": MetaAgentOperation.CREATE_TOOL,  # Next operation
        "awaiting_confirmation": True,
        "confirmation_reason": "meta_agent_clarification",
        "pending_decisions": state.get("pending_decisions", []) + [{
            "id": str(uuid.uuid4()),
            "question": question,
            "options": ["Confirm and proceed", "Provide more details", "Cancel"],
            "importance": "high",
            "context": "Meta-Agent clarification",
            "resolved": False,
            "chosen_option": None,
        }],
    }


def _create_agent_config_operation(state: DesignState, topic: str) -> Dict[str, Any]:
    """
    Create an agent configuration

    Assembles:
    - System prompt
    - Available tools
    - Confidence threshold
    """
    generated_tools = state.get("generated_tools", [])
    tool_names = [t["name"] for t in generated_tools]

    config = AgentConfig(
        name=f"Custom Agent for {topic}",
        description=f"Specialized agent for handling {topic} tasks",
        tools=tool_names,
        system_prompt=_generate_system_prompt(topic, generated_tools),
        confidence_threshold=0.7,
    )

    agent_configs = state.get("agent_configs", [])

    return {
        "agent_configs": agent_configs + [config],
        "meta_agent_operation": MetaAgentOperation.IDLE,
        "meta_agent_active": False,
        "errors": state.get("errors", []) + [
            f"Meta-Agent: Created agent config '{config['name']}'"
        ],
    }


def _idle_operation(state: DesignState) -> Dict[str, Any]:
    """Exit meta-agent mode"""
    return {
        "meta_agent_active": False,
        "meta_agent_operation": None,
        "intent_type": "workflow",
    }


# === Search Functions ===

def _search_joseki_library(topic: str) -> List[Dict[str, Any]]:
    """Search Joseki library for relevant patterns"""
    # In full implementation, load from joseki/library/
    # For now, return template matches

    joseki_path = Path(__file__).parent.parent.parent / "joseki" / "library"

    matches = []

    # Keyword-based matching
    keywords = topic.lower().split()

    # Predefined joseki patterns
    known_patterns = [
        {"name": "table-basic", "keywords": ["table", "furniture"]},
        {"name": "chair-basic", "keywords": ["chair", "furniture", "seat"]},
        {"name": "box-parametric", "keywords": ["box", "cube", "parametric"]},
        {"name": "cylinder-array", "keywords": ["cylinder", "array", "pattern"]},
    ]

    for pattern in known_patterns:
        if any(kw in keywords for kw in pattern["keywords"]):
            matches.append({
                "name": pattern["name"],
                "type": "joseki",
                "description": f"Joseki pattern: {pattern['name']}",
                "source": "joseki_library",
            })

    return matches


def _search_generated_tools(topic: str, tools: List[GeneratedTool]) -> List[Dict[str, Any]]:
    """Search previously generated tools"""
    matches = []
    keywords = set(topic.lower().split())

    for tool in tools:
        tool_keywords = set(tool.get("name", "").lower().split())
        tool_keywords.update(tool.get("description", "").lower().split())

        overlap = keywords & tool_keywords
        if overlap:
            matches.append({
                "name": tool["name"],
                "type": "generated_tool",
                "description": tool["description"],
                "joseki_id": tool.get("joseki_id"),
            })

    return matches


# === Tool Generation ===

def _generate_tool_spec(topic: str, requirements: str) -> GeneratedTool:
    """Generate a tool specification"""

    # Extract likely parameters from topic
    params = _extract_parameters(topic, requirements)

    return GeneratedTool(
        name=f"tool_{topic.replace(' ', '_').lower()}",
        description=f"Custom tool for: {topic}",
        input_schema={
            "type": "object",
            "properties": {
                param: {"type": "number", "description": f"Parameter: {param}"}
                for param in params
            },
            "required": params[:2] if len(params) >= 2 else params,
        },
        output_schema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "component_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
        implementation=_generate_implementation(topic, params),
        joseki_id=None,
        created_at=datetime.now().isoformat(),
    )


def _extract_parameters(topic: str, requirements: str) -> List[str]:
    """Extract likely parameters from topic and requirements"""
    combined = f"{topic} {requirements}".lower()

    # Common parametric design parameters
    param_keywords = {
        "width": ["width", "w", "寬"],
        "height": ["height", "h", "高"],
        "depth": ["depth", "d", "深"],
        "length": ["length", "len", "長"],
        "radius": ["radius", "r", "半徑"],
        "count": ["count", "number", "數量"],
        "spacing": ["spacing", "gap", "間距"],
    }

    found_params = []
    for param_name, keywords in param_keywords.items():
        if any(kw in combined for kw in keywords):
            found_params.append(param_name)

    # Default if none found
    if not found_params:
        found_params = ["width", "height", "depth"]

    return found_params


def _generate_implementation(topic: str, params: List[str]) -> str:
    """Generate tool implementation as pseudo-code"""
    lines = [
        f"# Tool: {topic}",
        f"# Parameters: {', '.join(params)}",
        "",
        "# Step 1: Create sliders",
    ]

    for i, param in enumerate(params):
        lines.append(f"slider_{param} = add_slider('{param}', col=0, row={i})")

    lines.extend([
        "",
        "# Step 2: Create geometry",
        "# (Specific geometry depends on topic)",
        "",
        "# Step 3: Connect parameters",
        "# Connect sliders to geometry inputs",
        "",
        "# Step 4: Return results",
        "return component_ids",
    ])

    return "\n".join(lines)


def _save_to_joseki(tool: GeneratedTool) -> str:
    """Save tool to Joseki library"""
    joseki_id = f"joseki_{uuid.uuid4().hex[:8]}"

    # In full implementation, save to joseki/library/
    # For now, just return the ID

    return joseki_id


# === Formatting ===

def _format_tool_selection(tools: List[Dict]) -> str:
    """Format tool list for selection"""
    lines = ["Found the following relevant tools:\n"]

    for i, tool in enumerate(tools, 1):
        lines.append(f"{i}. **{tool['name']}** ({tool['type']})")
        lines.append(f"   {tool['description']}")
        lines.append("")

    lines.append("Which would you like to use?")
    return "\n".join(lines)


def _format_tool_details(tool: GeneratedTool) -> str:
    """Format tool details for display"""
    return (
        f"**Name**: {tool['name']}\n"
        f"**Description**: {tool['description']}\n"
        f"**Inputs**: {json.dumps(tool['input_schema'], indent=2)}\n"
        f"**Implementation**:\n```\n{tool['implementation']}\n```"
    )


def _generate_system_prompt(topic: str, tools: List[GeneratedTool]) -> str:
    """Generate system prompt for custom agent"""
    tool_list = "\n".join(f"- {t['name']}: {t['description']}" for t in tools)

    return f"""You are a specialized agent for handling {topic} tasks.

Available tools:
{tool_list}

Guidelines:
1. Use the available tools to accomplish the task
2. Ask for clarification if requirements are unclear
3. Verify results before reporting completion
4. Log any errors or issues encountered
"""


# === Entry/Exit Utilities ===

def enter_meta_agent_mode(state: DesignState) -> Dict[str, Any]:
    """Initialize Meta-Agent mode"""
    return {
        "meta_agent_active": True,
        "meta_agent_operation": MetaAgentOperation.SEARCH_TOOL,
        "generated_tools": state.get("generated_tools", []),
        "agent_configs": state.get("agent_configs", []),
        "intent_type": "meta_agent",
    }


def exit_meta_agent_mode(state: DesignState) -> Dict[str, Any]:
    """Clean exit from Meta-Agent mode"""
    return {
        "meta_agent_active": False,
        "meta_agent_operation": None,
        "intent_type": "workflow",
    }
