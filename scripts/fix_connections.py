#!/usr/bin/env python3
"""
修復組件連接

使用 param_mapping.py 的知識庫修復失敗的連接。

問題分析：
1. 多輸入組件需要 targetParam（如 Average.Input, Move.Geometry/T）
2. 多輸出組件需要 sourceParam（如 Vector XYZ.V, Extrude.Extrusion）
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient
from grasshopper_tools.param_mapping import (
    get_target_param,
    get_source_param,
    SOURCE_PARAM_MAPPING,
    TARGET_PARAM_MAPPING
)


# 連接定義（帶正確的參數名）
# 格式: (source_id, target_id, source_param, target_param)
CONNECTIONS = [
    # ===============================================
    # 1. Slider -> Average (需要 targetParam="Input")
    # ===============================================
    ("SLIDER_LEG1_X", "AVERAGE_LEG_X", None, "Input"),
    ("SLIDER_LEG2_X", "AVERAGE_LEG_X", None, "Input"),
    ("SLIDER_LEG3_X", "AVERAGE_LEG_X", None, "Input"),
    ("SLIDER_LEG4_X", "AVERAGE_LEG_X", None, "Input"),
    ("SLIDER_LEG1_Y", "AVERAGE_LEG_Y", None, "Input"),
    ("SLIDER_LEG2_Y", "AVERAGE_LEG_Y", None, "Input"),
    ("SLIDER_LEG3_Y", "AVERAGE_LEG_Y", None, "Input"),
    ("SLIDER_LEG4_Y", "AVERAGE_LEG_Y", None, "Input"),

    # ===============================================
    # 2. Average -> Construct Point (需要 sourceParam="A", targetParam)
    # ===============================================
    ("AVERAGE_LEG_X", "CONSTRUCT_POINT_CENTER", "A", "X coordinate"),
    ("AVERAGE_LEG_Y", "CONSTRUCT_POINT_CENTER", "A", "Y coordinate"),

    # ===============================================
    # 3. Construct Point -> XY Plane (需要 sourceParam="Point")
    # ===============================================
    ("CONSTRUCT_POINT_CENTER", "XY_PLANE_TOP", "Point", "Origin"),

    # ===============================================
    # 4. XY Plane -> Center Box
    # ===============================================
    ("XY_PLANE_TOP", "CENTER_BOX_TOP", "Plane", "Base"),

    # ===============================================
    # 5. Slider -> Division
    # ===============================================
    ("SLIDER_LENGTH", "DIVISION_X", None, "A"),
    ("CONSTANT_2", "DIVISION_X", None, "B"),
    ("SLIDER_WIDTH", "DIVISION_Y", None, "A"),
    ("CONSTANT_2", "DIVISION_Y", None, "B"),
    ("SLIDER_TOP_HEIGHT", "DIVISION_Z", None, "A"),
    ("CONSTANT_2", "DIVISION_Z", None, "B"),

    # ===============================================
    # 6. Division -> Center Box (需要 sourceParam="Result")
    # ===============================================
    ("DIVISION_X", "CENTER_BOX_TOP", "Result", "X"),
    ("DIVISION_Y", "CENTER_BOX_TOP", "Result", "Y"),
    ("DIVISION_Z", "CENTER_BOX_TOP", "Result", "Z"),

    # ===============================================
    # 7. XY Plane -> Circle
    # ===============================================
    ("XY_PLANE_LEG_BASE", "CIRCLE_LEG_BASE", "Plane", "Plane"),
    ("SLIDER_RADIUS_LEG", "CIRCLE_LEG_BASE", None, "Radius"),

    # ===============================================
    # 8. Circle -> Boundary Surfaces
    # ===============================================
    ("CIRCLE_LEG_BASE", "BOUNDARY_SURFACES_LEG_BASE", "Circle", "Edges"),

    # ===============================================
    # 9. Boundary Surfaces -> Extrude
    # ===============================================
    ("BOUNDARY_SURFACES_LEG_BASE", "EXTRUDE_LEG_BASE", "Surfaces", "Base"),

    # ===============================================
    # 10. Unit Z -> Amplitude -> Extrude
    # ===============================================
    ("UNIT_Z", "AMPLITUDE_LEG_BASE", None, "Vector"),
    ("SLIDER_LEG_HEIGHT", "AMPLITUDE_LEG_BASE", None, "Amplitude"),
    ("AMPLITUDE_LEG_BASE", "EXTRUDE_LEG_BASE", "Vector", "Direction"),

    # ===============================================
    # 11. Slider -> Vector XYZ (每條腿的位移向量)
    # ===============================================
    ("SLIDER_LEG1_X", "VECTOR_LEG1", None, "X component"),
    ("SLIDER_LEG1_Y", "VECTOR_LEG1", None, "Y component"),
    ("SLIDER_LEG1_Z", "VECTOR_LEG1", None, "Z component"),

    ("SLIDER_LEG2_X", "VECTOR_LEG2", None, "X component"),
    ("SLIDER_LEG2_Y", "VECTOR_LEG2", None, "Y component"),
    ("SLIDER_LEG2_Z", "VECTOR_LEG2", None, "Z component"),

    ("SLIDER_LEG3_X", "VECTOR_LEG3", None, "X component"),
    ("SLIDER_LEG3_Y", "VECTOR_LEG3", None, "Y component"),
    ("SLIDER_LEG3_Z", "VECTOR_LEG3", None, "Z component"),

    ("SLIDER_LEG4_X", "VECTOR_LEG4", None, "X component"),
    ("SLIDER_LEG4_Y", "VECTOR_LEG4", None, "Y component"),
    ("SLIDER_LEG4_Z", "VECTOR_LEG4", None, "Z component"),

    # ===============================================
    # 12. XY_PLANE_LEG_REF -> Move (作為要移動的 Geometry)
    # ===============================================
    ("XY_PLANE_LEG_REF", "MOVE_PLANE_LEG1", "Plane", "Geometry"),
    ("XY_PLANE_LEG_REF", "MOVE_PLANE_LEG2", "Plane", "Geometry"),
    ("XY_PLANE_LEG_REF", "MOVE_PLANE_LEG3", "Plane", "Geometry"),
    ("XY_PLANE_LEG_REF", "MOVE_PLANE_LEG4", "Plane", "Geometry"),

    # ===============================================
    # 13. Vector -> Move.T (移動方向)
    # ===============================================
    ("VECTOR_LEG1", "MOVE_PLANE_LEG1", "V", "T"),
    ("VECTOR_LEG2", "MOVE_PLANE_LEG2", "V", "T"),
    ("VECTOR_LEG3", "MOVE_PLANE_LEG3", "V", "T"),
    ("VECTOR_LEG4", "MOVE_PLANE_LEG4", "V", "T"),

    # ===============================================
    # 14. Extrude -> Orient.Geometry
    # ===============================================
    ("EXTRUDE_LEG_BASE", "ORIENT_LEG1", "Extrusion", "Geometry"),
    ("EXTRUDE_LEG_BASE", "ORIENT_LEG2", "Extrusion", "Geometry"),
    ("EXTRUDE_LEG_BASE", "ORIENT_LEG3", "Extrusion", "Geometry"),
    ("EXTRUDE_LEG_BASE", "ORIENT_LEG4", "Extrusion", "Geometry"),

    # ===============================================
    # 15. XY_PLANE_LEG_BASE -> Orient.Source
    # ===============================================
    ("XY_PLANE_LEG_BASE", "ORIENT_LEG1", "Plane", "Source"),
    ("XY_PLANE_LEG_BASE", "ORIENT_LEG2", "Plane", "Source"),
    ("XY_PLANE_LEG_BASE", "ORIENT_LEG3", "Plane", "Source"),
    ("XY_PLANE_LEG_BASE", "ORIENT_LEG4", "Plane", "Source"),

    # ===============================================
    # 16. Move.Geometry -> Orient.Target (移動後的 Plane)
    # ===============================================
    ("MOVE_PLANE_LEG1", "ORIENT_LEG1", "Geometry", "Target"),
    ("MOVE_PLANE_LEG2", "ORIENT_LEG2", "Geometry", "Target"),
    ("MOVE_PLANE_LEG3", "ORIENT_LEG3", "Geometry", "Target"),
    ("MOVE_PLANE_LEG4", "ORIENT_LEG4", "Geometry", "Target"),

    # ===============================================
    # 17. Center Box & Orient -> Solid Union
    # ===============================================
    ("CENTER_BOX_TOP", "BOOLEAN_UNION", "Box", "Breps"),
    ("ORIENT_LEG1", "BOOLEAN_UNION", "Geometry", "Breps"),
    ("ORIENT_LEG2", "BOOLEAN_UNION", "Geometry", "Breps"),
    ("ORIENT_LEG3", "BOOLEAN_UNION", "Geometry", "Breps"),
    ("ORIENT_LEG4", "BOOLEAN_UNION", "Geometry", "Breps"),
]


def load_id_map(path: str) -> dict:
    """讀取 component_id_map.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 70)
    print("修復組件連接")
    print("=" * 70)

    # 載入 ID 映射
    id_map_path = Path("GH_WIP/component_id_map.json")
    if not id_map_path.exists():
        print(f"✗ 找不到 {id_map_path}")
        return

    id_map = load_id_map(str(id_map_path))
    print(f"✓ 載入 {len(id_map)} 個組件 ID")

    # 連接 MCP
    client = GrasshopperClient()
    response = client.send_command("get_document_info")

    if not response.get("success"):
        print(f"\n✗ 無法連接到 Grasshopper MCP: {response.get('error')}")
        return

    print("✓ Grasshopper 已連接")

    # 執行連接
    print(f"\n連接 {len(CONNECTIONS)} 對組件...")
    print("-" * 70)

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for i, (source_key, target_key, source_param, target_param) in enumerate(CONNECTIONS, 1):
        source_id = id_map.get(source_key)
        target_id = id_map.get(target_key)

        if not source_id:
            print(f"  ⚠️  [{i}] 跳過: 找不到 {source_key}")
            skipped_count += 1
            continue

        if not target_id:
            print(f"  ⚠️  [{i}] 跳過: 找不到 {target_key}")
            skipped_count += 1
            continue

        params = {
            "sourceId": source_id,
            "targetId": target_id
        }

        if source_param:
            params["sourceParam"] = source_param
        if target_param:
            params["targetParam"] = target_param

        response = client.send_command("connect_components", params)

        # 檢查結果
        inner = response.get("data", {})
        ok = response.get("success", False)
        inner_ok = inner.get("success", False) if isinstance(inner, dict) else False

        if ok and inner_ok:
            print(f"  ✓ [{i}] {source_key} -> {target_key}")
            success_count += 1
        elif "already connected" in str(inner).lower():
            print(f"  ✓ [{i}] {source_key} -> {target_key} (已連接)")
            success_count += 1
        else:
            error = inner.get("error", "") if isinstance(inner, dict) else str(inner)
            print(f"  ✗ [{i}] {source_key} -> {target_key}: {error[:50]}")
            fail_count += 1

        time.sleep(0.03)

    # 總結
    print("\n" + "=" * 70)
    print("總結")
    print("=" * 70)
    print(f"成功: {success_count}")
    print(f"失敗: {fail_count}")
    print(f"跳過: {skipped_count}")

    if fail_count == 0:
        print("\n🎉 所有連接完成！請在 Grasshopper/Rhino 中查看結果。")
    else:
        print(f"\n⚠️  有 {fail_count} 個連接失敗，請檢查 Grasshopper 中的狀態。")


if __name__ == "__main__":
    main()
