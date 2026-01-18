#!/usr/bin/env python3
"""
重建桌子 v3 - 不使用 Move 組件

設計原則：
1. 不使用 Move (OLD) 組件
2. 用 Construct Point + XY Plane 直接創建目標平面
3. 桌腳半徑調小（2.5 → 直徑 5cm）

連接邏輯：
- EXTRUDE_LEG_BASE → Orient.Geometry
- XY_PLANE_LEG_BASE → Orient.Source (A)
- Slider X,Y → Construct Point → XY Plane → Orient.Target (B)
- Orient.Geometry → Solid Union.Breps
"""

import socket
import json
import time
from typing import Optional, Dict

# =========================================================================
# MCP 通訊函數
# =========================================================================

def send_command(cmd_type: str, params: dict = None) -> dict:
    """發送命令到 GH_MCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect(("127.0.0.1", 8080))

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
        print(f"  ✓ {label}")
        return comp_id
    else:
        print(f"  ✗ {name or comp_type}: {result.get('error', result)}")
        return None


def connect(source_id: str, target_id: str,
            source_param: str = None, target_param: str = None,
            desc: str = "") -> bool:
    """連接兩個組件"""
    if not source_id or not target_id:
        print(f"  ⚠️ 跳過 {desc}: 缺少 ID")
        return False

    params = {"sourceId": source_id, "targetId": target_id}
    if source_param:
        params["sourceParam"] = source_param
    if target_param:
        params["targetParam"] = target_param

    result = send_command("connect_components", params)

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
    """設定 slider 值"""
    if not slider_id:
        return False
    result = send_command("set_slider_value", {
        "componentId": slider_id,
        "value": value
    })
    if result.get("success"):
        actual = result.get("data", {}).get("value", "?")
        print(f"  ✓ {name} = {actual}")
        return True
    else:
        print(f"  ✗ {name}: {result.get('error', result)}")
        return False


# =========================================================================
# 主程式
# =========================================================================

def main():
    print("=" * 70)
    print("重建桌子 v3 - 不使用 Move 組件")
    print("=" * 70)

    # 測試連接
    result = send_command("get_document_info")
    if not result.get("success"):
        print(f"✗ MCP 連接失敗: {result}")
        return

    # 清除 canvas
    print("\n[Step 0] 清除 canvas...")
    result = send_command("clear_document")
    print(f"  結果: {result.get('success', False)}")
    time.sleep(0.3)

    ids: Dict[str, str] = {}

    # =========================================================================
    # Step 1: 參數 Sliders
    # =========================================================================
    print("\n[Step 1] 創建參數 Sliders...")

    slider_defs = [
        ("SLIDER_LENGTH", 0, 0, "桌面長度"),
        ("SLIDER_WIDTH", 0, 50, "桌面寬度"),
        ("SLIDER_TOP_HEIGHT", 0, 100, "桌面厚度"),
        ("SLIDER_RADIUS_LEG", 0, 150, "桌腳半徑"),
        ("SLIDER_LEG_HEIGHT", 0, 200, "桌腳高度"),
        # 四條腿的 X, Y 位置
        ("SLIDER_LEG1_X", 0, 300, "腿1 X"),
        ("SLIDER_LEG1_Y", 0, 350, "腿1 Y"),
        ("SLIDER_LEG2_X", 0, 400, "腿2 X"),
        ("SLIDER_LEG2_Y", 0, 450, "腿2 Y"),
        ("SLIDER_LEG3_X", 0, 500, "腿3 X"),
        ("SLIDER_LEG3_Y", 0, 550, "腿3 Y"),
        ("SLIDER_LEG4_X", 0, 600, "腿4 X"),
        ("SLIDER_LEG4_Y", 0, 650, "腿4 Y"),
    ]

    for name, x, y, label in slider_defs:
        ids[name] = add_component("Number Slider", x, y, label)

    time.sleep(0.2)

    # =========================================================================
    # Step 2: 桌面幾何
    # =========================================================================
    print("\n[Step 2] 創建桌面幾何...")

    # 除以 2（計算半長/半寬）
    ids["DIV_X"] = add_component("Division", 150, 0, "長度/2")
    ids["DIV_Y"] = add_component("Division", 150, 50, "寬度/2")
    ids["DIV_Z"] = add_component("Division", 150, 100, "厚度/2")
    ids["CONST_2"] = add_component("Integer", 150, 150, "常數2")

    # 平均計算桌腳位置
    ids["AVG_X"] = add_component("Average", 300, 350, "腿平均X")
    ids["AVG_Y"] = add_component("Average", 300, 450, "腿平均Y")

    # 構造桌面中心點
    ids["PT_CENTER"] = add_component("Construct Point", 350, 200, "桌面中心點")

    # XY Plane 和 Center Box
    ids["PLANE_TOP"] = add_component("XY Plane", 450, 200, "桌面平面")
    ids["BOX_TOP"] = add_component("Center Box", 550, 200, "桌面Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 3: 桌腳基礎幾何（在原點創建一個）
    # =========================================================================
    print("\n[Step 3] 創建桌腳基礎幾何...")

    ids["PLANE_BASE"] = add_component("XY Plane", 200, 700, "基礎平面")
    ids["CIRCLE_BASE"] = add_component("Circle", 300, 700, "基礎圓")
    ids["BOUNDARY"] = add_component("Boundary Surfaces", 400, 700, "圓面")
    ids["UNIT_Z"] = add_component("Unit Z", 500, 700, "Z方向")
    ids["AMPLITUDE"] = add_component("Amplitude", 600, 700, "拉伸向量")
    ids["EXTRUDE"] = add_component("Extrude", 700, 700, "拉伸桌腳")

    time.sleep(0.2)

    # =========================================================================
    # Step 4: 四條腿的目標平面（不用 Move！）
    # =========================================================================
    print("\n[Step 4] 創建四條腿的目標平面...")

    for i in range(1, 5):
        y_offset = 850 + (i - 1) * 100

        # Construct Point 從 Slider X, Y
        ids[f"PT_LEG{i}"] = add_component(
            "Construct Point", 200, y_offset, f"腿{i}位置點"
        )

        # XY Plane 從 Point
        ids[f"PLANE_LEG{i}"] = add_component(
            "XY Plane", 350, y_offset, f"腿{i}平面"
        )

        # Orient 複製桌腳
        ids[f"ORIENT{i}"] = add_component(
            "Orient", 500, y_offset, f"Orient腿{i}"
        )

    time.sleep(0.2)

    # =========================================================================
    # Step 5: Boolean Union
    # =========================================================================
    print("\n[Step 5] 創建 Boolean Union...")

    ids["UNION"] = add_component("Solid Union", 800, 200, "合併")

    time.sleep(0.2)

    # =========================================================================
    # Step 6: 連接 - 桌面
    # =========================================================================
    print("\n[Step 6] 連接桌面...")

    # Sliders → Division
    connect(ids["SLIDER_LENGTH"], ids["DIV_X"], None, "A", "Length → Div.A")
    connect(ids["SLIDER_WIDTH"], ids["DIV_Y"], None, "A", "Width → Div.A")
    connect(ids["SLIDER_TOP_HEIGHT"], ids["DIV_Z"], None, "A", "Height → Div.A")
    connect(ids["CONST_2"], ids["DIV_X"], None, "B", "2 → Div.B (X)")
    connect(ids["CONST_2"], ids["DIV_Y"], None, "B", "2 → Div.B (Y)")
    connect(ids["CONST_2"], ids["DIV_Z"], None, "B", "2 → Div.B (Z)")

    # Average 計算腿位置中心
    for i in range(1, 5):
        connect(ids[f"SLIDER_LEG{i}_X"], ids["AVG_X"], None, "Input", f"Leg{i}X → AvgX")
        connect(ids[f"SLIDER_LEG{i}_Y"], ids["AVG_Y"], None, "Input", f"Leg{i}Y → AvgY")

    # 中心點
    connect(ids["AVG_X"], ids["PT_CENTER"], "A", "X coordinate", "AvgX → Pt.X")
    connect(ids["AVG_Y"], ids["PT_CENTER"], "A", "Y coordinate", "AvgY → Pt.Y")
    connect(ids["DIV_Z"], ids["PT_CENTER"], "Result", "Z coordinate", "DivZ → Pt.Z")

    # 桌面平面和 Box
    connect(ids["PT_CENTER"], ids["PLANE_TOP"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_TOP"], ids["BOX_TOP"], "Plane", "Base", "Plane → Box.Base")
    connect(ids["DIV_X"], ids["BOX_TOP"], "Result", "X", "DivX → Box.X")
    connect(ids["DIV_Y"], ids["BOX_TOP"], "Result", "Y", "DivY → Box.Y")
    connect(ids["DIV_Z"], ids["BOX_TOP"], "Result", "Z", "DivZ → Box.Z")

    time.sleep(0.2)

    # =========================================================================
    # Step 7: 連接 - 桌腳基礎
    # =========================================================================
    print("\n[Step 7] 連接桌腳基礎...")

    # 基礎平面（原點）→ 圓
    connect(ids["PLANE_BASE"], ids["CIRCLE_BASE"], "Plane", "Plane", "Plane → Circle")
    connect(ids["SLIDER_RADIUS_LEG"], ids["CIRCLE_BASE"], None, "Radius", "Radius → Circle")

    # 圓 → 面 → 拉伸
    connect(ids["CIRCLE_BASE"], ids["BOUNDARY"], "Circle", "Edges", "Circle → Boundary")
    connect(ids["UNIT_Z"], ids["AMPLITUDE"], "Unit vector", "Base", "UnitZ → Amp.Base")
    connect(ids["SLIDER_LEG_HEIGHT"], ids["AMPLITUDE"], None, "Amplitude", "Height → Amp")
    connect(ids["BOUNDARY"], ids["EXTRUDE"], "Surfaces", "Base", "Surface → Extrude")
    connect(ids["AMPLITUDE"], ids["EXTRUDE"], "Amplitude", "Direction", "Vector → Extrude")

    time.sleep(0.2)

    # =========================================================================
    # Step 8: 連接 - 四條腿 Orient
    # =========================================================================
    print("\n[Step 8] 連接四條腿 Orient...")

    for i in range(1, 5):
        # Slider X, Y → Construct Point
        connect(ids[f"SLIDER_LEG{i}_X"], ids[f"PT_LEG{i}"], None, "X coordinate",
                f"Leg{i}X → Pt")
        connect(ids[f"SLIDER_LEG{i}_Y"], ids[f"PT_LEG{i}"], None, "Y coordinate",
                f"Leg{i}Y → Pt")

        # Point → XY Plane
        connect(ids[f"PT_LEG{i}"], ids[f"PLANE_LEG{i}"], "Point", "Origin",
                f"Pt{i} → Plane{i}")

        # Orient 連接：
        # - Geometry: 從 Extrude
        # - Source (A): 從 PLANE_BASE
        # - Target (B): 從 PLANE_LEGi
        connect(ids["EXTRUDE"], ids[f"ORIENT{i}"], "Extrusion", "Geometry",
                f"Extrude → Orient{i}.G")
        connect(ids["PLANE_BASE"], ids[f"ORIENT{i}"], "Plane", "Source",
                f"PlaneBase → Orient{i}.Source")
        connect(ids[f"PLANE_LEG{i}"], ids[f"ORIENT{i}"], "Plane", "Target",
                f"Plane{i} → Orient{i}.Target")

    time.sleep(0.2)

    # =========================================================================
    # Step 9: 連接 - Boolean Union
    # =========================================================================
    print("\n[Step 9] 連接 Boolean Union...")

    # 桌面 → Union
    connect(ids["BOX_TOP"], ids["UNION"], "Box", "Breps", "Box → Union")

    # 四條腿 → Union
    for i in range(1, 5):
        connect(ids[f"ORIENT{i}"], ids["UNION"], "Geometry", "Breps",
                f"Orient{i} → Union")

    time.sleep(0.3)

    # =========================================================================
    # Step 10: 設定 Slider 值
    # =========================================================================
    print("\n[Step 10] 設定 Slider 值...")

    # 常數 2
    result = send_command("set_slider_value", {
        "componentId": ids["CONST_2"],
        "value": 2
    })

    # 桌面尺寸
    set_slider(ids["SLIDER_LENGTH"], 120, "長度=120")
    set_slider(ids["SLIDER_WIDTH"], 80, "寬度=80")
    set_slider(ids["SLIDER_TOP_HEIGHT"], 5, "厚度=5")
    set_slider(ids["SLIDER_RADIUS_LEG"], 2.5, "腿半徑=2.5")
    set_slider(ids["SLIDER_LEG_HEIGHT"], 70, "腿高=70")

    # 四條腿位置（桌面內縮 10）
    leg_positions = [
        (1, -50, -30),  # 左後
        (2, 50, -30),   # 右後
        (3, -50, 30),   # 左前
        (4, 50, 30),    # 右前
    ]

    for leg, x, y in leg_positions:
        set_slider(ids[f"SLIDER_LEG{leg}_X"], x, f"腿{leg}X={x}")
        set_slider(ids[f"SLIDER_LEG{leg}_Y"], y, f"腿{leg}Y={y}")

    # =========================================================================
    # 儲存 ID 映射
    # =========================================================================
    with open("GH_WIP/component_id_map_v3.json", "w") as f:
        json.dump(ids, f, indent=2)

    print("\n" + "=" * 70)
    print("✓ 桌子重建完成！")
    print("=" * 70)
    print(f"組件數量: {len(ids)}")
    print("ID 映射已儲存: GH_WIP/component_id_map_v3.json")
    print("\n請在 Grasshopper 中確認：")
    print("1. 沒有紅線（類型匹配）")
    print("2. 桌腳細度合適")
    print("3. 桌子完整顯示")


if __name__ == "__main__":
    main()
