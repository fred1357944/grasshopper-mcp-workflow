#!/usr/bin/env python3
"""
使用增強版 MCP 設定桌子的所有 slider 值

桌子設計規格：
- 桌面: 120 x 80 x 5 cm
- 桌高: 75 cm (桌面中心 Z = 72.5)
- 腿: 半徑 3 cm, 高 70 cm
- 四腿位置: (±50, ±30, 0) 距離中心
"""

import socket
import json
import time


def send_command(command_type: str, params: dict = None) -> dict:
    """發送單個命令到 GH_MCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", 8080))

        command = {"Type": command_type}
        if params:
            command["Params"] = params

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
        return json.loads(response.decode("utf-8"))

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# 桌子參數定義
# ============================================================================
TABLE_PARAMS = {
    # 桌面尺寸
    "SLIDER_LENGTH": 120.0,      # 桌面長度
    "SLIDER_WIDTH": 80.0,        # 桌面寬度
    "SLIDER_TOP_HEIGHT": 5.0,    # 桌面厚度
    "SLIDER_TOP_Z": 72.5,        # 桌面中心 Z 座標

    # 桌腿
    "SLIDER_RADIUS_LEG": 3.0,    # 腿半徑
    "SLIDER_LEG_HEIGHT": 70.0,   # 腿高度

    # 腿 1 (前右)
    "SLIDER_LEG1_X": 50.0,
    "SLIDER_LEG1_Y": 30.0,
    "SLIDER_LEG1_Z": 0.0,

    # 腿 2 (前左)
    "SLIDER_LEG2_X": -50.0,
    "SLIDER_LEG2_Y": 30.0,
    "SLIDER_LEG2_Z": 0.0,

    # 腿 3 (後左)
    "SLIDER_LEG3_X": -50.0,
    "SLIDER_LEG3_Y": -30.0,
    "SLIDER_LEG3_Z": 0.0,

    # 腿 4 (後右)
    "SLIDER_LEG4_X": 50.0,
    "SLIDER_LEG4_Y": -30.0,
    "SLIDER_LEG4_Z": 0.0,
}


def main():
    print("=" * 60)
    print("設定參數桌 Slider 值（增強版 MCP）")
    print("=" * 60)

    # 載入 ID 映射
    try:
        with open("GH_WIP/component_id_map.json", "r") as f:
            id_map = json.load(f)
        print(f"✓ 載入 {len(id_map)} 個組件 ID")
    except FileNotFoundError:
        print("✗ 找不到 GH_WIP/component_id_map.json")
        return

    # 測試連接
    print("\n檢查 MCP 連接...")
    result = send_command("get_document_info")
    if "error" in result:
        print(f"✗ 連接失敗: {result['error']}")
        print("\n請確認 GH_MCP 組件已啟用")
        return
    print("✓ MCP 連接成功")

    # 先測試增強版命令是否可用
    print("\n檢查 set_slider_value 命令...")
    test_slider_id = id_map.get("SLIDER_LENGTH")
    if not test_slider_id:
        print("✗ 找不到 SLIDER_LENGTH")
        return

    result = send_command("set_slider_value", {
        "componentId": test_slider_id,
        "value": 120.0
    })

    if "Unknown command" in str(result):
        print("✗ set_slider_value 命令未註冊")
        print("  可能原因: 仍在使用舊版 GH_MCP.gha")
        print("  解決方案: 請重新啟動 Rhino 以載入增強版")
        return
    elif result.get("Success") or (result.get("Data", {}).get("success")):
        print("✓ set_slider_value 命令可用！")
    else:
        print(f"⚠️ 測試結果: {result}")
        # 繼續嘗試，可能只是回應格式不同

    # 設定所有 slider
    print("\n" + "-" * 60)
    print("開始設定 slider 值...")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    for slider_name, value in TABLE_PARAMS.items():
        slider_id = id_map.get(slider_name)

        if not slider_id:
            print(f"  ⚠️ 跳過 {slider_name}: 未找到 ID")
            fail_count += 1
            continue

        result = send_command("set_slider_value", {
            "componentId": slider_id,
            "value": float(value)
        })

        # 檢查結果
        if result.get("Success") or result.get("Data", {}).get("success"):
            print(f"  ✓ {slider_name} = {value}")
            success_count += 1
        elif "error" not in str(result).lower():
            # 可能成功但回應格式不同
            print(f"  ? {slider_name} = {value} (回應: {str(result)[:50]})")
            success_count += 1
        else:
            print(f"  ✗ {slider_name}: {result.get('error', result)}")
            fail_count += 1

        time.sleep(0.05)  # 小延遲避免過快

    # 總結
    print("\n" + "=" * 60)
    print("設定完成")
    print("=" * 60)
    print(f"成功: {success_count}")
    print(f"失敗: {fail_count}")

    if fail_count == 0:
        print("\n🎉 所有 slider 已設定！請在 Grasshopper/Rhino 中查看桌子。")
    else:
        print(f"\n⚠️ 有 {fail_count} 個設定失敗")


if __name__ == "__main__":
    main()
