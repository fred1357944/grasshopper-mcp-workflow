#!/usr/bin/env python3
"""
測試增強版 GH_MCP 的 set_slider_value 命令
"""

import socket
import json
import time


def send_command(command_type: str, params: dict = None, debug: bool = False) -> dict:
    """發送單個命令到 GH_MCP（每次建立新連接）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", 8080))

        command = {"Type": command_type}
        if params:
            command["Params"] = params

        message = json.dumps(command) + "\n"
        if debug:
            print(f"    [DEBUG] 發送: {message.strip()}")
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

        if debug:
            print(f"    [DEBUG] 收到原始: {response[:200]}")

        # 處理 BOM 和解碼
        decoded = response.decode("utf-8-sig").strip()
        if debug:
            print(f"    [DEBUG] 解碼後: {decoded[:200]}")

        if not decoded:
            return {"error": "Empty response"}

        return json.loads(decoded)

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}", "raw": decoded[:100] if 'decoded' in dir() else "N/A"}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("測試增強版 GH_MCP")
    print("=" * 60)

    # 測試 1: 基本連接（帶除錯）
    print("\n[測試 1] get_document_info - 確認連接")
    result = send_command("get_document_info", debug=True)

    if "error" in result and "Connection refused" in str(result.get("error", "")):
        print(f"  ✗ 連接失敗: {result['error']}")
        print("\n請確認:")
        print("  1. Rhino/Grasshopper 已啟動")
        print("  2. GH_MCP 組件已放置且 Enabled=true")
        return

    if "error" in result:
        print(f"  ⚠️ 錯誤: {result}")
    else:
        data = result.get("Data", {})
        component_count = data.get("componentCount", "?")
        print(f"  ✓ 連接成功！組件數量: {component_count}")

    time.sleep(0.2)

    # 測試 2: set_slider_value
    print("\n[測試 2] set_slider_value - 核心增強功能")

    # 從 component_id_map.json 讀取
    try:
        with open("GH_WIP/component_id_map.json", "r") as f:
            id_map = json.load(f)
        slider_id = id_map.get("SLIDER_LENGTH")
        if slider_id:
            print(f"  使用 SLIDER_LENGTH: {slider_id[:8]}...")
        else:
            print("  ⚠️ 找不到 SLIDER_LENGTH，跳過此測試")
            slider_id = None
    except FileNotFoundError:
        print("  ⚠️ 找不到 component_id_map.json")
        slider_id = None

    if slider_id:
        result = send_command("set_slider_value", {
            "componentId": slider_id,
            "value": 120.0
        }, debug=True)

        print(f"  回應: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if result.get("Success"):
            print("  ✓ set_slider_value 命令成功！增強版 MCP 運作正常")
        elif "Unknown command" in str(result):
            print("  ✗ 命令未註冊 - 增強版可能未正確載入")
        elif "not found" in str(result).lower():
            print("  ⚠️ Slider 組件未找到（但命令已註冊）")
        else:
            print("  ? 需要分析回應")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
