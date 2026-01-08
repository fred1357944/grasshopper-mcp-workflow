#!/usr/bin/env python3
"""
創建參數化椅子 - 測試 GH_MCP v2.1 能力

結構：
- 座面 (Seat): Center Box
- 靠背 (Backrest): Center Box + 旋轉到 XZ 平面
- 四條腿 (Legs): 圓柱 + Orient 到四個角落

參數：
- 座面: 寬度、深度、厚度、高度
- 靠背: 寬度、高度、厚度
- 腿: 半徑、（高度由座面高度決定）
"""

import socket
import json
import time
from typing import Optional, Dict

# =========================================================================
# MCP 通訊函數（與 rebuild_table_v9.py 相同）
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
    """創建 slider 並設置 min/max/value"""
    result = send_command("add_component", {
        "type": "Number Slider",
        "x": x,
        "y": y
    })
    comp_id = get_id(result)

    if not comp_id:
        print(f"  ✗ Slider {name}: {result.get('error', result)}")
        return None

    props_result = send_command("set_slider_properties", {
        "id": comp_id,
        "min": min_val,
        "max": max_val,
        "value": value
    })

    if props_result.get("success"):
        print(f"  ✓ Slider: {name} = {value} (range: {min_val}-{max_val})")
    else:
        print(f"  ⚠️ Slider {name}: 創建成功但設置屬性失敗")

    return comp_id


def add_component(comp_type: str, x: float, y: float, name: str = None) -> Optional[str]:
    """添加普通組件"""
    result = send_command("add_component", {"type": comp_type, "x": x, "y": y})
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
    print("創建參數化椅子 - GH_MCP v2.1 能力測試")
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

    # 座面參數
    ids["SEAT_WIDTH"] = add_slider(0, 0, 30, 60, 45, "座面寬度")
    ids["SEAT_DEPTH"] = add_slider(0, 50, 30, 60, 45, "座面深度")
    ids["SEAT_THICK"] = add_slider(0, 100, 2, 10, 4, "座面厚度")
    ids["SEAT_HEIGHT"] = add_slider(0, 150, 35, 55, 45, "座面高度")

    # 靠背參數
    ids["BACK_WIDTH"] = add_slider(0, 250, 30, 60, 40, "靠背寬度")
    ids["BACK_HEIGHT"] = add_slider(0, 300, 20, 50, 35, "靠背高度")
    ids["BACK_THICK"] = add_slider(0, 350, 2, 8, 3, "靠背厚度")

    # 腿參數
    ids["LEG_RADIUS"] = add_slider(0, 450, 1, 5, 2, "腿半徑")

    # 常數
    ids["CONST_2"] = add_slider(0, 550, 0, 10, 2, "常數2")

    time.sleep(0.2)

    # =========================================================================
    # Step 2: 座面幾何
    # =========================================================================
    print("\n[Step 2] 創建座面幾何...")

    # 除以 2（計算半尺寸）
    ids["DIV_SEAT_W"] = add_component("Division", 150, 0, "座寬/2")
    ids["DIV_SEAT_D"] = add_component("Division", 150, 50, "座深/2")
    ids["DIV_SEAT_T"] = add_component("Division", 150, 100, "座厚/2")

    # 座面中心高度 = seat_height + seat_thick/2
    ids["SEAT_CENTER_Z"] = add_component("Mass Addition", 200, 150, "座面中心Z")

    # 座面中心點
    ids["PT_SEAT"] = add_component("Construct Point", 300, 100, "座面中心點")

    # 座面平面和 Box
    ids["PLANE_SEAT"] = add_component("XY Plane", 400, 100, "座面平面")
    ids["BOX_SEAT"] = add_component("Center Box", 500, 100, "座面Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 3: 靠背幾何
    # =========================================================================
    print("\n[Step 3] 創建靠背幾何...")

    # 靠背尺寸 /2
    ids["DIV_BACK_W"] = add_component("Division", 150, 250, "背寬/2")
    ids["DIV_BACK_H"] = add_component("Division", 150, 300, "背高/2")
    ids["DIV_BACK_T"] = add_component("Division", 150, 350, "背厚/2")

    # 靠背中心位置計算
    # X = 0
    # Y = -seat_depth/2 + back_thick/2  (靠背在座面後緣)
    # Z = seat_height + seat_thick + back_height/2
    # 注意：避免使用 Subtraction (OLD)，改用 Negative + Mass Addition
    ids["NEG_SEAT_D2_BACK"] = add_component("Negative", 250, 260, "負座深/2(靠背)")
    ids["BACK_Y_OFFSET"] = add_component("Mass Addition", 250, 290, "靠背Y偏移")
    ids["BACK_Z_BASE"] = add_component("Mass Addition", 250, 330, "靠背Z基礎")
    ids["BACK_CENTER_Z"] = add_component("Mass Addition", 320, 330, "靠背中心Z")

    # 靠背中心點
    ids["PT_BACK"] = add_component("Construct Point", 400, 300, "靠背中心點")

    # 靠背使用 XZ Plane（垂直平面）
    ids["PLANE_BACK"] = add_component("XZ Plane", 500, 300, "靠背平面")
    ids["BOX_BACK"] = add_component("Center Box", 600, 300, "靠背Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 4: 椅腿基礎幾何
    # =========================================================================
    print("\n[Step 4] 創建椅腿基礎幾何...")

    ids["PLANE_BASE"] = add_component("XY Plane", 200, 500, "基礎平面")
    ids["CIRCLE_BASE"] = add_component("Circle", 300, 500, "基礎圓")
    ids["BOUNDARY"] = add_component("Boundary Surfaces", 400, 500, "圓面")
    ids["UNIT_Z"] = add_component("Unit Z", 500, 500, "Z方向")
    ids["AMPLITUDE"] = add_component("Amplitude", 600, 500, "拉伸向量")
    ids["EXTRUDE_LEG"] = add_component("Extrude", 700, 500, "拉伸腿")

    time.sleep(0.2)

    # =========================================================================
    # Step 5: 四條腿的位置
    # =========================================================================
    print("\n[Step 5] 創建四條腿位置...")

    # 腿位置計算
    # 前左: (-seat_width/2 + offset, seat_depth/2 - offset)
    # 前右: (seat_width/2 - offset, seat_depth/2 - offset)
    # 後左: (-seat_width/2 + offset, -seat_depth/2 + offset)
    # 後右: (seat_width/2 - offset, -seat_depth/2 + offset)

    # 簡化：直接用 seat_width/2 和 seat_depth/2 的負值
    ids["NEG_SEAT_W2"] = add_component("Negative", 250, 0, "負座寬/2")
    ids["NEG_SEAT_D2"] = add_component("Negative", 250, 50, "負座深/2")

    leg_positions = [
        ("LEG1", "前左", 600),
        ("LEG2", "前右", 700),
        ("LEG3", "後左", 800),
        ("LEG4", "後右", 900),
    ]

    for leg_name, desc, y_pos in leg_positions:
        ids[f"PT_{leg_name}"] = add_component("Construct Point", 300, y_pos, f"{desc}位置點")
        ids[f"PLANE_{leg_name}"] = add_component("XY Plane", 450, y_pos, f"{desc}平面")
        ids[f"ORIENT_{leg_name}"] = add_component("Orient", 600, y_pos, f"Orient{desc}")

    time.sleep(0.2)

    # =========================================================================
    # Step 6: Boolean Union
    # =========================================================================
    print("\n[Step 6] 創建 Boolean Union...")

    ids["UNION"] = add_component("Solid Union", 850, 400, "合併")

    time.sleep(0.2)

    # =========================================================================
    # Step 7: 連接 - 座面
    # =========================================================================
    print("\n[Step 7] 連接座面...")

    # Sliders → Division
    connect(ids["SEAT_WIDTH"], ids["DIV_SEAT_W"], None, "A", "SeatW → Div.A")
    connect(ids["SEAT_DEPTH"], ids["DIV_SEAT_D"], None, "A", "SeatD → Div.A")
    connect(ids["SEAT_THICK"], ids["DIV_SEAT_T"], None, "A", "SeatT → Div.A")
    connect(ids["CONST_2"], ids["DIV_SEAT_W"], None, "B", "2 → Div.B (W)")
    connect(ids["CONST_2"], ids["DIV_SEAT_D"], None, "B", "2 → Div.B (D)")
    connect(ids["CONST_2"], ids["DIV_SEAT_T"], None, "B", "2 → Div.B (T)")

    # 座面中心 Z
    connect(ids["SEAT_HEIGHT"], ids["SEAT_CENTER_Z"], None, "Input", "SeatH → Z")
    connect(ids["DIV_SEAT_T"], ids["SEAT_CENTER_Z"], "Result", "Input", "SeatT/2 → Z")

    # 座面中心點 (0, 0, seat_center_z)
    connect(ids["SEAT_CENTER_Z"], ids["PT_SEAT"], "Result", "Z coordinate", "Z → Pt")

    # 座面 Box
    connect(ids["PT_SEAT"], ids["PLANE_SEAT"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_SEAT"], ids["BOX_SEAT"], "Plane", "Base", "Plane → Box")
    connect(ids["DIV_SEAT_W"], ids["BOX_SEAT"], "Result", "X", "W/2 → Box.X")
    connect(ids["DIV_SEAT_D"], ids["BOX_SEAT"], "Result", "Y", "D/2 → Box.Y")
    connect(ids["DIV_SEAT_T"], ids["BOX_SEAT"], "Result", "Z", "T/2 → Box.Z")

    # Negative 座面尺寸
    connect(ids["DIV_SEAT_W"], ids["NEG_SEAT_W2"], "Result", "Value", "W/2 → Neg")
    connect(ids["DIV_SEAT_D"], ids["NEG_SEAT_D2"], "Result", "Value", "D/2 → Neg")

    time.sleep(0.2)

    # =========================================================================
    # Step 8: 連接 - 靠背
    # =========================================================================
    print("\n[Step 8] 連接靠背...")

    # 靠背尺寸 /2
    connect(ids["BACK_WIDTH"], ids["DIV_BACK_W"], None, "A", "BackW → Div.A")
    connect(ids["BACK_HEIGHT"], ids["DIV_BACK_H"], None, "A", "BackH → Div.A")
    connect(ids["BACK_THICK"], ids["DIV_BACK_T"], None, "A", "BackT → Div.A")
    connect(ids["CONST_2"], ids["DIV_BACK_W"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_BACK_H"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_BACK_T"], None, "B", "2 → Div.B")

    # 靠背 Y = -seat_depth/2 + back_thick/2 (用 Negative + Mass Addition 替代 Subtraction)
    connect(ids["DIV_SEAT_D"], ids["NEG_SEAT_D2_BACK"], "Result", "Value", "SeatD/2 → Neg")
    connect(ids["NEG_SEAT_D2_BACK"], ids["BACK_Y_OFFSET"], None, "Input", "NegSeatD/2 → Add")
    connect(ids["DIV_BACK_T"], ids["BACK_Y_OFFSET"], "Result", "Input", "BackT/2 → Add")

    # 靠背 Z = seat_height + seat_thick + back_height/2
    connect(ids["SEAT_HEIGHT"], ids["BACK_Z_BASE"], None, "Input", "SeatH → Z")
    connect(ids["SEAT_THICK"], ids["BACK_Z_BASE"], None, "Input", "SeatT → Z")
    connect(ids["BACK_Z_BASE"], ids["BACK_CENTER_Z"], "Result", "Input", "Base → Z")
    connect(ids["DIV_BACK_H"], ids["BACK_CENTER_Z"], "Result", "Input", "BackH/2 → Z")

    # 靠背中心點 (Mass Addition 輸出是 "Result")
    connect(ids["BACK_Y_OFFSET"], ids["PT_BACK"], "Result", "Y coordinate", "Y → Pt")
    connect(ids["BACK_CENTER_Z"], ids["PT_BACK"], "Result", "Z coordinate", "Z → Pt")

    # 靠背 Box (使用 XZ Plane)
    connect(ids["PT_BACK"], ids["PLANE_BACK"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_BACK"], ids["BOX_BACK"], "Plane", "Base", "Plane → Box")
    connect(ids["DIV_BACK_W"], ids["BOX_BACK"], "Result", "X", "W/2 → Box.X")
    connect(ids["DIV_BACK_H"], ids["BOX_BACK"], "Result", "Y", "H/2 → Box.Y")
    connect(ids["DIV_BACK_T"], ids["BOX_BACK"], "Result", "Z", "T/2 → Box.Z")

    time.sleep(0.2)

    # =========================================================================
    # Step 9: 連接 - 椅腿基礎
    # =========================================================================
    print("\n[Step 9] 連接椅腿基礎...")

    connect(ids["PLANE_BASE"], ids["CIRCLE_BASE"], "Plane", "Plane", "Plane → Circle")
    connect(ids["LEG_RADIUS"], ids["CIRCLE_BASE"], None, "Radius", "Radius → Circle")
    connect(ids["CIRCLE_BASE"], ids["BOUNDARY"], "Circle", "Edges", "Circle → Boundary")
    connect(ids["UNIT_Z"], ids["AMPLITUDE"], "Unit vector", "Vector", "UnitZ → Amp")
    connect(ids["SEAT_HEIGHT"], ids["AMPLITUDE"], None, "Amplitude", "SeatH → Amp")
    connect(ids["BOUNDARY"], ids["EXTRUDE_LEG"], "Surfaces", "Base", "Surface → Extrude")
    connect(ids["AMPLITUDE"], ids["EXTRUDE_LEG"], "Vector", "Direction", "Vector → Extrude")

    time.sleep(0.2)

    # =========================================================================
    # Step 10: 連接 - 四條腿 Orient
    # =========================================================================
    print("\n[Step 10] 連接四條腿 Orient...")

    # 腿位置:
    # 前左 LEG1: (-W/2, D/2)
    # 前右 LEG2: (W/2, D/2)
    # 後左 LEG3: (-W/2, -D/2)
    # 後右 LEG4: (W/2, -D/2)

    # Negative 組件輸出參數是 "Number" (NickName: N)，需要用 NickName
    leg_coords = [
        ("LEG1", "NEG_SEAT_W2", "DIV_SEAT_D"),   # 前左
        ("LEG2", "DIV_SEAT_W", "DIV_SEAT_D"),    # 前右
        ("LEG3", "NEG_SEAT_W2", "NEG_SEAT_D2"),  # 後左
        ("LEG4", "DIV_SEAT_W", "NEG_SEAT_D2"),   # 後右
    ]

    for leg_name, x_src, y_src in leg_coords:
        # Negative 輸出用 None (自動匹配)，Division 用 "Result"
        x_param = None if "NEG" in x_src else "Result"
        y_param = None if "NEG" in y_src else "Result"

        connect(ids[x_src], ids[f"PT_{leg_name}"], x_param, "X coordinate",
                f"{x_src} → Pt.X")
        connect(ids[y_src], ids[f"PT_{leg_name}"], y_param, "Y coordinate",
                f"{y_src} → Pt.Y")

        # Point → Plane
        connect(ids[f"PT_{leg_name}"], ids[f"PLANE_{leg_name}"], "Point", "Origin",
                f"Pt → Plane ({leg_name})")

        # Orient
        connect(ids["EXTRUDE_LEG"], ids[f"ORIENT_{leg_name}"], "Extrusion", "Geometry",
                f"Extrude → Orient.G ({leg_name})")
        connect(ids["PLANE_BASE"], ids[f"ORIENT_{leg_name}"], "Plane", "Source",
                f"PlaneBase → Orient.A ({leg_name})")
        connect(ids[f"PLANE_{leg_name}"], ids[f"ORIENT_{leg_name}"], "Plane", "Target",
                f"Plane → Orient.B ({leg_name})")

    time.sleep(0.2)

    # =========================================================================
    # Step 11: 連接 - Boolean Union
    # =========================================================================
    print("\n[Step 11] 連接 Boolean Union...")

    # 座面 → Union
    connect(ids["BOX_SEAT"], ids["UNION"], "Box", "Breps", "Seat → Union")

    # 靠背 → Union
    connect(ids["BOX_BACK"], ids["UNION"], "Box", "Breps", "Back → Union")

    # 四條腿 → Union
    for leg_name, _, _ in leg_coords:
        connect(ids[f"ORIENT_{leg_name}"], ids["UNION"], "Geometry", "Breps",
                f"{leg_name} → Union")

    time.sleep(0.3)

    # =========================================================================
    # 儲存 ID 映射
    # =========================================================================
    with open("GH_WIP/component_id_map_chair.json", "w") as f:
        json.dump(ids, f, indent=2)

    print("\n" + "=" * 70)
    print("✓ 椅子創建完成！")
    print("=" * 70)
    print(f"組件數量: {len(ids)}")
    print("ID 映射已儲存: GH_WIP/component_id_map_chair.json")
    print("\n椅子結構：")
    print("  - 座面: Center Box (XY Plane)")
    print("  - 靠背: Center Box (XZ Plane - 垂直)")
    print("  - 四腿: 圓柱 + Orient 到四角")
    print("\n可調參數：")
    print("  - 座面: 寬度/深度/厚度/高度")
    print("  - 靠背: 寬度/高度/厚度")
    print("  - 腿: 半徑")


if __name__ == "__main__":
    main()
