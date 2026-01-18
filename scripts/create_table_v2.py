#!/usr/bin/env python3
"""
創建參數化桌子 v2.0

應用之前學到的所有教訓：
1. 參數名小寫: type, x, y, componentId, value
2. Orient 參數: "Source", "Target" (不是 "A", "B")
3. Average: 輸入 "Input", 輸出 "A"
4. 多輸出組件需 sourceParam
5. UTF-8-sig 解碼

桌子規格:
- 桌面: 120 x 80 x 5 cm (Z=72.5)
- 腿: 半徑 3cm, 高 70cm
- 四腿位置: (±50, ±30, 0)
"""

import socket
import json
import time
from typing import Optional


def send_command(cmd_type: str, params: dict = None) -> dict:
    """發送命令到 GH_MCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect(("127.0.0.1", 8080))

        # 重要: JSON 屬性名是 "type" 和 "parameters" (小寫)
        command = {"type": cmd_type}
        if params:
            command["parameters"] = params

        message = json.dumps(command) + "\n"
        sock.sendall(message.encode("utf-8"))

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break

        sock.close()
        return json.loads(response.decode("utf-8-sig").strip())

    except Exception as e:
        return {"error": str(e), "success": False}


def add_component(comp_type: str, x: float, y: float, name: str = None) -> Optional[str]:
    """添加組件，返回 ID"""
    params = {"type": comp_type, "x": x, "y": y}
    result = send_command("add_component", params)

    if result.get("success"):
        comp_id = result.get("data", {}).get("id")
        label = name or comp_type
        print(f"  ✓ {label}: {comp_id[:8]}..." if comp_id else f"  ✓ {label}")
        return comp_id
    else:
        print(f"  ✗ {name or comp_type}: {result.get('error', result)}")
        return None


def connect(source_id: str, target_id: str,
            source_param: str = None, target_param: str = None,
            desc: str = "") -> bool:
    """連接兩個組件"""
    params = {"sourceId": source_id, "targetId": target_id}
    if source_param:
        params["sourceParam"] = source_param
    if target_param:
        params["targetParam"] = target_param

    result = send_command("connect_components", params)

    # 檢查結果
    ok = result.get("success", False)
    inner = result.get("data", {})
    inner_ok = inner.get("success", False) if isinstance(inner, dict) else False
    already = "already connected" in str(inner).lower()

    if ok and (inner_ok or already):
        print(f"  ✓ {desc}")
        return True
    else:
        error = inner.get("error", str(result)) if isinstance(inner, dict) else str(result)
        print(f"  ✗ {desc}: {error[:60]}")
        return False


def set_slider(slider_id: str, value: float, name: str = "") -> bool:
    """設定 slider 值（增強版命令）"""
    params = {"componentId": slider_id, "value": value}
    result = send_command("set_slider_value", params)

    if result.get("success"):
        print(f"  ✓ {name} = {value}")
        return True
    elif "Unknown command" in str(result):
        print(f"  ⚠️ set_slider_value 未註冊（使用舊版 MCP）")
        return False
    else:
        print(f"  ✗ {name}: {result.get('error', result)}")
        return False


def main():
    print("=" * 70)
    print("創建參數化桌子 v2.0 - 應用所有學到的教訓")
    print("=" * 70)

    # =========================================================================
    # Step 0: 連接測試
    # =========================================================================
    print("\n[Step 0] 測試連接...")
    result = send_command("get_document_info")
    if not result.get("success"):
        print(f"✗ 連接失敗: {result}")
        return
    print("✓ MCP 連接成功")

    # =========================================================================
    # Step 1: 清空文檔
    # =========================================================================
    print("\n[Step 1] 清空文檔...")
    result = send_command("clear_document")
    if result.get("success"):
        print("✓ 文檔已清空")
    else:
        print(f"⚠️ 清空可能失敗: {result}")
    time.sleep(0.2)

    # ID 儲存
    ids = {}

    # =========================================================================
    # Step 2: 創建 Sliders (桌面尺寸)
    # =========================================================================
    print("\n[Step 2] 創建 Sliders...")

    # 桌面參數
    ids["SLIDER_LENGTH"] = add_component("Number Slider", 50, 50, "長度 Slider")
    ids["SLIDER_WIDTH"] = add_component("Number Slider", 50, 100, "寬度 Slider")
    ids["SLIDER_TOP_HEIGHT"] = add_component("Number Slider", 50, 150, "厚度 Slider")

    # 腿參數
    ids["SLIDER_RADIUS_LEG"] = add_component("Number Slider", 50, 250, "腿半徑 Slider")
    ids["SLIDER_LEG_HEIGHT"] = add_component("Number Slider", 50, 300, "腿高度 Slider")

    # 四腿位置 (X, Y, Z)
    leg_y_start = 400
    for i in range(1, 5):
        ids[f"SLIDER_LEG{i}_X"] = add_component("Number Slider", 50, leg_y_start + (i-1)*150, f"腿{i} X")
        ids[f"SLIDER_LEG{i}_Y"] = add_component("Number Slider", 50, leg_y_start + (i-1)*150 + 50, f"腿{i} Y")

    time.sleep(0.1)

    # =========================================================================
    # Step 3: 創建常數和數學組件
    # =========================================================================
    print("\n[Step 3] 創建數學組件...")

    ids["CONSTANT_2"] = add_component("Number Slider", 200, 50, "常數 2")

    # Division 用於計算桌面半尺寸
    ids["DIVISION_X"] = add_component("Division", 300, 50, "Division X")
    ids["DIVISION_Y"] = add_component("Division", 300, 100, "Division Y")
    ids["DIVISION_Z"] = add_component("Division", 300, 150, "Division Z")

    # Average 用於計算桌面中心
    ids["AVERAGE_LEG_X"] = add_component("Average", 300, 400, "Average X")
    ids["AVERAGE_LEG_Y"] = add_component("Average", 300, 500, "Average Y")

    time.sleep(0.1)

    # =========================================================================
    # Step 4: 創建幾何組件 (桌面)
    # =========================================================================
    print("\n[Step 4] 創建桌面幾何組件...")

    ids["CONSTRUCT_POINT_CENTER"] = add_component("Construct Point", 450, 450, "桌面中心點")
    ids["XY_PLANE_TOP"] = add_component("XY Plane", 550, 450, "桌面平面")
    ids["CENTER_BOX_TOP"] = add_component("Center Box", 650, 100, "桌面 Box")

    time.sleep(0.1)

    # =========================================================================
    # Step 5: 創建幾何組件 (腿)
    # =========================================================================
    print("\n[Step 5] 創建腿幾何組件...")

    # 基礎腿
    ids["XY_PLANE_LEG_BASE"] = add_component("XY Plane", 450, 600, "腿基座平面")
    ids["CIRCLE_LEG_BASE"] = add_component("Circle", 550, 600, "腿圓形")
    ids["BOUNDARY_SURFACES_LEG_BASE"] = add_component("Boundary Surfaces", 650, 600, "腿底面")
    ids["UNIT_Z"] = add_component("Unit Z", 450, 700, "Z 向量")
    ids["AMPLITUDE_LEG_BASE"] = add_component("Amplitude", 550, 700, "腿高度向量")
    ids["EXTRUDE_LEG_BASE"] = add_component("Extrude", 750, 650, "腿擠出")

    time.sleep(0.1)

    # =========================================================================
    # Step 6: 創建四條腿的位移和定向
    # =========================================================================
    print("\n[Step 6] 創建四腿位移組件...")

    # 參考平面 (用於 Move)
    ids["XY_PLANE_LEG_REF"] = add_component("XY Plane", 450, 800, "腿參考平面")

    for i in range(1, 5):
        y_offset = 900 + (i-1) * 120
        ids[f"VECTOR_LEG{i}"] = add_component("Vector XYZ", 550, y_offset, f"腿{i} 向量")
        ids[f"MOVE_PLANE_LEG{i}"] = add_component("Move", 650, y_offset, f"腿{i} 移動平面")
        ids[f"ORIENT_LEG{i}"] = add_component("Orient", 850, y_offset, f"腿{i} Orient")

    time.sleep(0.1)

    # =========================================================================
    # Step 7: 創建布林聯集
    # =========================================================================
    print("\n[Step 7] 創建布林聯集...")

    ids["BOOLEAN_UNION"] = add_component("Solid Union", 1000, 500, "布林聯集")

    time.sleep(0.2)

    # =========================================================================
    # Step 8: 建立連接
    # =========================================================================
    print("\n[Step 8] 建立連接...")

    # 檢查必要的 ID 是否存在
    missing = [k for k, v in ids.items() if v is None]
    if missing:
        print(f"\n⚠️ 缺少 {len(missing)} 個組件: {missing[:5]}...")
        print("部分連接可能失敗")

    success_count = 0
    fail_count = 0

    def try_connect(src, tgt, sp=None, tp=None, desc=""):
        nonlocal success_count, fail_count
        src_id = ids.get(src)
        tgt_id = ids.get(tgt)
        if src_id and tgt_id:
            if connect(src_id, tgt_id, sp, tp, desc):
                success_count += 1
            else:
                fail_count += 1
        else:
            print(f"  ⚠️ 跳過 {desc}: 缺少 ID")
            fail_count += 1

    # --- Division 連接 ---
    try_connect("SLIDER_LENGTH", "DIVISION_X", None, "A", "長度 -> Division X.A")
    try_connect("CONSTANT_2", "DIVISION_X", None, "B", "常數2 -> Division X.B")
    try_connect("SLIDER_WIDTH", "DIVISION_Y", None, "A", "寬度 -> Division Y.A")
    try_connect("CONSTANT_2", "DIVISION_Y", None, "B", "常數2 -> Division Y.B")
    try_connect("SLIDER_TOP_HEIGHT", "DIVISION_Z", None, "A", "厚度 -> Division Z.A")
    try_connect("CONSTANT_2", "DIVISION_Z", None, "B", "常數2 -> Division Z.B")

    # --- Division -> Center Box ---
    try_connect("DIVISION_X", "CENTER_BOX_TOP", "Result", "X", "Division X -> Box.X")
    try_connect("DIVISION_Y", "CENTER_BOX_TOP", "Result", "Y", "Division Y -> Box.Y")
    try_connect("DIVISION_Z", "CENTER_BOX_TOP", "Result", "Z", "Division Z -> Box.Z")

    # --- Average 連接 (每條腿的 X/Y 輸入) ---
    for i in range(1, 5):
        try_connect(f"SLIDER_LEG{i}_X", "AVERAGE_LEG_X", None, "Input", f"腿{i}X -> Average X")
        try_connect(f"SLIDER_LEG{i}_Y", "AVERAGE_LEG_Y", None, "Input", f"腿{i}Y -> Average Y")

    # --- Average -> Construct Point (注意: Average 輸出是 "A") ---
    try_connect("AVERAGE_LEG_X", "CONSTRUCT_POINT_CENTER", "A", "X coordinate", "Avg X -> Point.X")
    try_connect("AVERAGE_LEG_Y", "CONSTRUCT_POINT_CENTER", "A", "Y coordinate", "Avg Y -> Point.Y")

    # --- Construct Point -> XY Plane ---
    try_connect("CONSTRUCT_POINT_CENTER", "XY_PLANE_TOP", "Point", "Origin", "Point -> Plane.Origin")

    # --- XY Plane -> Center Box ---
    try_connect("XY_PLANE_TOP", "CENTER_BOX_TOP", "Plane", "Base", "Plane -> Box.Base")

    # --- 腿基座 ---
    try_connect("XY_PLANE_LEG_BASE", "CIRCLE_LEG_BASE", "Plane", "Plane", "Plane -> Circle.Plane")
    try_connect("SLIDER_RADIUS_LEG", "CIRCLE_LEG_BASE", None, "Radius", "半徑 -> Circle.Radius")
    try_connect("CIRCLE_LEG_BASE", "BOUNDARY_SURFACES_LEG_BASE", "Circle", "Edges", "Circle -> BoundarySurf.Edges")
    try_connect("BOUNDARY_SURFACES_LEG_BASE", "EXTRUDE_LEG_BASE", "Surfaces", "Base", "BoundarySurf -> Extrude.Base")

    # --- 擠出向量 ---
    try_connect("UNIT_Z", "AMPLITUDE_LEG_BASE", None, "Vector", "UnitZ -> Amplitude.Vector")
    try_connect("SLIDER_LEG_HEIGHT", "AMPLITUDE_LEG_BASE", None, "Amplitude", "腿高度 -> Amplitude.A")
    try_connect("AMPLITUDE_LEG_BASE", "EXTRUDE_LEG_BASE", "Vector", "Direction", "Amplitude -> Extrude.Direction")

    # --- 四腿向量和移動 ---
    for i in range(1, 5):
        # Slider -> Vector XYZ
        try_connect(f"SLIDER_LEG{i}_X", f"VECTOR_LEG{i}", None, "X component", f"腿{i}X -> Vector.X")
        try_connect(f"SLIDER_LEG{i}_Y", f"VECTOR_LEG{i}", None, "Y component", f"腿{i}Y -> Vector.Y")

        # 參考平面 -> Move.Geometry
        try_connect("XY_PLANE_LEG_REF", f"MOVE_PLANE_LEG{i}", "Plane", "Geometry", f"RefPlane -> Move{i}.G")

        # Vector -> Move.T (注意: Vector XYZ 輸出是 "V")
        try_connect(f"VECTOR_LEG{i}", f"MOVE_PLANE_LEG{i}", "V", "T", f"Vector{i} -> Move{i}.T")

        # Orient 連接
        # 重要: Orient 的參數是 "Source" 和 "Target"，不是 "A" 和 "B"！
        try_connect("EXTRUDE_LEG_BASE", f"ORIENT_LEG{i}", "Extrusion", "Geometry", f"Extrude -> Orient{i}.G")
        try_connect("XY_PLANE_LEG_BASE", f"ORIENT_LEG{i}", "Plane", "Source", f"BasePlane -> Orient{i}.Source")
        try_connect(f"MOVE_PLANE_LEG{i}", f"ORIENT_LEG{i}", "Geometry", "Target", f"MovedPlane -> Orient{i}.Target")

        # Orient -> Boolean Union
        try_connect(f"ORIENT_LEG{i}", "BOOLEAN_UNION", "Geometry", "Breps", f"Orient{i} -> Union.Breps")

    # --- 桌面 -> Boolean Union ---
    try_connect("CENTER_BOX_TOP", "BOOLEAN_UNION", "Box", "Breps", "Box -> Union.Breps")

    print(f"\n連接結果: 成功 {success_count}, 失敗 {fail_count}")

    time.sleep(0.2)

    # =========================================================================
    # Step 9: 設定 Slider 值（使用增強版 MCP）
    # =========================================================================
    print("\n[Step 9] 設定 Slider 值...")

    # 檢查 set_slider_value 是否可用
    test_result = send_command("set_slider_value", {
        "componentId": ids.get("SLIDER_LENGTH", "test"),
        "value": 120.0
    })

    if "Unknown command" in str(test_result):
        print("⚠️ set_slider_value 不可用（舊版 MCP）")
        print("   Slider 將保持默認值，請手動調整")
    else:
        # 設定桌面尺寸
        set_slider(ids["SLIDER_LENGTH"], 120.0, "桌面長度")
        set_slider(ids["SLIDER_WIDTH"], 80.0, "桌面寬度")
        set_slider(ids["SLIDER_TOP_HEIGHT"], 5.0, "桌面厚度")
        set_slider(ids["CONSTANT_2"], 2.0, "常數 2")

        # 設定腿參數
        set_slider(ids["SLIDER_RADIUS_LEG"], 3.0, "腿半徑")
        set_slider(ids["SLIDER_LEG_HEIGHT"], 70.0, "腿高度")

        # 設定四腿位置
        leg_positions = [
            (50.0, 30.0),    # 腿1: 前右
            (-50.0, 30.0),   # 腿2: 前左
            (-50.0, -30.0),  # 腿3: 後左
            (50.0, -30.0),   # 腿4: 後右
        ]

        for i, (x, y) in enumerate(leg_positions, 1):
            set_slider(ids[f"SLIDER_LEG{i}_X"], x, f"腿{i} X")
            set_slider(ids[f"SLIDER_LEG{i}_Y"], y, f"腿{i} Y")

    # =========================================================================
    # 完成
    # =========================================================================
    print("\n" + "=" * 70)
    print("桌子創建完成！")
    print("=" * 70)
    print(f"組件數量: {len([v for v in ids.values() if v])}")
    print("\n請在 Grasshopper/Rhino 中查看結果")

    # 儲存 ID 映射
    valid_ids = {k: v for k, v in ids.items() if v}
    with open("GH_WIP/component_id_map_v2.json", "w") as f:
        json.dump(valid_ids, f, indent=2)
    print(f"✓ ID 映射已儲存至 GH_WIP/component_id_map_v2.json")


if __name__ == "__main__":
    main()
