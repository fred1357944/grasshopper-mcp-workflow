#!/usr/bin/env python3
"""
創建參數化高層建築外殼 - GH_MCP v2.1 能力測試

結構：
- 基座 (Podium): 較寬較矮的裙樓
- 塔樓 (Tower): 高而窄的主體
- 頂冠 (Crown): Loft 收尖效果

參數：
- 基座: 寬度、深度、高度
- 塔樓: 寬度、深度、高度
- 頂冠: 高度、收縮比例
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
    print("創建參數化高層建築外殼 - GH_MCP v2.1")
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

    # 基座參數
    ids["PODIUM_W"] = add_slider(0, 0, 30, 100, 60, "基座寬度")
    ids["PODIUM_D"] = add_slider(0, 50, 30, 100, 50, "基座深度")
    ids["PODIUM_H"] = add_slider(0, 100, 10, 50, 25, "基座高度")

    # 塔樓參數
    ids["TOWER_W"] = add_slider(0, 200, 20, 60, 35, "塔樓寬度")
    ids["TOWER_D"] = add_slider(0, 250, 20, 60, 30, "塔樓深度")
    ids["TOWER_H"] = add_slider(0, 300, 50, 300, 150, "塔樓高度")

    # 頂冠參數
    ids["CROWN_H"] = add_slider(0, 400, 5, 40, 20, "頂冠高度")
    ids["CROWN_RATIO"] = add_slider(0, 450, 0.3, 0.9, 0.6, "頂冠收縮比")

    # 常數
    ids["CONST_2"] = add_slider(0, 550, 0, 10, 2, "常數2")

    time.sleep(0.2)

    # =========================================================================
    # Step 2: 基座幾何
    # =========================================================================
    print("\n[Step 2] 創建基座幾何...")

    # 基座尺寸 /2
    ids["DIV_POD_W"] = add_component("Division", 150, 0, "基座寬/2")
    ids["DIV_POD_D"] = add_component("Division", 150, 50, "基座深/2")
    ids["DIV_POD_H"] = add_component("Division", 150, 100, "基座高/2")

    # 基座中心 Z = podium_height / 2
    ids["PT_PODIUM"] = add_component("Construct Point", 300, 50, "基座中心點")
    ids["PLANE_PODIUM"] = add_component("XY Plane", 400, 50, "基座平面")
    ids["BOX_PODIUM"] = add_component("Center Box", 500, 50, "基座Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 3: 塔樓幾何
    # =========================================================================
    print("\n[Step 3] 創建塔樓幾何...")

    # 塔樓尺寸 /2
    ids["DIV_TWR_W"] = add_component("Division", 150, 200, "塔樓寬/2")
    ids["DIV_TWR_D"] = add_component("Division", 150, 250, "塔樓深/2")
    ids["DIV_TWR_H"] = add_component("Division", 150, 300, "塔樓高/2")

    # 塔樓中心 Z = podium_height + tower_height/2
    ids["TOWER_Z"] = add_component("Mass Addition", 250, 300, "塔樓中心Z")

    ids["PT_TOWER"] = add_component("Construct Point", 350, 250, "塔樓中心點")
    ids["PLANE_TOWER"] = add_component("XY Plane", 450, 250, "塔樓平面")
    ids["BOX_TOWER"] = add_component("Center Box", 550, 250, "塔樓Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 4: 頂冠幾何 (Loft 收尖)
    # =========================================================================
    print("\n[Step 4] 創建頂冠幾何...")

    # 底部矩形 (塔樓頂面位置)
    ids["CROWN_BASE_Z"] = add_component("Mass Addition", 200, 400, "頂冠底Z")  # podium_h + tower_h
    ids["PT_CROWN_BASE"] = add_component("Construct Point", 300, 400, "頂冠底中心")
    ids["PLANE_CROWN_BASE"] = add_component("XY Plane", 400, 400, "頂冠底平面")
    ids["RECT_CROWN_BASE"] = add_component("Rectangle", 500, 400, "頂冠底矩形")

    # 頂部矩形 (收縮後)
    ids["CROWN_TOP_Z"] = add_component("Mass Addition", 200, 500, "頂冠頂Z")  # base_z + crown_h
    ids["PT_CROWN_TOP"] = add_component("Construct Point", 300, 500, "頂冠頂中心")
    ids["PLANE_CROWN_TOP"] = add_component("XY Plane", 400, 500, "頂冠頂平面")

    # 收縮尺寸計算 - 直接在 Rectangle 用縮放後的值
    # 方案: 用 Division 配合 1/ratio 來達成乘法效果
    # 或者簡化設計: 頂部矩形直接用較小的固定比例
    # 這裡改用簡單方案: 頂部尺寸 = 塔樓尺寸 * ratio
    # 用 Division 實現: 塔樓尺寸 / (1/ratio) = 塔樓尺寸 * ratio
    ids["INV_RATIO"] = add_component("Division", 220, 520, "1/ratio")  # 1 / ratio
    ids["CONST_1"] = add_slider(150, 520, 0, 10, 1, "常數1")
    ids["DIV_CROWN_W"] = add_component("Division", 300, 550, "頂冠寬")  # tower_w / (1/ratio)
    ids["DIV_CROWN_D"] = add_component("Division", 300, 600, "頂冠深")  # tower_d / (1/ratio)
    ids["RECT_CROWN_TOP"] = add_component("Rectangle", 500, 550, "頂冠頂矩形")

    # 簡化方案：頂冠用 Center Box（放棄 Loft 收尖）
    # 頂冠中心 Z = crown_base_z + crown_h/2
    ids["DIV_CROWN_H"] = add_component("Division", 580, 450, "頂冠高/2")
    ids["CROWN_CENTER_Z"] = add_component("Mass Addition", 620, 400, "頂冠中心Z")
    ids["PT_CROWN"] = add_component("Construct Point", 680, 400, "頂冠中心點")
    ids["PLANE_CROWN"] = add_component("XY Plane", 750, 400, "頂冠平面")
    ids["BOX_CROWN"] = add_component("Center Box", 820, 400, "頂冠Box")

    time.sleep(0.2)

    # =========================================================================
    # Step 5: Boolean Union
    # =========================================================================
    print("\n[Step 5] 創建 Boolean Union...")

    ids["UNION"] = add_component("Solid Union", 750, 200, "合併")

    time.sleep(0.2)

    # =========================================================================
    # Step 6: 連接 - 基座
    # =========================================================================
    print("\n[Step 6] 連接基座...")

    # 基座尺寸 /2
    connect(ids["PODIUM_W"], ids["DIV_POD_W"], None, "A", "PodW → Div.A")
    connect(ids["PODIUM_D"], ids["DIV_POD_D"], None, "A", "PodD → Div.A")
    connect(ids["PODIUM_H"], ids["DIV_POD_H"], None, "A", "PodH → Div.A")
    connect(ids["CONST_2"], ids["DIV_POD_W"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_POD_D"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_POD_H"], None, "B", "2 → Div.B")

    # 基座中心點 (0, 0, podium_h/2)
    connect(ids["DIV_POD_H"], ids["PT_PODIUM"], "Result", "Z coordinate", "PodH/2 → Pt.Z")

    # 基座 Box
    connect(ids["PT_PODIUM"], ids["PLANE_PODIUM"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_PODIUM"], ids["BOX_PODIUM"], "Plane", "Base", "Plane → Box")
    connect(ids["DIV_POD_W"], ids["BOX_PODIUM"], "Result", "X", "W/2 → Box.X")
    connect(ids["DIV_POD_D"], ids["BOX_PODIUM"], "Result", "Y", "D/2 → Box.Y")
    connect(ids["DIV_POD_H"], ids["BOX_PODIUM"], "Result", "Z", "H/2 → Box.Z")

    time.sleep(0.2)

    # =========================================================================
    # Step 7: 連接 - 塔樓
    # =========================================================================
    print("\n[Step 7] 連接塔樓...")

    # 塔樓尺寸 /2
    connect(ids["TOWER_W"], ids["DIV_TWR_W"], None, "A", "TwrW → Div.A")
    connect(ids["TOWER_D"], ids["DIV_TWR_D"], None, "A", "TwrD → Div.A")
    connect(ids["TOWER_H"], ids["DIV_TWR_H"], None, "A", "TwrH → Div.A")
    connect(ids["CONST_2"], ids["DIV_TWR_W"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_TWR_D"], None, "B", "2 → Div.B")
    connect(ids["CONST_2"], ids["DIV_TWR_H"], None, "B", "2 → Div.B")

    # 塔樓中心 Z = podium_h + tower_h/2
    connect(ids["PODIUM_H"], ids["TOWER_Z"], None, "Input", "PodH → Z")
    connect(ids["DIV_TWR_H"], ids["TOWER_Z"], "Result", "Input", "TwrH/2 → Z")

    # 塔樓中心點
    connect(ids["TOWER_Z"], ids["PT_TOWER"], "Result", "Z coordinate", "Z → Pt")

    # 塔樓 Box
    connect(ids["PT_TOWER"], ids["PLANE_TOWER"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_TOWER"], ids["BOX_TOWER"], "Plane", "Base", "Plane → Box")
    connect(ids["DIV_TWR_W"], ids["BOX_TOWER"], "Result", "X", "W/2 → Box.X")
    connect(ids["DIV_TWR_D"], ids["BOX_TOWER"], "Result", "Y", "D/2 → Box.Y")
    connect(ids["DIV_TWR_H"], ids["BOX_TOWER"], "Result", "Z", "H/2 → Box.Z")

    time.sleep(0.2)

    # =========================================================================
    # Step 8: 連接 - 頂冠
    # =========================================================================
    print("\n[Step 8] 連接頂冠...")

    # 頂冠底 Z = podium_h + tower_h
    connect(ids["PODIUM_H"], ids["CROWN_BASE_Z"], None, "Input", "PodH → BaseZ")
    connect(ids["TOWER_H"], ids["CROWN_BASE_Z"], None, "Input", "TwrH → BaseZ")

    # 頂冠底矩形
    connect(ids["CROWN_BASE_Z"], ids["PT_CROWN_BASE"], "Result", "Z coordinate", "Z → Pt")
    connect(ids["PT_CROWN_BASE"], ids["PLANE_CROWN_BASE"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_CROWN_BASE"], ids["RECT_CROWN_BASE"], "Plane", "Plane", "Plane → Rect")
    connect(ids["TOWER_W"], ids["RECT_CROWN_BASE"], None, "X Size", "TwrW → Rect.X")
    connect(ids["TOWER_D"], ids["RECT_CROWN_BASE"], None, "Y Size", "TwrD → Rect.Y")

    # 頂冠頂 Z = base_z + crown_h
    connect(ids["CROWN_BASE_Z"], ids["CROWN_TOP_Z"], "Result", "Input", "BaseZ → TopZ")
    connect(ids["CROWN_H"], ids["CROWN_TOP_Z"], None, "Input", "CrownH → TopZ")

    # 頂部收縮尺寸 - 用 Division 實現乘法: A * ratio = A / (1/ratio)
    # Step 1: 計算 1/ratio
    connect(ids["CONST_1"], ids["INV_RATIO"], None, "A", "1 → InvRatio.A")
    connect(ids["CROWN_RATIO"], ids["INV_RATIO"], None, "B", "Ratio → InvRatio.B")

    # Step 2: tower_w / (1/ratio) = tower_w * ratio
    connect(ids["TOWER_W"], ids["DIV_CROWN_W"], None, "A", "TwrW → DivW.A")
    connect(ids["INV_RATIO"], ids["DIV_CROWN_W"], "Result", "B", "InvRatio → DivW.B")

    # Step 3: tower_d / (1/ratio) = tower_d * ratio
    connect(ids["TOWER_D"], ids["DIV_CROWN_D"], None, "A", "TwrD → DivD.A")
    connect(ids["INV_RATIO"], ids["DIV_CROWN_D"], "Result", "B", "InvRatio → DivD.B")

    # 頂冠頂矩形
    connect(ids["CROWN_TOP_Z"], ids["PT_CROWN_TOP"], "Result", "Z coordinate", "Z → Pt")
    connect(ids["PT_CROWN_TOP"], ids["PLANE_CROWN_TOP"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_CROWN_TOP"], ids["RECT_CROWN_TOP"], "Plane", "Plane", "Plane → Rect")
    # Division 輸出用 Result
    connect(ids["DIV_CROWN_W"], ids["RECT_CROWN_TOP"], "Result", "X Size", "CrownW → Rect.X")
    connect(ids["DIV_CROWN_D"], ids["RECT_CROWN_TOP"], "Result", "Y Size", "CrownD → Rect.Y")

    # 頂冠 Box 連接（簡化版本）
    # 頂冠高 / 2
    connect(ids["CROWN_H"], ids["DIV_CROWN_H"], None, "A", "CrownH → Div.A")
    connect(ids["CONST_2"], ids["DIV_CROWN_H"], None, "B", "2 → Div.B")

    # 頂冠中心 Z = crown_base_z + crown_h/2
    connect(ids["CROWN_BASE_Z"], ids["CROWN_CENTER_Z"], "Result", "Input", "BaseZ → CenterZ")
    connect(ids["DIV_CROWN_H"], ids["CROWN_CENTER_Z"], "Result", "Input", "H/2 → CenterZ")

    # 頂冠中心點
    connect(ids["CROWN_CENTER_Z"], ids["PT_CROWN"], "Result", "Z coordinate", "Z → Pt.Z")

    # 頂冠平面和 Box
    connect(ids["PT_CROWN"], ids["PLANE_CROWN"], "Point", "Origin", "Pt → Plane")
    connect(ids["PLANE_CROWN"], ids["BOX_CROWN"], "Plane", "Base", "Plane → Box.Base")
    connect(ids["DIV_CROWN_W"], ids["BOX_CROWN"], "Result", "X", "W/2 → Box.X")
    connect(ids["DIV_CROWN_D"], ids["BOX_CROWN"], "Result", "Y", "D/2 → Box.Y")
    connect(ids["DIV_CROWN_H"], ids["BOX_CROWN"], "Result", "Z", "H/2 → Box.Z")

    time.sleep(0.2)

    # =========================================================================
    # Step 9: 連接 - Boolean Union
    # =========================================================================
    print("\n[Step 9] 連接 Boolean Union...")

    connect(ids["BOX_PODIUM"], ids["UNION"], "Box", "Breps", "Podium → Union")
    connect(ids["BOX_TOWER"], ids["UNION"], "Box", "Breps", "Tower → Union")
    connect(ids["BOX_CROWN"], ids["UNION"], "Box", "Breps", "Crown → Union")

    time.sleep(0.3)

    # =========================================================================
    # 儲存 ID 映射
    # =========================================================================
    with open("GH_WIP/component_id_map_tower.json", "w") as f:
        json.dump(ids, f, indent=2)

    print("\n" + "=" * 70)
    print("✓ 高層建築外殼創建完成！")
    print("=" * 70)
    print(f"組件數量: {len(ids)}")
    print("ID 映射已儲存: GH_WIP/component_id_map_tower.json")
    print("\n建築結構：")
    print("  - 基座 (Podium): 60x50x25")
    print("  - 塔樓 (Tower): 35x30x150")
    print("  - 頂冠 (Crown): Loft 收尖, 高度20, 收縮60%")
    print("\n可調參數：")
    print("  - 基座: 寬度/深度/高度")
    print("  - 塔樓: 寬度/深度/高度")
    print("  - 頂冠: 高度/收縮比例")


if __name__ == "__main__":
    main()
