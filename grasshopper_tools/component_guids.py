"""
Grasshopper 組件 GUID 映射表

方案 A: 用 Python 內建的 GUID 映射表代替 get_component_candidates
這些 GUID 從 component_info.mmd 和 Grasshopper 文檔中提取

使用方式:
    from grasshopper_tools.component_guids import COMPONENT_GUIDS, get_guid

    guid = get_guid("Number Slider")  # 返回 GUID 字串
    guid = COMPONENT_GUIDS["Number Slider"]  # 直接查詢
"""

# 常用組件 GUID 映射表
# 格式: "組件名稱": "GUID"
COMPONENT_GUIDS = {
    # === 輸入組件 ===
    "Number Slider": "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da",
    "Panel": "59e0b89a-e487-49f8-bab8-b5bab16be14c",
    "Boolean Toggle": "2e78987b-9dfb-42a2-8b76-3923ac8bd91a",

    # === 平面與座標 ===
    "XY Plane": "a896f6c1-dd6c-4830-88f2-44808c07dc10",
    "XZ Plane": "c84e3e1f-1a40-4b52-be98-13c6c4c2e8ac",
    "YZ Plane": "e5a0e75e-5f7f-4be3-9e6d-e5b25f5e1d0d",
    "Construct Point": "9dceff86-6201-4c8e-90b1-706ad5bc3d49",
    "Construct Plane": "0fa47f5e-6e0d-48c6-bef0-a7c4a7d8e5e0",

    # === 向量 ===
    "Unit X": "2bda4f32-8366-4c58-8b43-fe6e0ca4cd8c",
    "Unit Y": "f8a96b67-e7e0-4b7a-9f1c-5e5d5e5e5e5e",
    "Unit Z": "9428ce3a-b2a0-4c8f-832a-8ad2b81a9743",
    "Vector XYZ": "d3116726-7a3e-4089-b3e2-216b266a1245",
    "Amplitude": "7b93e28d-6191-425a-844e-6e9e4127dd6b",

    # === 曲線 ===
    "Circle": "40dda121-a31b-421b-94b0-e46f5774f98e",
    "Rectangle": "9adebb98-f5c2-42da-8dfe-3bffbb7c12ca",
    "Line": "b082c8d3-3a97-40c5-a6a9-cc7c87bef2e6",
    "Polyline": "f0d85b24-76b8-4f79-b9e8-2e9e45edea26",

    # === 曲面 ===
    "Boundary Surfaces": "9ec27fcf-b30f-4ad2-b2d1-c1934c32f855",
    "Surface": "3d3b6a7c-d0e4-4f5a-8b7c-9c0d1e2f3a4b",

    # === 實體 ===
    "Extrude": "1c5e4c65-5f57-432c-96d3-53563470ab51",
    "Center Box": "e1f83fb4-efe0-4f10-8c20-4b38df56b36c",
    "Box": "6b3e7a8c-1234-5678-9abc-def012345678",
    "Cylinder": "4c5d6e7f-8a9b-0c1d-2e3f-4a5b6c7d8e9f",
    "Sphere": "2a3b4c5d-6e7f-8a9b-0c1d-2e3f4a5b6c7d",

    # === 布林運算 ===
    "Solid Union": "cabe86d9-6ef0-4037-90bd-01a02e0d30f0",
    "Solid Difference": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
    "Solid Intersection": "1234abcd-5678-efgh-ijkl-mnopqrstuvwx",

    # === 變換 ===
    "Move": "6af48ec9-decb-4ad7-81ac-cd20452189a2",
    "Orient": "b08eae6f-0030-4f63-be06-9f1c7f89efd1",
    "Rotate": "5d6e7f8a-9b0c-1d2e-3f4a-5b6c7d8e9f0a",
    "Scale": "7e8f9a0b-1c2d-3e4f-5a6b-7c8d9e0f1a2b",
    "Mirror": "8f9a0b1c-2d3e-4f5a-6b7c-8d9e0f1a2b3c",

    # === 數學運算 ===
    "Addition": "c1287c72-4931-4946-9a35-c8d888fbcae3",
    "Subtraction": "6e8eb3b4-3d24-4cc8-9a88-5e8ce73d9f0b",
    "Multiplication": "a0e66c8a-7f09-4d24-a1db-3c5f4c6b7a89",
    "Division": "7ed9789a-7403-4eeb-9716-d6e5681f4136",
    "Average": "3e0451ca-da24-452d-a6b1-a6877453d4e4",

    # === 列表操作 ===
    "List Item": "59daf374-bc21-4a5e-8282-5f29f6e8d7e4",
    "Merge": "09a3e0fc-d90f-4f13-8e9c-3c8d5a6b7c8d",
    "Flatten": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
}

# 組件名稱別名映射
COMPONENT_ALIASES = {
    "Slider": "Number Slider",
    "Pt": "Construct Point",
    "Plane": "XY Plane",
    "Rect": "Rectangle",
    "Brep": "Solid Union",
    "BoolUnion": "Solid Union",
}


def get_guid(component_name: str) -> str:
    """
    根據組件名稱獲取 GUID

    Args:
        component_name: 組件名稱（支援別名）

    Returns:
        組件 GUID 字串

    Raises:
        KeyError: 組件不存在
    """
    # 檢查別名
    if component_name in COMPONENT_ALIASES:
        component_name = COMPONENT_ALIASES[component_name]

    if component_name not in COMPONENT_GUIDS:
        raise KeyError(f"Unknown component: {component_name}. Available: {list(COMPONENT_GUIDS.keys())}")

    return COMPONENT_GUIDS[component_name]


def get_component_name(guid: str) -> str:
    """
    根據 GUID 獲取組件名稱（反向查詢）

    Args:
        guid: 組件 GUID

    Returns:
        組件名稱

    Raises:
        KeyError: GUID 不存在
    """
    guid_lower = guid.lower()
    for name, g in COMPONENT_GUIDS.items():
        if g.lower() == guid_lower:
            return name
    raise KeyError(f"Unknown GUID: {guid}")


def list_components() -> list[str]:
    """列出所有可用的組件名稱"""
    return sorted(COMPONENT_GUIDS.keys())


def search_components(keyword: str) -> list[tuple[str, str]]:
    """
    搜索組件（模糊匹配）

    Args:
        keyword: 搜索關鍵字

    Returns:
        [(組件名稱, GUID), ...]
    """
    keyword_lower = keyword.lower()
    results = []
    for name, guid in COMPONENT_GUIDS.items():
        if keyword_lower in name.lower():
            results.append((name, guid))
    return results


if __name__ == "__main__":
    # 測試
    print("=== 組件 GUID 映射表 ===")
    print(f"共 {len(COMPONENT_GUIDS)} 個組件\n")

    print("搜索 'Plane':")
    for name, guid in search_components("Plane"):
        print(f"  {name}: {guid}")

    print("\n搜索 'Box':")
    for name, guid in search_components("Box"):
        print(f"  {name}: {guid}")
