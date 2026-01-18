#!/usr/bin/env python3
"""
快速測試 set_slider_value：先創建一個 slider，再設定值
"""

import socket
import json
import time


def send_command(command_type: str, params: dict = None) -> dict:
    """發送命令到 GH_MCP"""
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
        return json.loads(response.decode("utf-8-sig").strip())

    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("快速測試 set_slider_value")
    print("=" * 60)

    # Step 1: 創建一個新 slider
    print("\n[Step 1] 創建 Number Slider...")
    result = send_command("add_component", {
        "Type": "Number Slider",
        "X": 100,
        "Y": 100
    })

    if not result.get("success"):
        print(f"  ✗ 創建失敗: {result}")
        return

    slider_id = result.get("data", {}).get("id")
    if not slider_id:
        print(f"  ✗ 未獲得 slider ID: {result}")
        return

    print(f"  ✓ Slider 創建成功！ID: {slider_id}")

    time.sleep(0.2)

    # Step 2: 設定 slider 值
    print("\n[Step 2] 使用 set_slider_value 設定值為 123.45...")
    result = send_command("set_slider_value", {
        "componentId": slider_id,
        "value": 123.45
    })

    print(f"  回應: {json.dumps(result, indent=2, ensure_ascii=False)}")

    if result.get("success"):
        print("\n🎉 成功！增強版 set_slider_value 命令運作正常！")
        print("   請在 Grasshopper 中確認 slider 值已變為 123.45")
    else:
        error = result.get("error", "")
        if "Unknown command" in error:
            print("\n✗ 命令未註冊 - 使用的是舊版 GH_MCP")
        else:
            print(f"\n⚠️ 設定失敗: {error}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
