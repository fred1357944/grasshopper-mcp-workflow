"""
Execution Nodes

Step 4-5 of the Grasshopper workflow: Execute placement and analyze results
"""

from typing import Any
from ..state import DesignState, Decision
import uuid
import json


def execute_placement_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Execute placement_info.json

    This node:
    1. Validates placement_info structure
    2. Executes component placement
    3. Executes connections
    4. Returns execution result

    Integrates with existing PlacementExecutor
    """
    placement_info = state.get("placement_info")

    if not placement_info:
        # Need to generate placement_info first
        return {
            "errors": ["No placement_info available"],
            "current_stage": "guid_resolution",
        }

    # Execute placement
    # In production, this calls PlacementExecutor
    result = _execute_placement(placement_info)

    return {
        "execution_result": result,
        "errors": result.get("errors", []),
        "current_stage": "evaluation" if result["success"] else "execution",
    }


def analyze_errors_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Analyze execution errors

    This node:
    1. Categorizes errors
    2. Identifies root causes
    3. Suggests fixes
    4. Creates decisions for critical errors

    Returns analysis and suggested actions
    """
    execution_result = state.get("execution_result", {})
    errors = state.get("errors", [])

    if not errors:
        return {
            "current_stage": "evaluation",
        }

    # Analyze errors
    analysis = _analyze_errors(errors, execution_result)

    # Create decisions for actionable errors
    new_decisions = []
    for error_analysis in analysis["actionable_errors"]:
        new_decisions.append(Decision(
            id=str(uuid.uuid4()),
            question=f"Error: {error_analysis['summary']}",
            options=error_analysis["suggested_actions"],
            importance="high" if error_analysis["blocking"] else "medium",
            context=error_analysis["details"],
            resolved=False,
            chosen_option=None
        ))

    # Determine next stage
    if analysis["can_continue"]:
        next_stage = "optimization"
    elif new_decisions:
        next_stage = "execution"  # Wait for decisions
    else:
        next_stage = "execution"  # Retry needed

    return {
        "pending_decisions": state["pending_decisions"] + new_decisions,
        "current_stage": next_stage,
    }


def _execute_placement(placement_info: dict) -> dict:
    """
    Execute placement_info

    In production, this integrates with:
    - PlacementExecutor.execute_placement_info()
    - ComponentManager
    - ConnectionManager

    Returns:
    {
        "success": bool,
        "add_success": int,
        "add_fail": int,
        "connect_success": int,
        "connect_fail": int,
        "errors": list[str],
        "component_id_map": dict
    }
    """
    # Placeholder: Simulate execution
    # In production, call actual executor

    try:
        commands = placement_info.get("commands", [])
        add_commands = [c for c in commands if c.get("type") == "add_component"]
        connect_commands = [c for c in commands if c.get("type") == "connect_components"]

        # Simulate execution
        return {
            "success": True,
            "add_success": len(add_commands),
            "add_fail": 0,
            "connect_success": len(connect_commands),
            "connect_fail": 0,
            "errors": [],
            "component_id_map": {},
            "add_time": 0.0,
            "connect_time": 0.0,
            "total_time": 0.0,
        }

    except Exception as e:
        return {
            "success": False,
            "add_success": 0,
            "add_fail": 0,
            "connect_success": 0,
            "connect_fail": 0,
            "errors": [str(e)],
            "component_id_map": {},
        }


def _analyze_errors(errors: list[str], execution_result: dict) -> dict:
    """
    Analyze execution errors and suggest fixes

    Returns:
    {
        "total_errors": int,
        "by_category": {category: count},
        "actionable_errors": [
            {
                "summary": str,
                "details": str,
                "suggested_actions": list[str],
                "blocking": bool
            }
        ],
        "can_continue": bool
    }
    """
    analysis = {
        "total_errors": len(errors),
        "by_category": {},
        "actionable_errors": [],
        "can_continue": True
    }

    # Categorize errors
    categories = {
        "connection": [],
        "component": [],
        "parameter": [],
        "unknown": []
    }

    for error in errors:
        error_lower = error.lower()
        if "connect" in error_lower:
            categories["connection"].append(error)
        elif "component" in error_lower or "guid" in error_lower:
            categories["component"].append(error)
        elif "parameter" in error_lower or "value" in error_lower:
            categories["parameter"].append(error)
        else:
            categories["unknown"].append(error)

    analysis["by_category"] = {k: len(v) for k, v in categories.items() if v}

    # Generate actionable suggestions
    if categories["connection"]:
        analysis["actionable_errors"].append({
            "summary": f"{len(categories['connection'])} connection errors",
            "details": "\n".join(categories["connection"][:3]),
            "suggested_actions": [
                "Retry connections with delay",
                "Check component compatibility",
                "Verify parameter names"
            ],
            "blocking": True
        })
        analysis["can_continue"] = False

    if categories["component"]:
        analysis["actionable_errors"].append({
            "summary": f"{len(categories['component'])} component errors",
            "details": "\n".join(categories["component"][:3]),
            "suggested_actions": [
                "Verify GUIDs are correct",
                "Check if components are installed",
                "Try alternative components"
            ],
            "blocking": True
        })
        analysis["can_continue"] = False

    if categories["parameter"]:
        analysis["actionable_errors"].append({
            "summary": f"{len(categories['parameter'])} parameter errors",
            "details": "\n".join(categories["parameter"][:3]),
            "suggested_actions": [
                "Adjust parameter values",
                "Check value ranges",
                "Verify parameter types"
            ],
            "blocking": False  # Usually can continue
        })

    return analysis
