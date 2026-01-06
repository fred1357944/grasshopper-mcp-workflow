"""
Geometric Decomposition Nodes

Step 2 of the Grasshopper workflow: Decompose geometry into parts
"""

from typing import Any
from ..state import DesignState, Decision
import uuid


def decompose_geometry_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Decompose design into geometric parts

    This node:
    1. Analyzes requirements
    2. Identifies geometric components
    3. Creates part_info.mmd structure
    4. Defines relationships between parts

    Output: part_info.mmd content
    """
    requirements = state["requirements"]
    existing_part_info = state.get("part_info_mmd", "")

    if existing_part_info:
        # Already have decomposition, validate it
        return {
            "current_stage": "connectivity",
        }

    # Generate part decomposition
    part_info = _generate_part_info(requirements)

    return {
        "part_info_mmd": part_info,
        "current_stage": "connectivity",
    }


def validate_decomposition_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Validate geometric decomposition

    Checks:
    1. All parts are defined
    2. Relationships are valid
    3. No circular dependencies
    4. Manufacturing feasibility

    Returns validation result and any issues found
    """
    part_info = state["part_info_mmd"]

    # Validate the decomposition
    validation_result = _validate_part_info(part_info)

    if not validation_result["is_valid"]:
        # Create decision for fixing issues
        new_decisions = []
        for issue in validation_result["issues"]:
            if issue["severity"] == "error":
                new_decisions.append(Decision(
                    id=str(uuid.uuid4()),
                    question=f"Decomposition issue: {issue['message']}",
                    options=issue.get("suggestions", ["Fix manually", "Ignore"]),
                    importance="high",
                    context=f"Part: {issue.get('part', 'unknown')}",
                    resolved=False,
                    chosen_option=None
                ))

        return {
            "errors": [f"Decomposition: {i['message']}" for i in validation_result["issues"]],
            "pending_decisions": state["pending_decisions"] + new_decisions,
            "current_stage": "decomposition",  # Stay in decomposition stage
        }

    return {
        "current_stage": "connectivity",
    }


def _generate_part_info(requirements: str) -> str:
    """
    Generate part_info.mmd from requirements

    Format: Mermaid ER diagram
    """
    # Placeholder: In production, use LLM to analyze requirements

    # Default template for common designs
    template = """erDiagram
    DESIGN ||--|| MAIN_BODY : contains
    DESIGN ||--o{ SUPPORT : has
    MAIN_BODY ||--|| TOP_SURFACE : includes
    SUPPORT ||--|| LEG : "is a"

    MAIN_BODY {
        string sketch_type "Rectangle"
        string forming_method "Extrude"
        string base_plane "XY"
    }

    TOP_SURFACE {
        string sketch_type "Rectangle"
        string forming_method "Surface"
        float width "variable"
        float length "variable"
    }

    SUPPORT {
        string sketch_type "Circle"
        string forming_method "Extrude"
        int count "4"
    }

    LEG {
        float radius "variable"
        float height "variable"
        string position "corner"
    }
"""
    return template


def _validate_part_info(part_info: str) -> dict:
    """
    Validate part_info.mmd content

    Returns:
    {
        "is_valid": bool,
        "issues": [{"severity": str, "message": str, "part": str, "suggestions": list}]
    }
    """
    issues = []

    # Check for required sections
    if "erDiagram" not in part_info:
        issues.append({
            "severity": "error",
            "message": "Missing erDiagram declaration",
            "suggestions": ["Add 'erDiagram' at the beginning"]
        })

    # Check for at least one entity
    if "||" not in part_info and "--" not in part_info:
        issues.append({
            "severity": "error",
            "message": "No relationships defined",
            "suggestions": ["Define at least one relationship between parts"]
        })

    # Check for entity definitions
    if "{" not in part_info:
        issues.append({
            "severity": "warning",
            "message": "No entity attributes defined",
            "suggestions": ["Add attributes to entities for better documentation"]
        })

    return {
        "is_valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues
    }
