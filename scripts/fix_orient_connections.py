#!/usr/bin/env python3
"""
修復 Orient 連接問題

問題：Move (OLD) 輸出 Geometry 類型，Orient 需要 Plane 類型
解決：用 Construct Point + XY Plane 代替 Move

步驟：
1. 為每條腿創建 Construct Point（從 X, Y slider）
2. 為每條腿創建 XY Plane（從 Point）
3. 連接到 Orient.Target
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


def main():
    print("=" * 70)
    print("修復 Orient 連接 - 用 Construct Point + XY Plane 代替 Move")
    print("=" * 70)

    # 載入現有 ID 映射
    try:
        with open("GH_WIP/component_id_map_v2.json", "r") as f:
            ids = json.load(f)
        print(f"✓ 載入 {len(ids)} 個組件 ID")
    except FileNotFoundError:
        print("✗ 找不到 component_id_map_v2.json")
        return

    # 測試連接
    result = send_command("get_document_info")
    if not result.get("success"):
        print(f"✗ MCP 連接失敗: {result}")
        return
    print("✓ MCP 連接成功")

    # =========================================================================
    # Step 1: 為每條腿創建 Construct Point 和 XY Plane
    # =========================================================================
    print("\n[Step 1] 創建腿位置的 Construct Point 和 XY Plane...")

    new_ids = {}
    for i in range(1, 5):
        y_offset = 900 + (i-1) * 120

        # Construct Point for leg position
        new_ids[f"POINT_LEG{i}"] = add_component(
            "Construct Point", 500, y_offset, f"腿{i} 位置點"
        )

        # XY Plane at leg position (this outputs proper Plane type!)
        new_ids[f"PLANE_LEG{i}"] = add_component(
            "XY Plane", 600, y_offset, f"腿{i} 平面"
        )

    time.sleep(0.2)

    # =========================================================================
    # Step 2: 連接 Slider -> Construct Point -> XY Plane
    # =========================================================================
    print("\n[Step 2] 連接 Slider → Point → Plane...")

    for i in range(1, 5):
        slider_x = ids.get(f"SLIDER_LEG{i}_X")
        slider_y = ids.get(f"SLIDER_LEG{i}_Y")
        point_id = new_ids.get(f"POINT_LEG{i}")
        plane_id = new_ids.get(f"PLANE_LEG{i}")

        if not all([slider_x, slider_y, point_id, plane_id]):
            print(f"  ⚠️ 跳過腿{i}: 缺少組件")
            continue

        # Slider X -> Point.X coordinate
        connect(slider_x, point_id, None, "X coordinate", f"Slider{i}X → Point.X")

        # Slider Y -> Point.Y coordinate
        connect(slider_y, point_id, None, "Y coordinate", f"Slider{i}Y → Point.Y")

        # Point -> XY Plane.Origin
        connect(point_id, plane_id, "Point", "Origin", f"Point{i} → Plane.Origin")

    time.sleep(0.2)

    # =========================================================================
    # Step 3: 重新連接 Orient 的 Target（用新的 Plane 代替 Move 輸出）
    # =========================================================================
    print("\n[Step 3] 連接新的 Plane → Orient.Target...")

    for i in range(1, 5):
        plane_id = new_ids.get(f"PLANE_LEG{i}")
        orient_id = ids.get(f"ORIENT_LEG{i}")

        if not plane_id or not orient_id:
            print(f"  ⚠️ 跳過腿{i}: 缺少組件")
            continue

        # New Plane -> Orient.Target (now with proper Plane type!)
        connect(plane_id, orient_id, "Plane", "Target", f"Plane{i} → Orient{i}.Target")

    # =========================================================================
    # 儲存更新的 ID 映射
    # =========================================================================
    ids.update(new_ids)
    with open("GH_WIP/component_id_map_v2.json", "w") as f:
        json.dump(ids, f, indent=2)

    print("\n" + "=" * 70)
    print("修復完成！")
    print("=" * 70)
    print("新增組件: 4 個 Construct Point + 4 個 XY Plane")
    print("請在 Grasshopper 中確認 Orient 的紅線是否消失")


if __name__ == "__main__":
    main()
