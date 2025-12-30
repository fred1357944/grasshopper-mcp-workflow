"""
簡單的 Rectangle 組件創建範例

這個版本使用更簡潔的方式創建 Rectangle 組件。
可以直接通過 MCP 工具呼叫，或者作為獨立腳本執行。
"""

import socket
import json
from typing import Optional


def send_command(command_type: str, params: Optional[dict] = None):
    """發送命令到 Grasshopper MCP"""
    if params is None:
        params = {}
    
    command = {"type": command_type, "parameters": params}
    
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("localhost", 8080))
        client.sendall((json.dumps(command) + "\n").encode("utf-8"))
        
        response_data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if response_data.endswith(b"\n"):
                break
        
        response = json.loads(response_data.decode("utf-8-sig").strip())
        client.close()
        return response
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """主函數：創建 Rectangle 組件"""
    
    # 創建 XY Plane
    plane = send_command("add_component", {
        "type": "XY Plane",
        "x": 100,
        "y": 100
    })
    plane_id = plane.get("result", {}).get("id") if plane.get("success") else None
    
    # 創建寬度滑塊
    width_slider = send_command("add_component", {
        "type": "Number Slider",
        "x": 100,
        "y": 250
    })
    width_id = width_slider.get("result", {}).get("id") if width_slider.get("success") else None
    
    # 創建長度滑塊
    length_slider = send_command("add_component", {
        "type": "Number Slider",
        "x": 100,
        "y": 400
    })
    length_id = length_slider.get("result", {}).get("id") if length_slider.get("success") else None
    
    # 創建 Rectangle
    rectangle = send_command("add_component", {
        "type": "Rectangle",
        "x": 400,
        "y": 250
    })
    rect_id = rectangle.get("result", {}).get("id") if rectangle.get("success") else None
    
    # 連接組件
    if all([plane_id, width_id, length_id, rect_id]):
        send_command("connect_components", {
            "sourceId": plane_id,
            "targetId": rect_id,
            "sourceParam": "Plane",
            "targetParam": "Plane"
        })
        
        send_command("connect_components", {
            "sourceId": width_id,
            "targetId": rect_id,
            "sourceParam": "N",
            "targetParam": "X Size"
        })
        
        send_command("connect_components", {
            "sourceId": length_id,
            "targetId": rect_id,
            "sourceParam": "N",
            "targetParam": "Y Size"
        })
        
        print("✓ Rectangle 組件創建成功！")
    else:
        print("✗ 創建組件失敗")


if __name__ == "__main__":
    main()

