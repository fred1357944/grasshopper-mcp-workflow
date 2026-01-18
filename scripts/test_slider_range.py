#!/usr/bin/env python3
"""
測試 Slider 範圍修復 - 簡單測試腳本
驗證 add_component_advanced 是否正確設定 slider 的 min/max/value
"""

import socket
import json

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


def main():
    print("=" * 60)
    print("測試 Slider 範圍修復")
    print("=" * 60)

    # 測試連接
    result = send_command("get_document_info")
    if not result.get("success"):
        print(f"✗ MCP 連接失敗: {result}")
        return False

    print("✓ MCP 連接成功")

    # 清除 canvas
    print("\n[1] 清除 canvas...")
    result = send_command("clear_document")

    # 創建測試 slider
    print("\n[2] 創建測試 slider (期望: min=0, max=200, value=120)...")
    result = send_command("add_component_advanced", {
        "type": "Number Slider",
        "x": 100,
        "y": 100,
        "initialParams": {
            "min": 0,
            "max": 200,
            "value": 120
        },
        "name": "測試Slider"
    })

    if not result.get("success"):
        print(f"✗ 創建失敗: {result}")
        return False

    comp_id = result.get("data", {}).get("componentId") or result.get("data", {}).get("id")
    print(f"✓ 創建成功, ID: {comp_id}")

    # 查詢 slider 詳情
    print("\n[3] 查詢 slider 詳情...")
    result = send_command("get_component_details", {"componentId": comp_id})

    if not result.get("success"):
        print(f"✗ 查詢失敗: {result}")
        return False

    params = result.get("data", {}).get("parameters", {})
    actual_min = params.get("min", "N/A")
    actual_max = params.get("max", "N/A")
    actual_value = params.get("value", "N/A")

    print(f"\n結果:")
    print(f"  min:   {actual_min} (期望: 0)")
    print(f"  max:   {actual_max} (期望: 200)")
    print(f"  value: {actual_value} (期望: 120)")

    # 驗證
    print("\n" + "=" * 60)

    # 容許一點浮點誤差
    min_ok = abs(float(actual_min) - 0) < 0.01
    max_ok = abs(float(actual_max) - 200) < 0.01
    val_ok = abs(float(actual_value) - 120) < 0.01

    if min_ok and max_ok and val_ok:
        print("✓✓✓ 測試通過！Slider 範圍修復成功！")
        return True
    else:
        print("✗✗✗ 測試失敗！Slider 範圍仍然有問題")
        if not min_ok:
            print(f"  - min 錯誤: 期望 0, 實際 {actual_min}")
        if not max_ok:
            print(f"  - max 錯誤: 期望 200, 實際 {actual_max}")
        if not val_ok:
            print(f"  - value 錯誤: 期望 120, 實際 {actual_value}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
