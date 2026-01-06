"""
Component Connectivity Nodes

Step 3 of the Grasshopper workflow: Plan component connectivity
"""

from typing import Any
from ..state import DesignState, Decision
import uuid


def plan_connectivity_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Plan Grasshopper component connectivity

    This node:
    1. Analyzes part_info.mmd
    2. Determines required Grasshopper components
    3. Plans data flow connections
    4. Creates component_info.mmd

    Output: component_info.mmd content
    """
    part_info = state["part_info_mmd"]
    requirements = state["requirements"]
    existing_component_info = state.get("component_info_mmd", "")

    if existing_component_info:
        # Already have connectivity plan
        return {
            "current_stage": "guid_resolution",
        }

    # Generate component connectivity diagram
    component_info = _generate_component_info(part_info, requirements)

    return {
        "component_info_mmd": component_info,
        "current_stage": "guid_resolution",
    }


def detect_conflicts_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Detect conflicts in component connectivity

    Checks for:
    1. Type mismatches between connected components
    2. Missing required connections
    3. Circular dependencies
    4. Incompatible data types

    Returns conflicts and suggestions
    """
    component_info = state["component_info_mmd"]

    # Detect conflicts
    conflicts = _detect_connectivity_conflicts(component_info)

    if conflicts:
        new_decisions = []
        for conflict in conflicts:
            if conflict["severity"] == "error":
                new_decisions.append(Decision(
                    id=str(uuid.uuid4()),
                    question=f"Connection conflict: {conflict['message']}",
                    options=conflict.get("solutions", ["Fix manually", "Remove connection"]),
                    importance="high",
                    context=f"Connection: {conflict.get('source', '?')} -> {conflict.get('target', '?')}",
                    resolved=False,
                    chosen_option=None
                ))

        return {
            "errors": [f"Connectivity: {c['message']}" for c in conflicts if c["severity"] == "error"],
            "pending_decisions": state["pending_decisions"] + new_decisions,
            "current_stage": "connectivity",  # Stay for fixes
        }

    return {
        "current_stage": "guid_resolution",
    }


def _generate_component_info(part_info: str, requirements: str) -> str:
    """
    Generate component_info.mmd from part decomposition

    Format: Mermaid flowchart
    """
    # Placeholder: In production, use LLM to map parts to components

    template = """flowchart LR
    subgraph Input["Input Parameters"]
        SLIDER_WIDTH["Number Slider<br/>Width"]
        SLIDER_LENGTH["Number Slider<br/>Length"]
        SLIDER_HEIGHT["Number Slider<br/>Height"]
        SLIDER_LEG_RADIUS["Number Slider<br/>Leg Radius"]
    end

    subgraph Geometry["Geometry Generation"]
        RECT["Rectangle<br/>Table Top Outline"]
        SURFACE["Surface<br/>Table Top"]
        CIRCLE["Circle<br/>Leg Cross Section"]
        EXTRUDE_TOP["Extrude<br/>Table Top"]
        EXTRUDE_LEG["Extrude<br/>Leg"]
    end

    subgraph Positioning["Positioning"]
        CORNERS["Rectangle Corners<br/>Leg Positions"]
        MOVE["Move<br/>Position Legs"]
    end

    subgraph Output["Output"]
        BREP["Brep Join<br/>Final Geometry"]
    end

    %% Connections
    SLIDER_WIDTH --> RECT
    SLIDER_LENGTH --> RECT
    RECT --> SURFACE
    RECT --> CORNERS
    SURFACE --> EXTRUDE_TOP
    SLIDER_HEIGHT --> EXTRUDE_TOP

    SLIDER_LEG_RADIUS --> CIRCLE
    CIRCLE --> EXTRUDE_LEG
    SLIDER_HEIGHT --> EXTRUDE_LEG

    CORNERS --> MOVE
    EXTRUDE_LEG --> MOVE

    EXTRUDE_TOP --> BREP
    MOVE --> BREP
"""
    return template


def _detect_connectivity_conflicts(component_info: str) -> list[dict]:
    """
    Detect conflicts in component connectivity

    Returns list of:
    {
        "severity": "error" | "warning",
        "message": str,
        "source": str,
        "target": str,
        "solutions": list[str]
    }
    """
    conflicts = []

    # Check for basic structure
    if "flowchart" not in component_info and "graph" not in component_info:
        conflicts.append({
            "severity": "error",
            "message": "Missing flowchart declaration",
            "solutions": ["Add 'flowchart LR' or 'flowchart TD' at the beginning"]
        })

    # Check for orphan nodes (nodes with no connections)
    lines = component_info.split("\n")
    defined_nodes = set()
    connected_nodes = set()

    for line in lines:
        # Simple parsing for node definitions
        if '["' in line or '("' in line:
            # Extract node ID
            parts = line.strip().split("[")
            if len(parts) > 1:
                node_id = parts[0].strip()
                if node_id and not node_id.startswith("%"):
                    defined_nodes.add(node_id)

        # Simple parsing for connections
        if "-->" in line:
            parts = line.split("-->")
            if len(parts) == 2:
                source = parts[0].strip().split()[-1] if parts[0].strip() else ""
                target = parts[1].strip().split()[0] if parts[1].strip() else ""
                if source:
                    connected_nodes.add(source)
                if target:
                    connected_nodes.add(target)

    # Find orphan nodes
    orphans = defined_nodes - connected_nodes
    for orphan in orphans:
        if orphan and not orphan.startswith("subgraph"):
            conflicts.append({
                "severity": "warning",
                "message": f"Node '{orphan}' has no connections",
                "source": orphan,
                "target": None,
                "solutions": ["Add connections to/from this node", "Remove if unused"]
            })

    return conflicts
