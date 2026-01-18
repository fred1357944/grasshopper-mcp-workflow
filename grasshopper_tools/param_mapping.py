"""
Grasshopper 組件參數映射知識庫

從實戰經驗中學習的參數名稱映射。
當 MCP 連接失敗時，使用此映射表找到正確的參數名。

用法:
    from grasshopper_tools.param_mapping import get_target_param, get_source_param

    # 連接 Slider -> Average
    target_param = get_target_param("Average", "Number")  # -> "Input"

    # 連接 Vector XYZ -> Move
    source_param = get_source_param("Vector XYZ")  # -> "V"
"""

# ============================================================================
# targetParam 映射：多輸入組件的實際參數名
# ============================================================================
TARGET_PARAM_MAPPING = {
    # Math
    "Average": {
        "Number": "Input",
        "Input": "Input",
        "I": "Input",
        "N": "Input",
    },
    "Division": {
        "A": "A",
        "B": "B",
        "Dividend": "A",
        "Divisor": "B",
    },
    "Addition": {
        "A": "A",
        "B": "B",
        "First": "A",
        "Second": "B",
    },
    "Multiplication": {
        "A": "A",
        "B": "B",
    },

    # Vector
    "Vector XYZ": {
        "X": "X component",
        "Y": "Y component",
        "Z": "Z component",
        "X component": "X component",
        "Y component": "Y component",
        "Z component": "Z component",
    },
    "Construct Point": {
        "X": "X coordinate",
        "Y": "Y coordinate",
        "Z": "Z coordinate",
        "X coordinate": "X coordinate",
        "Y coordinate": "Y coordinate",
        "Z coordinate": "Z coordinate",
    },
    "Construct Plane": {
        "Origin": "Origin",
        "O": "Origin",
        "X": "X direction",
        "Y": "Y direction",
        "X direction": "X direction",
        "Y direction": "Y direction",
    },
    "Amplitude": {
        "Vector": "Vector",
        "Amplitude": "Amplitude",
        "V": "Vector",
        "A": "Amplitude",
    },

    # Transform
    "Move": {
        "Geometry": "Geometry",
        "Motion": "T",
        "T": "T",
        "Translation": "T",
        "Transform": "T",
        "G": "Geometry",
    },
    "Orient": {
        "Geometry": "Geometry",
        "Source": "Source",  # 正確！不是 "A"
        "Target": "Target",  # 正確！不是 "B"
        "A": "Source",       # 兼容別名
        "B": "Target",       # 兼容別名
        "G": "Geometry",
        "Source Plane": "Source",
        "Target Plane": "Target",
    },
    "Scale": {
        "Geometry": "Geometry",
        "Center": "Center",
        "Factor": "Factor",
        "G": "Geometry",
        "C": "Center",
        "F": "Factor",
    },

    # Curve
    "Circle": {
        "Plane": "Plane",
        "Radius": "Radius",
        "P": "Plane",
        "R": "Radius",
    },
    "Line": {
        "Start Point": "Start Point",
        "End Point": "End Point",
        "A": "Start Point",
        "B": "End Point",
    },

    # Surface
    "Extrude": {
        "Base": "Base",
        "Direction": "Direction",
        "B": "Base",
        "D": "Direction",
    },
    "Boundary Surfaces": {
        "Edges": "Edges",
        "E": "Edges",
    },

    # Solid
    "Center Box": {
        "Base": "Base",
        "Plane": "Base",  # 常見錯誤：用 "Plane" 但實際是 "Base"
        "X": "X",
        "Y": "Y",
        "Z": "Z",
        "P": "Base",
    },
    "Solid Union": {
        "Breps": "Breps",
        "B": "Breps",
        "Brep": "Breps",
        "Solids": "Breps",
    },
    "Solid Difference": {
        "A": "A",
        "B": "B",
        "First": "A",
        "Second": "B",
    },

    # Primitive
    "XY Plane": {
        "Origin": "Origin",
        "O": "Origin",
    },
    "Unit Z": {
        "Factor": "Factor",
        "F": "Factor",
    },
}

# ============================================================================
# sourceParam 映射：多輸出組件的輸出參數名
# ============================================================================
SOURCE_PARAM_MAPPING = {
    "Vector XYZ": "V",
    "Construct Point": "Point",
    "Construct Plane": "Plane",  # 輸出正確的 Plane 類型
    "Orient": "Geometry",
    "Move": "Geometry",
    "Scale": "Geometry",
    "Extrude": "Extrusion",
    "Boundary Surfaces": "Surfaces",
    "Solid Union": "Result",
    "Solid Difference": "Result",
    "Center Box": "Box",
    "Circle": "Circle",
    "Line": "Line",
    "Division": "Result",
    "Addition": "Result",
    "Multiplication": "Result",
    "Average": "A",  # 注意：不是 "Average"，是 "A"！
    "Amplitude": "Vector",
    "XY Plane": "Plane",  # 新增
}


def get_target_param(component_type: str, intended_param: str) -> str:
    """
    獲取組件的正確 targetParam 名稱

    Args:
        component_type: 組件類型（如 "Average", "Move"）
        intended_param: 預期的參數名（可能不正確）

    Returns:
        正確的參數名，如果找不到則返回原始值

    Example:
        >>> get_target_param("Average", "Number")
        "Input"
        >>> get_target_param("Move", "Motion")
        "T"
    """
    if component_type not in TARGET_PARAM_MAPPING:
        return intended_param

    mapping = TARGET_PARAM_MAPPING[component_type]
    return mapping.get(intended_param, intended_param)


def get_source_param(component_type: str) -> str | None:
    """
    獲取組件的 sourceParam 名稱（多輸出組件）

    Args:
        component_type: 組件類型

    Returns:
        sourceParam 名稱，如果不需要則返回 None

    Example:
        >>> get_source_param("Vector XYZ")
        "V"
        >>> get_source_param("Number Slider")
        None
    """
    return SOURCE_PARAM_MAPPING.get(component_type)


def needs_source_param(component_type: str) -> bool:
    """檢查組件是否需要指定 sourceParam"""
    return component_type in SOURCE_PARAM_MAPPING


def needs_target_param(component_type: str) -> bool:
    """檢查組件是否需要指定 targetParam"""
    return component_type in TARGET_PARAM_MAPPING


# ============================================================================
# 錯誤模式識別
# ============================================================================
ERROR_PATTERNS = {
    "Target parameter not found": "需要指定 targetParam",
    "Source parameter not found": "需要指定 sourceParam",
    "already connected": "連接已存在，可跳過",
    "Component type is required": "add_component 需要 type 參數",
}


def diagnose_error(error_message: str) -> str:
    """
    診斷連接錯誤並給出建議

    Args:
        error_message: MCP 返回的錯誤訊息

    Returns:
        診斷結果和建議
    """
    for pattern, diagnosis in ERROR_PATTERNS.items():
        if pattern.lower() in error_message.lower():
            return diagnosis
    return f"未知錯誤: {error_message}"


# ============================================================================
# MCP 限制記錄（從實戰中學到的）
# ============================================================================
MCP_LIMITATIONS = {
    "add_component": {
        "value_param": False,  # ❌ value 參數被忽略，slider 總是默認值
        "min_max_param": False,  # ❌ min/max 參數也被忽略
        "note": "基礎版 MCP 無法設定 slider 初始值，需要增強版"
    },
    "set_slider_value": {
        "supported": False,
        "note": "基礎版 MCP 不支援此命令"
    },
    "delete_component": {
        "supported": False,
        "note": "基礎版 MCP 不支援此命令"
    }
}

# 已驗證可用的命令
MCP_SUPPORTED_COMMANDS = [
    "get_document_info",
    "add_component",  # 但不支援 value 參數
    "connect_components",
    "clear_document",
    "save_document",
    "load_document"
]


# ============================================================================
# 自動學習機制（未來擴展）
# ============================================================================
def learn_connection(
    source_type: str,
    target_type: str,
    source_param: str | None,
    target_param: str | None,
    success: bool
):
    """
    從成功/失敗的連接中學習（未來可寫入文件）

    這個函數目前只是占位符，未來可以：
    1. 記錄到 JSON 文件
    2. 更新映射表
    3. 統計成功率
    """
    # TODO: 實作自動學習機制
    pass
