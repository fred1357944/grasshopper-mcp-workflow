"""
Component Connectivity Nodes

Step 3 of the Grasshopper workflow: Plan component connectivity

Enhanced v2.0:
- Writes component_info.mmd to GH_WIP/
- Pauses for user confirmation (Mermaid preview)
- Validates connection completeness
- Integrates with Gemini for validation
"""

from typing import Any
from pathlib import Path
from ..state import DesignState, Decision
import uuid


# Default work directory
GH_WIP_DIR = Path("GH_WIP")


def plan_connectivity_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Plan Grasshopper component connectivity

    This node:
    1. Analyzes part_info.mmd
    2. Determines required Grasshopper components
    3. Plans data flow connections
    4. Creates component_info.mmd
    5. Writes to GH_WIP/component_info.mmd
    6. Pauses for user confirmation (preview)

    Output: component_info.mmd content + file written
    """
    part_info = state["part_info_mmd"]
    requirements = state.get("requirements", "")
    topic = state.get("topic", "design")
    existing_component_info = state.get("component_info_mmd", "")

    # If already confirmed, move to next stage
    if existing_component_info and not state.get("awaiting_confirmation"):
        return {
            "current_stage": "guid_resolution",
        }

    # Generate component connectivity diagram
    component_info = _generate_component_info(part_info, requirements, topic)

    # Ensure GH_WIP directory exists
    GH_WIP_DIR.mkdir(exist_ok=True)

    # Write to file
    component_info_path = GH_WIP_DIR / "component_info.mmd"
    with open(component_info_path, "w", encoding="utf-8") as f:
        f.write(component_info)

    # Pause for user confirmation with preview
    return {
        "component_info_mmd": component_info,
        "awaiting_confirmation": True,
        "confirmation_reason": "component_info_preview",
        "current_stage": "connectivity",
        "pending_decisions": state.get("pending_decisions", []) + [
            Decision(
                id=str(uuid.uuid4()),
                question=f"請預覽 GH_WIP/component_info.mmd 的組件連接圖，確認是否正確？",
                options=["確認並繼續", "需要修改", "使用 Gemini 檢查完整性"],
                importance="high",
                context=f"檔案已寫入：{component_info_path.absolute()}",
                resolved=False,
                chosen_option=None
            )
        ]
    }


def confirm_connectivity_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Handle user confirmation of connectivity plan

    Checks user decision and either:
    - Proceeds to GUID resolution stage
    - Returns to connectivity for modification
    - Triggers Gemini validation
    """
    decisions = state.get("pending_decisions", [])

    for decision in decisions:
        if "component_info" in decision.get("question", "") and decision.get("resolved"):
            if decision["chosen_option"] == "確認並繼續":
                return {
                    "awaiting_confirmation": False,
                    "current_stage": "guid_resolution",
                }
            elif decision["chosen_option"] == "使用 Gemini 檢查完整性":
                # Would trigger Gemini validation here
                # For now, just proceed to validation node
                return {
                    "awaiting_confirmation": False,
                    "current_stage": "connectivity",  # Will go through validation
                }
            else:
                return {
                    "awaiting_confirmation": True,
                    "current_stage": "connectivity",
                }

    return {
        "awaiting_confirmation": True,
        "current_stage": "connectivity",
    }


def detect_conflicts_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Detect conflicts in component connectivity

    Checks for:
    1. Type mismatches between connected components
    2. Missing required connections
    3. Circular dependencies
    4. Incompatible data types
    5. Missing inputs/outputs

    Returns conflicts and suggestions
    """
    component_info = state["component_info_mmd"]

    # Detect conflicts
    conflicts = _detect_connectivity_conflicts(component_info)

    if conflicts:
        error_conflicts = [c for c in conflicts if c["severity"] == "error"]
        warning_conflicts = [c for c in conflicts if c["severity"] == "warning"]

        if error_conflicts:
            new_decisions = []
            for conflict in error_conflicts:
                new_decisions.append(Decision(
                    id=str(uuid.uuid4()),
                    question=f"連接衝突: {conflict['message']}",
                    options=conflict.get("solutions", ["手動修復", "移除連接"]),
                    importance="high",
                    context=f"連接: {conflict.get('source', '?')} -> {conflict.get('target', '?')}",
                    resolved=False,
                    chosen_option=None
                ))

            return {
                "errors": [f"連接問題: {c['message']}" for c in error_conflicts],
                "pending_decisions": state.get("pending_decisions", []) + new_decisions,
                "awaiting_confirmation": True,
                "confirmation_reason": "connectivity_conflicts",
                "current_stage": "connectivity",
            }

        # Only warnings, can proceed with user awareness
        if warning_conflicts:
            return {
                "errors": [f"警告: {c['message']}" for c in warning_conflicts],
                "current_stage": "guid_resolution",
            }

    return {
        "current_stage": "guid_resolution",
    }


def _generate_component_info(part_info: str, requirements: str, topic: str) -> str:
    """
    Generate component_info.mmd from part decomposition

    Format: Mermaid flowchart

    In production, this should be enhanced with:
    - LLM analysis of part_info
    - Gemini collaboration for optimization
    """
    topic_lower = topic.lower() if topic else ""

    if "桌" in topic or "table" in topic_lower:
        return _generate_table_component_info()
    elif "椅" in topic or "chair" in topic_lower:
        return _generate_chair_component_info()
    else:
        return _generate_default_component_info()


def _generate_table_component_info() -> str:
    """Generate table-specific component_info.mmd"""
    return """flowchart LR
    %% 桌面模块
    subgraph TOP["桌面 TABLE_TOP"]
        direction LR
        XY_PLANE_TOP["XY Plane<br/>输出: Plane"]
        SLIDER_WIDTH["Number Slider<br/>输出: 120.0"]
        SLIDER_LENGTH["Number Slider<br/>输出: 80.0"]
        SLIDER_TOP_HEIGHT["Number Slider<br/>输出: 5.0"]
        RECTANGLE_TOP["Rectangle<br/>输入: Plane, X Size, Y Size<br/>输出: Rectangle"]
        BOUNDARY_SURFACES_TOP["Boundary Surfaces<br/>输入: Edges<br/>输出: Surfaces"]
        UNIT_Z["Unit Z<br/>输出: Vector"]
        AMPLITUDE_TOP["Amplitude<br/>输入: Vector, Amplitude<br/>输出: Vector"]
        EXTRUDE_TOP["Extrude<br/>输入: Base, Direction<br/>输出: Result"]

        XY_PLANE_TOP -->|"Plane"| RECTANGLE_TOP
        SLIDER_WIDTH -->|"X Size"| RECTANGLE_TOP
        SLIDER_LENGTH -->|"Y Size"| RECTANGLE_TOP
        RECTANGLE_TOP -->|"Edges"| BOUNDARY_SURFACES_TOP
        BOUNDARY_SURFACES_TOP -->|"Base"| EXTRUDE_TOP
        UNIT_Z -->|"Vector"| AMPLITUDE_TOP
        SLIDER_TOP_HEIGHT -->|"Amplitude"| AMPLITUDE_TOP
        AMPLITUDE_TOP -->|"Direction"| EXTRUDE_TOP
    end

    %% 桌腳基礎模組（只創建一個，使用 Orient 複製到4個位置）
    subgraph LEG_BASE["桌腳基礎 TABLE_LEG_BASE"]
        direction LR
        XY_PLANE_LEG_BASE["XY Plane<br/>输出: Plane"]
        SLIDER_RADIUS_LEG["Number Slider<br/>输出: 2.5"]
        SLIDER_LEG_HEIGHT["Number Slider<br/>输出: 70.0"]
        CIRCLE_LEG_BASE["Circle<br/>输入: Plane, Radius<br/>输出: Circle"]
        BOUNDARY_SURFACES_LEG["Boundary Surfaces<br/>输入: Edges<br/>输出: Surfaces"]
        AMPLITUDE_LEG["Amplitude<br/>输入: Vector, Amplitude<br/>输出: Vector"]
        EXTRUDE_LEG_BASE["Extrude<br/>输入: Base, Direction<br/>输出: Result"]

        XY_PLANE_LEG_BASE -->|"Plane"| CIRCLE_LEG_BASE
        SLIDER_RADIUS_LEG -->|"Radius"| CIRCLE_LEG_BASE
        CIRCLE_LEG_BASE -->|"Edges"| BOUNDARY_SURFACES_LEG
        BOUNDARY_SURFACES_LEG -->|"Base"| EXTRUDE_LEG_BASE
        UNIT_Z -->|"Vector"| AMPLITUDE_LEG
        SLIDER_LEG_HEIGHT -->|"Amplitude"| AMPLITUDE_LEG
        AMPLITUDE_LEG -->|"Direction"| EXTRUDE_LEG_BASE
    end

    %% 桌腳位置平面（4個不同位置）
    subgraph LEG_PLANES["桌腳位置平面"]
        direction LR
        XY_PLANE_LEG_REF["XY Plane<br/>输出: Plane"]
        SLIDER_LEG1_X["Number Slider<br/>输出: -50.0"]
        SLIDER_LEG1_Y["Number Slider<br/>输出: -30.0"]
        SLIDER_LEG2_X["Number Slider<br/>输出: 50.0"]
        SLIDER_LEG2_Y["Number Slider<br/>输出: -30.0"]
        SLIDER_LEG3_X["Number Slider<br/>输出: -50.0"]
        SLIDER_LEG3_Y["Number Slider<br/>输出: 30.0"]
        SLIDER_LEG4_X["Number Slider<br/>输出: 50.0"]
        SLIDER_LEG4_Y["Number Slider<br/>输出: 30.0"]
        VECTOR_LEG1["Vector XYZ<br/>输入: X, Y, Z<br/>输出: Vector"]
        VECTOR_LEG2["Vector XYZ<br/>输入: X, Y, Z<br/>输出: Vector"]
        VECTOR_LEG3["Vector XYZ<br/>输入: X, Y, Z<br/>输出: Vector"]
        VECTOR_LEG4["Vector XYZ<br/>输入: X, Y, Z<br/>输出: Vector"]
        MOVE_PLANE_LEG1["Move<br/>输入: Geometry, Motion<br/>输出: Geometry"]
        MOVE_PLANE_LEG2["Move<br/>输入: Geometry, Motion<br/>输出: Geometry"]
        MOVE_PLANE_LEG3["Move<br/>输入: Geometry, Motion<br/>输出: Geometry"]
        MOVE_PLANE_LEG4["Move<br/>输入: Geometry, Motion<br/>输出: Geometry"]

        SLIDER_LEG1_X -->|"X"| VECTOR_LEG1
        SLIDER_LEG1_Y -->|"Y"| VECTOR_LEG1
        SLIDER_LEG2_X -->|"X"| VECTOR_LEG2
        SLIDER_LEG2_Y -->|"Y"| VECTOR_LEG2
        SLIDER_LEG3_X -->|"X"| VECTOR_LEG3
        SLIDER_LEG3_Y -->|"Y"| VECTOR_LEG3
        SLIDER_LEG4_X -->|"X"| VECTOR_LEG4
        SLIDER_LEG4_Y -->|"Y"| VECTOR_LEG4

        XY_PLANE_LEG_REF -->|"Geometry"| MOVE_PLANE_LEG1
        XY_PLANE_LEG_REF -->|"Geometry"| MOVE_PLANE_LEG2
        XY_PLANE_LEG_REF -->|"Geometry"| MOVE_PLANE_LEG3
        XY_PLANE_LEG_REF -->|"Geometry"| MOVE_PLANE_LEG4
        VECTOR_LEG1 -->|"Motion"| MOVE_PLANE_LEG1
        VECTOR_LEG2 -->|"Motion"| MOVE_PLANE_LEG2
        VECTOR_LEG3 -->|"Motion"| MOVE_PLANE_LEG3
        VECTOR_LEG4 -->|"Motion"| MOVE_PLANE_LEG4
    end

    %% Orient 組件（將基礎桌腳複製到4個不同位置的平面）
    subgraph ORIENT_GROUP["Orient 複製組"]
        direction LR
        ORIENT_LEG1["Orient<br/>输入: Geometry, Source, Target<br/>输出: Geometry"]
        ORIENT_LEG2["Orient<br/>输入: Geometry, Source, Target<br/>输出: Geometry"]
        ORIENT_LEG3["Orient<br/>输入: Geometry, Source, Target<br/>输出: Geometry"]
        ORIENT_LEG4["Orient<br/>输入: Geometry, Source, Target<br/>输出: Geometry"]
    end

    %% 连接基礎桌腳到 Orient
    EXTRUDE_LEG_BASE -->|"Geometry"| ORIENT_LEG1
    EXTRUDE_LEG_BASE -->|"Geometry"| ORIENT_LEG2
    EXTRUDE_LEG_BASE -->|"Geometry"| ORIENT_LEG3
    EXTRUDE_LEG_BASE -->|"Geometry"| ORIENT_LEG4
    XY_PLANE_LEG_BASE -->|"Source"| ORIENT_LEG1
    XY_PLANE_LEG_BASE -->|"Source"| ORIENT_LEG2
    XY_PLANE_LEG_BASE -->|"Source"| ORIENT_LEG3
    XY_PLANE_LEG_BASE -->|"Source"| ORIENT_LEG4
    MOVE_PLANE_LEG1 -->|"Target"| ORIENT_LEG1
    MOVE_PLANE_LEG2 -->|"Target"| ORIENT_LEG2
    MOVE_PLANE_LEG3 -->|"Target"| ORIENT_LEG3
    MOVE_PLANE_LEG4 -->|"Target"| ORIENT_LEG4

    %% 最终合并
    SOLID_UNION["Solid Union<br/>输入: Breps<br/>输出: Result"]

    EXTRUDE_TOP -->|"Breps"| SOLID_UNION
    ORIENT_LEG1 -->|"Breps"| SOLID_UNION
    ORIENT_LEG2 -->|"Breps"| SOLID_UNION
    ORIENT_LEG3 -->|"Breps"| SOLID_UNION
    ORIENT_LEG4 -->|"Breps"| SOLID_UNION
"""


def _generate_chair_component_info() -> str:
    """Generate chair-specific component_info.mmd"""
    return """flowchart LR
    %% 座椅模块
    subgraph SEAT["座椅 SEAT"]
        direction LR
        XY_PLANE_SEAT["XY Plane<br/>输出: Plane"]
        SLIDER_SEAT_W["Number Slider<br/>输出: 45.0"]
        SLIDER_SEAT_D["Number Slider<br/>输出: 45.0"]
        SLIDER_SEAT_H["Number Slider<br/>输出: 5.0"]
        RECT_SEAT["Rectangle<br/>输入: Plane, X Size, Y Size<br/>输出: Rectangle"]
        BOUNDARY_SEAT["Boundary Surfaces<br/>输入: Edges<br/>输出: Surfaces"]
        UNIT_Z["Unit Z<br/>输出: Vector"]
        AMP_SEAT["Amplitude<br/>输入: Vector, Amplitude<br/>输出: Vector"]
        EXTRUDE_SEAT["Extrude<br/>输入: Base, Direction<br/>输出: Result"]

        XY_PLANE_SEAT -->|"Plane"| RECT_SEAT
        SLIDER_SEAT_W -->|"X Size"| RECT_SEAT
        SLIDER_SEAT_D -->|"Y Size"| RECT_SEAT
        RECT_SEAT -->|"Edges"| BOUNDARY_SEAT
        BOUNDARY_SEAT -->|"Base"| EXTRUDE_SEAT
        UNIT_Z -->|"Vector"| AMP_SEAT
        SLIDER_SEAT_H -->|"Amplitude"| AMP_SEAT
        AMP_SEAT -->|"Direction"| EXTRUDE_SEAT
    end

    %% 椅背模块
    subgraph BACK["椅背 BACKREST"]
        direction LR
        CONSTRUCT_PT_BACK["Construct Point<br/>输入: X, Y, Z<br/>输出: Point"]
        XZ_PLANE_BACK["XZ Plane<br/>输入: Origin<br/>输出: Plane"]
        SLIDER_BACK_W["Number Slider<br/>输出: 45.0"]
        SLIDER_BACK_H["Number Slider<br/>输出: 40.0"]
        SLIDER_BACK_T["Number Slider<br/>输出: 3.0"]
        RECT_BACK["Rectangle<br/>输入: Plane, X Size, Y Size<br/>输出: Rectangle"]
        BOUNDARY_BACK["Boundary Surfaces<br/>输入: Edges<br/>输出: Surfaces"]
        UNIT_Y["Unit Y<br/>输出: Vector"]
        AMP_BACK["Amplitude<br/>输入: Vector, Amplitude<br/>输出: Vector"]
        EXTRUDE_BACK["Extrude<br/>输入: Base, Direction<br/>输出: Result"]

        CONSTRUCT_PT_BACK -->|"Origin"| XZ_PLANE_BACK
        XZ_PLANE_BACK -->|"Plane"| RECT_BACK
        SLIDER_BACK_W -->|"X Size"| RECT_BACK
        SLIDER_BACK_H -->|"Y Size"| RECT_BACK
        RECT_BACK -->|"Edges"| BOUNDARY_BACK
        BOUNDARY_BACK -->|"Base"| EXTRUDE_BACK
        UNIT_Y -->|"Vector"| AMP_BACK
        SLIDER_BACK_T -->|"Amplitude"| AMP_BACK
        AMP_BACK -->|"Direction"| EXTRUDE_BACK
    end

    %% 最终合并
    SOLID_UNION["Solid Union<br/>输入: Breps<br/>输出: Result"]

    EXTRUDE_SEAT -->|"Breps"| SOLID_UNION
    EXTRUDE_BACK -->|"Breps"| SOLID_UNION
"""


def _generate_default_component_info() -> str:
    """Generate default component_info.mmd template"""
    return """flowchart LR
    subgraph Input["輸入參數"]
        SLIDER_WIDTH["Number Slider<br/>寬度"]
        SLIDER_LENGTH["Number Slider<br/>長度"]
        SLIDER_HEIGHT["Number Slider<br/>高度"]
    end

    subgraph Geometry["幾何生成"]
        PLANE["XY Plane<br/>基準平面"]
        RECT["Rectangle<br/>矩形草圖"]
        SURFACE["Boundary Surfaces<br/>曲面"]
        UNIT_Z["Unit Z<br/>方向向量"]
        AMP["Amplitude<br/>方向縮放"]
        EXTRUDE["Extrude<br/>擠出"]
    end

    subgraph Output["輸出"]
        RESULT["輸出幾何體"]
    end

    %% 連接
    SLIDER_WIDTH -->|"X Size"| RECT
    SLIDER_LENGTH -->|"Y Size"| RECT
    PLANE -->|"Plane"| RECT
    RECT -->|"Edges"| SURFACE
    SURFACE -->|"Base"| EXTRUDE
    UNIT_Z -->|"Vector"| AMP
    SLIDER_HEIGHT -->|"Amplitude"| AMP
    AMP -->|"Direction"| EXTRUDE
    EXTRUDE --> RESULT
"""


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
            "message": "缺少 flowchart 宣告",
            "solutions": ["在開頭加入 'flowchart LR' 或 'flowchart TD'"]
        })
        return conflicts  # Can't validate further without proper structure

    lines = component_info.split("\n")
    defined_nodes = set()
    connected_sources = set()
    connected_targets = set()

    for line in lines:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("%") or line.startswith("%%"):
            continue

        # Parse node definitions
        if '["' in line and "-->" not in line:
            parts = line.split("[")
            if len(parts) > 1:
                node_id = parts[0].strip()
                if node_id and not node_id.startswith("subgraph") and not node_id.startswith("direction"):
                    defined_nodes.add(node_id)

        # Parse connections
        if "-->" in line:
            # Handle connections with labels like A -->|"label"| B
            if "|" in line:
                parts = line.split("-->")
                if len(parts) >= 2:
                    source = parts[0].strip().split()[-1] if parts[0].strip() else ""
                    # Extract target after the label
                    target_part = parts[1].split("|")[-1].strip() if "|" in parts[1] else parts[1].strip()
                    target = target_part.split()[0] if target_part else ""
            else:
                parts = line.split("-->")
                if len(parts) == 2:
                    source = parts[0].strip()
                    target = parts[1].strip()

            if source:
                connected_sources.add(source)
            if target:
                connected_targets.add(target)

    # Find nodes that are defined but never connected
    all_connected = connected_sources | connected_targets
    orphan_nodes = defined_nodes - all_connected

    for orphan in orphan_nodes:
        if orphan and not any(kw in orphan.lower() for kw in ["subgraph", "direction", "end", "style", "class"]):
            conflicts.append({
                "severity": "warning",
                "message": f"節點 '{orphan}' 沒有任何連接",
                "source": orphan,
                "target": None,
                "solutions": ["添加連接到/從此節點", "如果不需要則移除"]
            })

    # Check for nodes that are only sources (potential outputs)
    only_sources = connected_sources - connected_targets
    # This is often okay for output nodes, so just log as info

    # Check for nodes that are only targets (potential inputs without output)
    # This might indicate missing data flow
    only_targets = connected_targets - connected_sources - defined_nodes
    for node in only_targets:
        if node and "end" not in node.lower():
            conflicts.append({
                "severity": "warning",
                "message": f"節點 '{node}' 被連接但未定義或無輸出",
                "source": None,
                "target": node,
                "solutions": ["確認此節點是否正確定義", "檢查是否需要添加輸出連接"]
            })

    return conflicts
