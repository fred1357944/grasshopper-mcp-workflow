"""
Knowledge Query Node - GH_MCP 知識查詢節點

在執行 GH_MCP 操作之前，自動查詢知識庫以獲取：
1. 組件 GUID 和參數信息
2. 匹配的連接模式
3. MCP 命令可用性檢查

這是 Claude 長文記憶增強計劃的核心組件，確保在上下文壓縮後
仍能通過查詢知識庫獲取正確的信息。

使用方式：
```python
from grasshopper_mcp.langgraph.nodes.knowledge_query import (
    knowledge_query_node,
    validate_commands_node,
    resolve_guids_node
)
```

2026-01-24
"""

from typing import Any, Dict, List, Set
import re
import logging

from ..state import DesignState
from ...knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


# Component name patterns for extraction
COMPONENT_PATTERNS = [
    r'Number Slider',
    r'Panel',
    r'Construct Point',
    r'Center Box',
    r'Mesh Box',
    r'Face Normals',
    r'Rotate',
    r'Move',
    r'Scale',
    r'Pipe',
    r'Interpolate',
    r'Circle',
    r'Line',
    r'Series',
    r'Division',
    r'Multiplication',
    r'Addition',
    r'Subtraction',
    r'Radians',
    r'Sine',
    r'Cosine',
    # WASP components
    r'WASP Part',
    r'WASP Connection',
    r'WASP Rule',
    r'WASP Aggregation',
    r'Connection From Direction',
    r'Stochastic Aggregation',
    # Karamba components
    r'Karamba',
    r'LineToBeam',
    r'CrossSection',
    r'Assemble',
    r'Analyze',
    # Kangaroo components
    r'Kangaroo',
    r'Anchor',
    r'SoapFilm',
    r'Pressure',
    r'EdgeLengths',
    # Common GH components
    r'Extrude',
    r'Loft',
    r'XY Plane',
    r'Unit Z',
    r'Cylinder',
    r'Boolean Toggle',
    r'Merge',
    r'Flatten',
    r'Graft',
    r'List Item',
]


def extract_component_names(text: str) -> Set[str]:
    """
    從設計意圖或 MMD 內容中提取組件名稱

    Args:
        text: 設計描述或 Mermaid 圖內容

    Returns:
        識別出的組件名稱集合
    """
    components = set()

    for pattern in COMPONENT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        components.update(matches)

    # Also extract from common patterns in MMD
    # e.g., "SLIDER --> DIVISION" or "[Number Slider]"
    bracket_pattern = r'\[([\w\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, text)
    components.update(bracket_matches)

    return components


def knowledge_query_node(state: DesignState) -> Dict[str, Any]:
    """
    知識查詢節點 - 在執行前查詢必要信息

    這個節點：
    1. 分析設計意圖，識別需要的組件
    2. 查詢每個組件的 GUID 和參數
    3. 搜索相關的連接模式
    4. 將知識注入到 state 中供後續節點使用

    Returns:
        更新的 state，包含 component_knowledge 和 matched_patterns
    """
    kb = get_knowledge_base()

    # 收集設計相關文本
    design_text = "\n".join([
        state.get("requirements", ""),
        state.get("topic", ""),
        state.get("component_info_mmd", ""),
        state.get("part_info_mmd", ""),
    ])

    # 1. 識別需要的組件
    components_needed = extract_component_names(design_text)
    logger.info(f"Identified {len(components_needed)} components: {components_needed}")

    # 2. 查詢每個組件的 GUID 和參數
    component_knowledge: Dict[str, Dict] = {}
    missing_components: List[str] = []

    for comp in components_needed:
        info = kb.get_component_guid(comp)
        if info:
            component_knowledge[comp] = {
                "guid": info.get("guid"),
                "inputs": info.get("inputs", []),
                "outputs": info.get("outputs", []),
                "category": info.get("category"),
                "note": info.get("note"),
                "known_conflicts": info.get("known_conflicts"),
            }
        else:
            missing_components.append(comp)

    # 3. 搜索相關的連接模式
    matched_patterns: List[Dict] = []

    # 基於關鍵字搜索
    for keyword in ["wasp", "karamba", "kangaroo", "ladybug", "honeybee"]:
        if keyword.lower() in design_text.lower():
            patterns = kb.search_patterns(keyword)
            matched_patterns.extend(patterns)

    # 去重
    seen_pattern_names = set()
    unique_patterns = []
    for p in matched_patterns:
        if p.get("name") not in seen_pattern_names:
            seen_pattern_names.add(p.get("name"))
            unique_patterns.append(p)

    # 4. 準備輸出
    errors = []
    if missing_components:
        errors.append(f"[知識庫] 未找到組件信息: {', '.join(missing_components[:5])}")

    # Log summary
    logger.info(
        f"Knowledge query complete: "
        f"{len(component_knowledge)} components found, "
        f"{len(missing_components)} missing, "
        f"{len(unique_patterns)} patterns matched"
    )

    return {
        "component_knowledge": component_knowledge,
        "matched_patterns": unique_patterns,
        "errors": state.get("errors", []) + errors if errors else state.get("errors", []),
    }


def validate_commands_node(state: DesignState) -> Dict[str, Any]:
    """
    命令驗證節點 - 檢查即將使用的 MCP 命令是否可用

    這個節點：
    1. 識別 placement_info 中使用的命令
    2. 檢查每個命令的可用性
    3. 提供不可用命令的替代方案

    Returns:
        更新的 state，包含 command_validation 結果
    """
    kb = get_knowledge_base()
    placement_info = state.get("placement_info")

    if not placement_info:
        return {}

    # 識別使用的命令類型
    used_commands = set()

    # 檢查 components
    if placement_info.get("components"):
        used_commands.add("add_component")
        for comp in placement_info["components"]:
            if comp.get("type") == "Number Slider":
                used_commands.add("set_slider_properties")

    # 檢查 connections
    if placement_info.get("connections"):
        used_commands.add("connect_components")

    # 驗證每個命令
    unavailable_commands: List[Dict] = []
    for cmd in used_commands:
        if not kb.is_command_available(cmd):
            workaround = kb.get_workaround(cmd)
            unavailable_commands.append({
                "command": cmd,
                "workaround": workaround,
            })

    # 獲取常見錯誤提醒
    common_mistakes = kb.get_common_mistakes()

    # 準備警告信息
    warnings = []
    if unavailable_commands:
        for item in unavailable_commands:
            warnings.append(
                f"[MCP] 命令不可用: {item['command']} → {item['workaround']}"
            )

    return {
        "command_validation": {
            "used_commands": list(used_commands),
            "unavailable_commands": unavailable_commands,
            "common_mistakes": common_mistakes,
        },
        "errors": state.get("errors", []) + warnings if warnings else state.get("errors", []),
    }


def resolve_guids_node(state: DesignState) -> Dict[str, Any]:
    """
    GUID 解析節點 - 為組件解析可信 GUID

    這個節點：
    1. 遍歷 placement_info 中的組件
    2. 使用知識庫解析可信 GUID
    3. 標記有衝突風險的組件

    Returns:
        更新的 state，包含 resolved_guids
    """
    kb = get_knowledge_base()
    placement_info = state.get("placement_info")

    if not placement_info:
        return {}

    components = placement_info.get("components", [])
    resolved_guids: Dict[str, str] = {}
    conflict_warnings: List[str] = []

    for comp in components:
        comp_type = comp.get("type", "")
        comp_id = comp.get("id", "")

        # 跳過已有 GUID 的組件
        if comp.get("guid"):
            resolved_guids[comp_id] = comp["guid"]
            continue

        # 查詢知識庫
        info = kb.get_component_guid(comp_type)
        if info:
            resolved_guids[comp_id] = info.get("guid", "")

            # 檢查衝突
            conflicts = info.get("known_conflicts")
            if conflicts:
                conflict_warnings.append(
                    f"[GUID] {comp_type} 有已知衝突: {conflicts}，建議使用 GUID {info.get('guid')}"
                )
        else:
            # 未找到，標記為需要運行時查詢
            logger.warning(f"No trusted GUID for: {comp_type}")

    return {
        "resolved_guids": resolved_guids,
        "conflict_warnings": conflict_warnings,
        "errors": state.get("errors", []) + conflict_warnings if conflict_warnings else state.get("errors", []),
    }


def inject_knowledge_node(state: DesignState) -> Dict[str, Any]:
    """
    知識注入節點 - 將知識庫信息注入到執行上下文

    這是一個聚合節點，用於在執行前統一查詢和注入所有知識。
    包含：知識查詢、命令驗證、GUID 解析

    Returns:
        完整的知識注入結果
    """
    # 執行所有知識查詢
    knowledge_result = knowledge_query_node(state)

    # 建立合併狀態 - 使用類型轉換避免 Pyright 錯誤
    merged_state_1: Any = {**state, **knowledge_result}
    command_result = validate_commands_node(merged_state_1)

    merged_state_2: Any = {**state, **knowledge_result, **command_result}
    guid_result = resolve_guids_node(merged_state_2)

    # 合併結果
    all_errors = []
    for result in [knowledge_result, command_result, guid_result]:
        all_errors.extend(result.get("errors", []))

    # 去重
    unique_errors = list(set(all_errors))

    return {
        "component_knowledge": knowledge_result.get("component_knowledge", {}),
        "matched_patterns": knowledge_result.get("matched_patterns", []),
        "command_validation": command_result.get("command_validation", {}),
        "resolved_guids": guid_result.get("resolved_guids", {}),
        "conflict_warnings": guid_result.get("conflict_warnings", []),
        "errors": unique_errors,
    }


def get_quick_reference() -> str:
    """
    生成知識庫快速參考信息

    用於在對話中提供關鍵知識摘要
    """
    kb = get_knowledge_base()
    summary = kb.get_summary()

    lines = [
        "=== GH_MCP 知識庫快速參考 ===",
        "",
        f"【已載入】組件: {summary['total_components']} | 模式: {summary['total_patterns']} | 命令: {summary['available_commands']}",
        "",
        "【關鍵 GUID】",
        "  Rotate: 19c70daf-600f-4697-ace2-567f6702144d",
        "  Pipe: 1ee25749-2e2d-4fc6-9209-0ea0515081f9",
        "  Series: 651c4fa5-dff4-4be6-ba31-6dc267d3ab47",
        "  Face Normals: f4370b82-4bd6-4ca7-90e8-c88584b280d5",
        "",
        "【禁用命令】",
        "  clear_canvas → 用 clear_document",
        "  Panel 作為數值 → 用 Number Slider",
        "",
        "【查詢方式】",
        "  from grasshopper_mcp.knowledge_base import lookup",
        "  lookup('Face Normals')  # 快速查詢",
    ]

    return "\n".join(lines)
