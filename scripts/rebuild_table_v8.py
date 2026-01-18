#!/usr/bin/env python3
"""
重建桌子 v8 - 使用 Expression 組件避免 OLD 問題

修正：
1. 使用 Expression 組件計算 Z = leg_height + top_height/2
2. 避免使用會產生 OLD 的 Addition 組件
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


def get_id(result: dict) -> Optional[str]:
    """從回應中提取 ID"""
    if not result.get("success"):
        return None
    data = result.get("data", {})
    return data.get("componentId") or data.get("id")


def add_slider(x: float, y: float, min_val: float, max_val: float,
               value: float, name: str = "") -> Optional[str]:
    """使用 add_component_advanced 創建帶範圍的 slider"""
    params = {
        "type": "Number Slider",
        "x": x,
        "y": y,
        "initialParams": {
            "min": min_val,
            "max": max_val,
            "value": value
        }
    }
    if name:
        params["name"] = name

    result = send_command("add_component_advanced", params)
    comp_id = get_id(result)

    if comp_id:
        print(f"  ✓ Slider: {name} = {value} (range: {min_val}-{max_val})")
        return comp_id
    else:
        print(f"  ✗ Slider {name}: {result.get('error', result)}")
        return None


def add_component(comp_type: str, x: float, y: float, name: str = None) -> Optional[str]:
    """添加普通組件"""
    params = {"type": comp_type, "x": x, "y": y}
    result = send_command("add_component", params)
    comp_id = get_id(result)

    if comp_id:
        print(f"  ✓ {name or comp_type}")
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


# =========================================================================
# 主程式
# =========================================================================

def main():
    print("=" * 70)
    print("重建桌子 v8 - 使用 Expression 組件避免 OLD 問題")
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

    # 桌面尺寸 sliders
    ids["SLIDER_LENGTH"] = add_slider(0, 0, 0, 200, 120, "桌面長度")
    ids["SLIDER_WIDTH"] = add_slider(0, 50, 0, 200, 80, "桌面寬度")
    ids["SLIDER_TOP_HEIGHT"] = add_slider(0, 100, 0, 20, 5, "桌面厚度")
    ids["SLIDER_RADIUS_LEG"] = add_slider(0, 150, 0.5, 10, 2.5, "桌腳半徑")
    ids["SLIDER_LEG_HEIGHT"] = add_slider(0, 200, 0, 100, 70, "桌腳高度")

    # 四條腿的位置 sliders
    ids["SLIDER_LEG1_X"] = add_slider(0, 300, -100, 100, -50, "腿1 X")
    ids["SLIDER_LEG1_Y"] = add_slider(0, 350, -100, 100, -30, "腿1 Y")
    ids["SLIDER_LEG2_X"] = add_slider(0, 400, -100, 100, 50, "腿2 X")
    ids["SLIDER_LEG2_Y"] = add_slider(0, 450, -100, 100, -30, "腿2 Y")
    ids["SLIDER_LEG3_X"] = add_slider(0, 500, -100, 100, -50, "腿3 X")
    ids["SLIDER_LEG3_Y"] = add_slider(0, 550, -100, 100, 30, "腿3 Y")
    ids["SLIDER_LEG4_X"] = add_slider(0, 600, -100, 100, 50, "腿4 X")
    ids["SLIDER_LEG4_Y"] = add_slider(0, 650, -100, 100, 30, "腿4 Y")

    time.sleep(0.2)

    # =========================================================================
    # Step 2: 桌面幾何
    # =========================================================================
    print("\n[Step 2] 創建桌面幾何組件...")

    # 除以 2（計算半長/半寬/半厚）
    ids["DIV_X"] = add_component("Division", 150, 0, "長度/2")
    ids["DIV_Y"] = add_component("Division", 150, 50, "寬度/2")
    ids["DIV_Z"] = add_component("Division", 150, 100, "厚度/2")

    # 常數 2
    ids["CONST_2"] = add_slider(150, 150, 0, 10, 2, "常數2")

    # 【使用 Expression 組件】計算桌面中心 Z = leg_height + top_height/2
    ids["EXPR_Z"] = add_component("Expression", 200, 200, "桌面Z公式")

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
    # Step 4: 四條腿的目標平面
    # =========================================================================
    print("\n[Step 4] 創建四條腿的目標平面...")

    for i in range(1, 5):
        y_offset = 850 + (i - 1) * 100

        ids[f"PT_LEG{i}"] = add_component("Construct Point", 200, y_offset, f"腿{i}位置點")
        ids[f"PLANE_LEG{i}"] = add_component("XY Plane", 350, y_offset, f"腿{i}平面")
        ids[f"ORIENT{i}"] = add_component("Orient", 500, y_offset, f"Orient腿{i}")

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

    # 【Expression 需要設定公式：x+y】
    # Expression 組件的輸入是 x, y, z... 輸出是 Result
    # 連接 leg_height → x, div_z → y
    connect(ids["SLIDER_LEG_HEIGHT"], ids["EXPR_Z"], None, "x", "LegHeight → Expr.x")
    connect(ids["DIV_Z"], ids["EXPR_Z"], "Result", "y", "DivZ → Expr.y")

    # Average 計算腿位置中心
    for i in range(1, 5):
        connect(ids[f"SLIDER_LEG{i}_X"], ids["AVG_X"], None, "Input", f"Leg{i}X → AvgX")
        connect(ids[f"SLIDER_LEG{i}_Y"], ids["AVG_Y"], None, "Input", f"Leg{i}Y → AvgY")

    # 中心點 - Z 使用 Expression 輸出
    connect(ids["AVG_X"], ids["PT_CENTER"], "Arithmetic mean", "X coordinate", "AvgX → Pt.X")
    connect(ids["AVG_Y"], ids["PT_CENTER"], "Arithmetic mean", "Y coordinate", "AvgY → Pt.Y")
    connect(ids["EXPR_Z"], ids["PT_CENTER"], "Result", "Z coordinate", "ExprZ → Pt.Z")

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
    connect(ids["UNIT_Z"], ids["AMPLITUDE"], "Unit vector", "Vector", "UnitZ → Amp.Vector")
    connect(ids["SLIDER_LEG_HEIGHT"], ids["AMPLITUDE"], None, "Amplitude", "Height → Amp")
    connect(ids["BOUNDARY"], ids["EXTRUDE"], "Surfaces", "Base", "Surface → Extrude")
    connect(ids["AMPLITUDE"], ids["EXTRUDE"], "Vector", "Direction", "Vector → Extrude")

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

        # Orient 連接
        connect(ids["EXTRUDE"], ids[f"ORIENT{i}"], "Extrusion", "Geometry",
                f"Extrude → Orient{i}.Geometry")
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
    # 儲存 ID 映射
    # =========================================================================
    with open("GH_WIP/component_id_map_v8.json", "w") as f:
        json.dump(ids, f, indent=2)

    print("\n" + "=" * 70)
    print("✓ 桌子重建完成！(v8 - 使用 Expression 組件)")
    print("=" * 70)
    print(f"組件數量: {len(ids)}")
    print("ID 映射已儲存: GH_WIP/component_id_map_v8.json")
    print("\n注意：")
    print("  - Expression 組件需要在 Grasshopper 中手動設定公式為 'x+y'")
    print("  - 或者需要 MCP 支援 set_expression 命令")


if __name__ == "__main__":
    main()
