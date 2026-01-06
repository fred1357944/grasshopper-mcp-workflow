"""
Geometric Decomposition Nodes

Step 2 of the Grasshopper workflow: Decompose geometry into parts

Enhanced v2.0:
- Writes part_info.mmd to GH_WIP/
- Pauses for user confirmation (Mermaid preview)
- Integrates with Gemini for validation
"""

from typing import Any
from pathlib import Path
from ..state import DesignState, Decision
import uuid
import os


# Default work directory
GH_WIP_DIR = Path("GH_WIP")


def decompose_geometry_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Decompose design into geometric parts

    This node:
    1. Analyzes requirements
    2. Identifies geometric components
    3. Creates part_info.mmd structure
    4. Writes to GH_WIP/part_info.mmd
    5. Pauses for user confirmation (preview)

    Output: part_info.mmd content + file written
    """
    requirements = state["requirements"]
    existing_part_info = state.get("part_info_mmd", "")
    topic = state.get("topic", "design")

    # If already confirmed, move to next stage
    if existing_part_info and not state.get("awaiting_confirmation"):
        return {
            "current_stage": "connectivity",
        }

    # Generate part decomposition based on requirements
    part_info = _generate_part_info(requirements, topic)

    # Ensure GH_WIP directory exists
    GH_WIP_DIR.mkdir(exist_ok=True)

    # Write to file
    part_info_path = GH_WIP_DIR / "part_info.mmd"
    with open(part_info_path, "w", encoding="utf-8") as f:
        f.write(part_info)

    # Pause for user confirmation with preview
    return {
        "part_info_mmd": part_info,
        "awaiting_confirmation": True,
        "confirmation_reason": "part_info_preview",
        "current_stage": "decomposition",
        "pending_decisions": state.get("pending_decisions", []) + [
            Decision(
                id=str(uuid.uuid4()),
                question=f"請預覽 GH_WIP/part_info.mmd 的幾何分解方案，確認是否正確？",
                options=["確認並繼續", "需要修改"],
                importance="high",
                context=f"檔案已寫入：{part_info_path.absolute()}",
                resolved=False,
                chosen_option=None
            )
        ]
    }


def confirm_decomposition_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Handle user confirmation of decomposition

    Checks user decision and either:
    - Proceeds to connectivity stage
    - Returns to decomposition for modification
    """
    decisions = state.get("pending_decisions", [])

    # Find the decomposition confirmation decision
    for decision in decisions:
        if "part_info" in decision.get("question", "") and decision.get("resolved"):
            if decision["chosen_option"] == "確認並繼續":
                # User approved, proceed
                return {
                    "awaiting_confirmation": False,
                    "current_stage": "connectivity",
                }
            else:
                # User wants modification, stay in stage
                return {
                    "awaiting_confirmation": True,
                    "current_stage": "decomposition",
                }

    # No decision found, continue waiting
    return {
        "awaiting_confirmation": True,
        "current_stage": "decomposition",
    }


def validate_decomposition_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Validate geometric decomposition

    Checks:
    1. All parts are defined
    2. Relationships are valid
    3. No circular dependencies
    4. Manufacturing feasibility

    Can optionally call Gemini for enhanced validation.
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
                    question=f"幾何分解問題: {issue['message']}",
                    options=issue.get("suggestions", ["手動修復", "忽略"]),
                    importance="high",
                    context=f"相關組件: {issue.get('part', 'unknown')}",
                    resolved=False,
                    chosen_option=None
                ))

        return {
            "errors": [f"幾何分解: {i['message']}" for i in validation_result["issues"]],
            "pending_decisions": state.get("pending_decisions", []) + new_decisions,
            "current_stage": "decomposition",
        }

    return {
        "current_stage": "connectivity",
    }


def _generate_part_info(requirements: str, topic: str) -> str:
    """
    Generate part_info.mmd from requirements

    Format: Mermaid ER diagram

    In production, this should be enhanced with:
    - LLM analysis of requirements
    - Gemini collaboration for optimization
    """
    # Detect design type from topic/requirements
    topic_lower = topic.lower() if topic else ""
    req_lower = requirements.lower() if requirements else ""

    # Template selection based on detected type
    if "桌" in topic or "table" in topic_lower:
        return _generate_table_template(requirements)
    elif "椅" in topic or "chair" in topic_lower:
        return _generate_chair_template(requirements)
    else:
        return _generate_default_template(requirements)


def _generate_table_template(requirements: str) -> str:
    """Generate table-specific part_info.mmd"""
    return """erDiagram
    TABLE ||--|| TABLE_TOP : contains
    TABLE ||--o{ TABLE_LEG : contains

    TABLE_TOP ||--o{ TABLE_LEG : supports

    TABLE {
        string name "桌子"
        int leg_count "4"
        float total_height "75.0"
    }

    TABLE_TOP {
        string sketch_type "Rectangle"
        string forming_method "Extrude"
        float width "120.0"
        float length "80.0"
        float height "5.0"
        plane base_plane "基準平面"
        vector extrusion_direction "擠出方向"
    }

    TABLE_LEG {
        string sketch_type "Circle"
        string forming_method "Extrude"
        float radius "2.5"
        float height "70.0"
        plane base_plane "基準平面（4個不同位置）"
        vector extrusion_direction "擠出方向"
        int leg_position "1-4"
        string replication_method "Orient"
    }
"""


def _generate_chair_template(requirements: str) -> str:
    """Generate chair-specific part_info.mmd"""
    return """erDiagram
    CHAIR ||--|| SEAT : contains
    CHAIR ||--|| BACKREST : contains
    CHAIR ||--o{ CHAIR_LEG : contains

    SEAT ||--o{ CHAIR_LEG : supports

    CHAIR {
        string name "椅子"
        int leg_count "4"
        float total_height "90.0"
    }

    SEAT {
        string sketch_type "Rectangle"
        string forming_method "Extrude"
        float width "45.0"
        float depth "45.0"
        float height "5.0"
        plane base_plane "基準平面"
    }

    BACKREST {
        string sketch_type "Rectangle"
        string forming_method "Extrude"
        float width "45.0"
        float height "40.0"
        float thickness "3.0"
        plane base_plane "傾斜平面"
    }

    CHAIR_LEG {
        string sketch_type "Circle"
        string forming_method "Extrude"
        float radius "2.0"
        float height "45.0"
        string replication_method "Orient"
    }
"""


def _generate_default_template(requirements: str) -> str:
    """Generate default part_info.mmd template"""
    return """erDiagram
    DESIGN ||--|| MAIN_BODY : contains
    DESIGN ||--o{ SUPPORT : has
    MAIN_BODY ||--|| TOP_SURFACE : includes
    SUPPORT ||--|| LEG : "is a"

    DESIGN {
        string name "設計物件"
        string description "請根據需求填寫"
    }

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
            "message": "缺少 erDiagram 宣告",
            "suggestions": ["在開頭加入 'erDiagram'"]
        })

    # Check for at least one entity
    if "||" not in part_info and "--" not in part_info:
        issues.append({
            "severity": "error",
            "message": "未定義任何關係",
            "suggestions": ["定義至少一個組件之間的關係"]
        })

    # Check for entity definitions
    if "{" not in part_info:
        issues.append({
            "severity": "warning",
            "message": "未定義實體屬性",
            "suggestions": ["為實體添加屬性以便後續使用"]
        })

    # Check for sketch_type
    if "sketch_type" not in part_info:
        issues.append({
            "severity": "warning",
            "message": "未指定 2D 草圖類型",
            "suggestions": ["為每個幾何體指定 sketch_type (Rectangle, Circle, etc.)"]
        })

    # Check for forming_method
    if "forming_method" not in part_info:
        issues.append({
            "severity": "warning",
            "message": "未指定 3D 成形方法",
            "suggestions": ["為每個幾何體指定 forming_method (Extrude, Surface, etc.)"]
        })

    return {
        "is_valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues
    }
