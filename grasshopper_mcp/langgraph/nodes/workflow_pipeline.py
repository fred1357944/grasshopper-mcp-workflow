"""
Workflow Pipeline Nodes - 工作流程管線節點

確定性四階段管線：
1. Intent Decomposition - 意圖分解為子任務
2. Tool Retrieval - 檢索相關工具/Joseki
3. Prompt Generation - 生成執行提示
4. Config Assembly - 組裝 placement_info.json

每階段有明確輸入輸出，支援漸進驗證。
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import uuid

from ..state import (
    DesignState,
    SubTask,
    WorkflowStage,
)


# === Stage 1: Intent Decomposition ===

def intent_decomposition_node(state: DesignState) -> Dict[str, Any]:
    """
    Stage 1: Decompose user intent into subtasks

    Breaks down high-level intent into actionable subtasks.
    Each subtask has clear inputs, outputs, and dependencies.

    Args:
        state: Current DesignState

    Returns:
        State updates with decomposed subtasks
    """
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    joseki_patterns = state.get("joseki_patterns", [])

    # Analyze intent and create subtasks
    subtasks = _decompose_intent(topic, requirements, joseki_patterns)

    # Build dependency graph
    dependency_order = _build_dependency_order(subtasks)

    return {
        "subtasks": subtasks,
        "current_stage": WorkflowStage.TOOL_RETRIEVAL.value,
        "workflow_stage_outputs": {
            **state.get("workflow_stage_outputs", {}),
            "decomposition": {
                "subtask_count": len(subtasks),
                "dependency_order": dependency_order,
                "topic": topic,
            }
        },
        "errors": state.get("errors", []) + [
            f"Workflow: Decomposed into {len(subtasks)} subtasks"
        ],
    }


def _decompose_intent(
    topic: str,
    requirements: str,
    joseki_patterns: List[Dict]
) -> List[SubTask]:
    """Decompose intent into subtasks based on topic and patterns"""
    subtasks = []

    # Common parametric design subtasks
    base_subtasks = [
        ("create_parameters", "Create parameter sliders", []),
        ("create_base_geometry", "Create base geometry primitives", ["create_parameters"]),
        ("apply_transformations", "Apply transformations to geometry", ["create_base_geometry"]),
        ("create_connections", "Connect components", ["apply_transformations"]),
        ("finalize_assembly", "Finalize assembly", ["create_connections"]),
    ]

    # Add joseki-specific subtasks if patterns exist
    if joseki_patterns:
        for pattern in joseki_patterns:
            pattern_name = pattern.get("name", "unknown")
            subtasks.append(SubTask(
                id=str(uuid.uuid4()),
                name=f"apply_joseki_{pattern_name}",
                description=f"Apply Joseki pattern: {pattern_name}",
                dependencies=[],
                status="pending",
                component_type="joseki",
                parameters={},
            ))

    # Add base subtasks
    for task_id, description, deps in base_subtasks:
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            name=task_id,
            description=description,
            dependencies=deps,
            status="pending",
            component_type="workflow",
            parameters={},
        ))

    return subtasks


def _build_dependency_order(subtasks: List[SubTask]) -> List[str]:
    """Build execution order based on dependencies"""
    # Simple topological sort
    name_to_task = {t["name"]: t for t in subtasks}
    visited = set()
    order = []

    def visit(task_name: str):
        if task_name in visited:
            return
        visited.add(task_name)

        task = name_to_task.get(task_name)
        if task:
            for dep in task.get("dependencies", []):
                visit(dep)
            order.append(task_name)

    for task in subtasks:
        visit(task["name"])

    return order


# === Stage 2: Tool Retrieval ===

def tool_retrieval_node(state: DesignState) -> Dict[str, Any]:
    """
    Stage 2: Retrieve relevant tools and Joseki patterns

    Searches:
    - Component registry
    - Joseki library
    - Generated tools (from Meta-Agent)

    Args:
        state: Current DesignState

    Returns:
        State updates with retrieved tools
    """
    topic = state.get("topic", "")
    subtasks = state.get("subtasks", [])
    generated_tools = state.get("generated_tools", [])

    # Retrieve tools for each subtask
    retrieved_tools = []

    for subtask in subtasks:
        tools = _retrieve_tools_for_subtask(subtask, generated_tools)
        retrieved_tools.extend(tools)

    # Search Joseki library
    joseki_matches = _search_joseki_for_topic(topic)

    return {
        "retrieved_tools": retrieved_tools,
        "joseki_patterns": joseki_matches,
        "current_stage": WorkflowStage.PROMPT_GENERATION.value,
        "workflow_stage_outputs": {
            **state.get("workflow_stage_outputs", {}),
            "tool_retrieval": {
                "tools_found": len(retrieved_tools),
                "joseki_matches": len(joseki_matches),
            }
        },
        "errors": state.get("errors", []) + [
            f"Workflow: Retrieved {len(retrieved_tools)} tools, {len(joseki_matches)} joseki patterns"
        ],
    }


def _retrieve_tools_for_subtask(
    subtask: SubTask,
    generated_tools: List[Dict]
) -> List[Dict]:
    """Retrieve tools relevant to a subtask"""
    tools = []
    task_name = subtask.get("name", "")

    # Map task types to component categories
    task_to_components = {
        "create_parameters": ["NumberSlider", "Panel"],
        "create_base_geometry": ["CenterBox", "Cylinder", "Sphere", "Rectangle"],
        "apply_transformations": ["Move", "Scale", "Rotate", "Orient"],
        "create_connections": ["MassAddition", "Division", "Negative"],
        "finalize_assembly": ["SolidUnion", "BrepJoin"],
    }

    components = task_to_components.get(task_name, [])
    for comp in components:
        tools.append({
            "name": comp,
            "type": "component",
            "subtask": task_name,
        })

    # Check generated tools
    for gen_tool in generated_tools:
        tool_name = gen_tool.get("name", "").lower()
        if task_name.lower() in tool_name:
            tools.append({
                "name": gen_tool["name"],
                "type": "generated",
                "subtask": task_name,
            })

    return tools


def _search_joseki_for_topic(topic: str) -> List[Dict]:
    """Search Joseki library for topic-related patterns"""
    # Keywords to pattern mapping
    pattern_keywords = {
        "table": ["furniture-table", "parametric-surface"],
        "chair": ["furniture-chair", "ergonomic-seat"],
        "box": ["primitive-box", "parametric-box"],
        "tower": ["vertical-stack", "modular-tower"],
        "cup": ["container-cylinder", "revolution-surface"],
        "seesaw": ["balance-mechanism", "pivot-rotation"],
    }

    matches = []
    topic_lower = topic.lower()

    for keyword, patterns in pattern_keywords.items():
        if keyword in topic_lower:
            for pattern in patterns:
                matches.append({
                    "name": pattern,
                    "matched_keyword": keyword,
                    "type": "joseki",
                })

    return matches


# === Stage 3: Prompt Generation ===

def prompt_generation_node(state: DesignState) -> Dict[str, Any]:
    """
    Stage 3: Generate execution prompts

    Creates structured prompts for component creation and connection.

    Args:
        state: Current DesignState

    Returns:
        State updates with generated prompts
    """
    topic = state.get("topic", "")
    subtasks = state.get("subtasks", [])
    retrieved_tools = state.get("retrieved_tools", [])
    joseki_patterns = state.get("joseki_patterns", [])

    # Generate prompts for each subtask
    prompts = []

    for subtask in subtasks:
        relevant_tools = [t for t in retrieved_tools if t.get("subtask") == subtask["name"]]
        prompt = _generate_prompt_for_subtask(subtask, relevant_tools, joseki_patterns)
        prompts.append(prompt)

    # Generate overall execution plan
    execution_plan = _generate_execution_plan(topic, prompts)

    return {
        "execution_prompts": prompts,
        "execution_plan": execution_plan,
        "current_stage": WorkflowStage.CONFIG_ASSEMBLY.value,
        "workflow_stage_outputs": {
            **state.get("workflow_stage_outputs", {}),
            "prompt_generation": {
                "prompts_generated": len(prompts),
                "has_execution_plan": bool(execution_plan),
            }
        },
        "errors": state.get("errors", []) + [
            f"Workflow: Generated {len(prompts)} execution prompts"
        ],
    }


def _generate_prompt_for_subtask(
    subtask: SubTask,
    tools: List[Dict],
    joseki_patterns: List[Dict]
) -> Dict[str, Any]:
    """Generate execution prompt for a subtask"""
    tool_names = [t["name"] for t in tools]

    return {
        "subtask_id": subtask["id"],
        "subtask_name": subtask["name"],
        "description": subtask["description"],
        "tools_to_use": tool_names,
        "joseki_hints": [p["name"] for p in joseki_patterns],
        "instructions": _generate_instructions(subtask, tools),
    }


def _generate_instructions(subtask: SubTask, tools: List[Dict]) -> str:
    """Generate human-readable instructions for a subtask"""
    task_name = subtask.get("name", "")
    tool_list = ", ".join(t["name"] for t in tools[:3])

    instructions_map = {
        "create_parameters": (
            f"Create parameter sliders for dimensions and counts.\n"
            f"Use components: {tool_list}\n"
            f"Place sliders in column 0 for easy access."
        ),
        "create_base_geometry": (
            f"Create base geometry primitives.\n"
            f"Use components: {tool_list}\n"
            f"Connect parameter sliders to dimension inputs."
        ),
        "apply_transformations": (
            f"Apply transformations to position geometry.\n"
            f"Use components: {tool_list}\n"
            f"Ensure proper orientation planes."
        ),
        "create_connections": (
            f"Connect components for calculations.\n"
            f"Use components: {tool_list}\n"
            f"Verify data type compatibility."
        ),
        "finalize_assembly": (
            f"Finalize the assembly.\n"
            f"Use components: {tool_list}\n"
            f"Create solid union if needed."
        ),
    }

    return instructions_map.get(task_name, f"Execute: {subtask['description']}")


def _generate_execution_plan(topic: str, prompts: List[Dict]) -> str:
    """Generate overall execution plan"""
    lines = [
        f"# Execution Plan: {topic}",
        "",
        "## Stages",
    ]

    for i, prompt in enumerate(prompts, 1):
        lines.append(f"{i}. **{prompt['subtask_name']}**: {prompt['description']}")
        if prompt.get("tools_to_use"):
            lines.append(f"   - Tools: {', '.join(prompt['tools_to_use'][:3])}")

    lines.extend([
        "",
        "## Execution Notes",
        "- Execute stages in order",
        "- Verify connections after each stage",
        "- Check for null geometry errors",
    ])

    return "\n".join(lines)


# === Stage 4: Config Assembly ===

def config_assembly_node(state: DesignState) -> Dict[str, Any]:
    """
    Stage 4: Assemble final configuration

    Creates placement_info.json for GH_MCP execution.

    Args:
        state: Current DesignState

    Returns:
        State updates with assembled configuration
    """
    topic = state.get("topic", "")
    subtasks = state.get("subtasks", [])
    execution_prompts = state.get("execution_prompts", [])
    retrieved_tools = state.get("retrieved_tools", [])

    # Assemble placement_info
    placement_info = _assemble_placement_info(topic, subtasks, retrieved_tools)

    # Assemble component_id_map
    component_id_map = _assemble_component_id_map(subtasks, retrieved_tools)

    # Generate final output
    final_output = {
        "placement_info": placement_info,
        "component_id_map": component_id_map,
        "execution_summary": _generate_execution_summary(state),
    }

    return {
        "placement_info": placement_info,
        "component_id_map": component_id_map,
        "final_output": final_output,
        "current_stage": WorkflowStage.COMPLETE.value,
        "workflow_stage_outputs": {
            **state.get("workflow_stage_outputs", {}),
            "config_assembly": {
                "components": len(placement_info.get("components", [])),
                "connections": len(placement_info.get("connections", [])),
            }
        },
        "errors": state.get("errors", []) + [
            "Workflow: Configuration assembled, ready for execution"
        ],
    }


def _assemble_placement_info(
    topic: str,
    subtasks: List[SubTask],
    tools: List[Dict]
) -> Dict[str, Any]:
    """Assemble placement_info.json structure"""
    components = []
    connections = []

    # Group tools by type
    sliders = [t for t in tools if t["name"] == "NumberSlider"]
    geometry = [t for t in tools if t["name"] in ["CenterBox", "Cylinder", "Sphere"]]
    transforms = [t for t in tools if t["name"] in ["Move", "Orient", "XYPlane"]]

    # Create component entries
    row = 0
    prev_component_id = None

    # Add sliders (column 0)
    for i, slider in enumerate(sliders[:5]):
        comp_id = f"slider_{i}"
        components.append({
            "id": comp_id,
            "type": "NumberSlider",
            "position": {"col": 0, "row": i},
            "parameters": {"value": 10.0, "min": 0.0, "max": 100.0},
        })
        prev_component_id = comp_id
        row = max(row, i)

    # Add geometry (column 2)
    for i, geom in enumerate(geometry[:3]):
        comp_id = f"geom_{i}"
        components.append({
            "id": comp_id,
            "type": geom["name"],
            "position": {"col": 2, "row": i},
            "parameters": {},
        })

        # Connect slider to geometry
        if i < len(sliders):
            connections.append({
                "from": f"slider_{i}",
                "from_output": "Number",
                "to": comp_id,
                "to_input": "X" if i == 0 else ("Y" if i == 1 else "Z"),
            })

    # Add transforms (column 4)
    for i, trans in enumerate(transforms[:2]):
        comp_id = f"trans_{i}"
        components.append({
            "id": comp_id,
            "type": trans["name"],
            "position": {"col": 4, "row": i},
            "parameters": {},
        })

    return {
        "name": topic,
        "version": "1.0",
        "components": components,
        "connections": connections,
        "metadata": {
            "subtask_count": len(subtasks),
            "tool_count": len(tools),
        }
    }


def _assemble_component_id_map(
    subtasks: List[SubTask],
    tools: List[Dict]
) -> Dict[str, str]:
    """Assemble component ID mapping"""
    id_map = {}

    # Map logical names to component IDs
    for i, tool in enumerate(tools):
        tool_name = tool.get("name", "unknown")
        subtask = tool.get("subtask", "general")
        logical_name = f"{subtask}_{tool_name}_{i}"
        id_map[logical_name] = f"guid_placeholder_{i}"

    return id_map


def _generate_execution_summary(state: DesignState) -> str:
    """Generate execution summary"""
    stage_outputs = state.get("workflow_stage_outputs", {})

    lines = [
        "# Execution Summary",
        "",
    ]

    for stage, output in stage_outputs.items():
        lines.append(f"## {stage.replace('_', ' ').title()}")
        for key, value in output.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    return "\n".join(lines)


# === Entry/Exit Utilities ===

def enter_workflow_mode(state: DesignState) -> Dict[str, Any]:
    """Initialize Workflow mode"""
    return {
        "current_stage": WorkflowStage.DECOMPOSITION.value,
        "subtasks": [],
        "retrieved_tools": [],
        "execution_prompts": [],
        "workflow_stage_outputs": {},
        "intent_type": "workflow",
    }


def exit_workflow_mode(state: DesignState) -> Dict[str, Any]:
    """Clean exit from Workflow mode"""
    return {
        "current_stage": WorkflowStage.COMPLETE.value,
    }


def get_current_stage_node(state: DesignState) -> Optional[str]:
    """Get the node function name for current stage"""
    stage_to_node = {
        WorkflowStage.DECOMPOSITION.value: "intent_decomposition_node",
        WorkflowStage.TOOL_RETRIEVAL.value: "tool_retrieval_node",
        WorkflowStage.PROMPT_GENERATION.value: "prompt_generation_node",
        WorkflowStage.CONFIG_ASSEMBLY.value: "config_assembly_node",
    }

    current_stage = state.get("current_stage")
    return stage_to_node.get(current_stage)
