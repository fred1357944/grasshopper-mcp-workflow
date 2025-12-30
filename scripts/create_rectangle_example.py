"""
創建 Grasshopper Rectangle 組件的範例程式

這個程式示範如何使用 MCP 工具以程式設計方式創建 Grasshopper 的 Rectangle 組件。
Rectangle 組件需要以下輸入：
- Plane: 定義矩形所在的平面
- X Size: 矩形的寬度
- Y Size: 矩形的高度

使用方法：
1. 確保 Grasshopper 正在執行，並且 GH_MCP 組件已添加到畫布上
2. 確保 MCP Bridge 伺服器正在執行 (python -m grasshopper_mcp.bridge)
3. 執行此腳本: python create_rectangle_example.py
"""

import socket
import json
import sys
from typing import Dict, Any, Optional

# Grasshopper MCP 連接參數
GRASSHOPPER_HOST = "localhost"
GRASSHOPPER_PORT = 8080


def send_to_grasshopper(command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """向 Grasshopper MCP 發送命令"""
    if params is None:
        params = {}
    
    # 創建命令
    command = {
        "type": command_type,
        "parameters": params
    }
    
    try:
        print(f"發送命令到 Grasshopper: {command_type} 參數: {params}")
        
        # 連接到 Grasshopper MCP
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((GRASSHOPPER_HOST, GRASSHOPPER_PORT))
        
        # 發送命令
        command_json = json.dumps(command)
        client.sendall((command_json + "\n").encode("utf-8"))
        print(f"命令已發送: {command_json}")
        
        # 接收響應
        response_data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if response_data.endswith(b"\n"):
                break
        
        # 處理可能的 BOM
        response_str = response_data.decode("utf-8-sig").strip()
        print(f"收到響應: {response_str}")
        
        # 解析 JSON 響應
        response = json.loads(response_str)
        client.close()
        return response
    except Exception as e:
        print(f"與 Grasshopper 通信時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"與 Grasshopper 通信時出錯: {str(e)}"
        }


def create_rectangle_component():
    """創建 Rectangle 組件及其所需的輸入組件"""
    
    print("=" * 60)
    print("開始創建 Rectangle 組件")
    print("=" * 60)
    
    # 組件位置配置（使用網格佈局）
    positions = {
        "xy_plane": {"x": 100, "y": 100},
        "slider_width": {"x": 100, "y": 250},
        "slider_length": {"x": 100, "y": 400},
        "rectangle": {"x": 400, "y": 250}
    }
    
    component_ids = {}
    
    # 1. 創建 XY Plane 組件（提供平面）
    print("\n1. 創建 XY Plane 組件...")
    result = send_to_grasshopper("add_component", {
        "type": "XY Plane",
        "x": positions["xy_plane"]["x"],
        "y": positions["xy_plane"]["y"]
    })
    
    if result.get("success"):
        # 響應可能使用 "data" 或 "result" 欄位
        component_data = result.get("data") or result.get("result", {})
        component_ids["xy_plane"] = component_data.get("id")
        if component_ids["xy_plane"]:
            print(f"   ✓ XY Plane 創建成功，ID: {component_ids['xy_plane']}")
        else:
            print("   ✗ XY Plane 創建失敗: 未找到組件 ID")
            return None
    else:
        print(f"   ✗ XY Plane 創建失敗: {result.get('error', '未知錯誤')}")
        return None
    
    # 2. 創建寬度滑塊（X Size）
    print("\n2. 創建寬度滑塊 (X Size)...")
    result = send_to_grasshopper("add_component", {
        "type": "Number Slider",
        "x": positions["slider_width"]["x"],
        "y": positions["slider_width"]["y"]
    })
    
    if result.get("success"):
        component_data = result.get("data") or result.get("result", {})
        component_ids["slider_width"] = component_data.get("id")
        if component_ids["slider_width"]:
            print(f"   ✓ 寬度滑塊創建成功，ID: {component_ids['slider_width']}")
        else:
            print("   ✗ 寬度滑塊創建失敗: 未找到組件 ID")
            return None
    else:
        print(f"   ✗ 寬度滑塊創建失敗: {result.get('error', '未知錯誤')}")
        return None
    
    # 3. 創建長度滑塊（Y Size）
    print("\n3. 創建長度滑塊 (Y Size)...")
    result = send_to_grasshopper("add_component", {
        "type": "Number Slider",
        "x": positions["slider_length"]["x"],
        "y": positions["slider_length"]["y"]
    })
    
    if result.get("success"):
        component_data = result.get("data") or result.get("result", {})
        component_ids["slider_length"] = component_data.get("id")
        if component_ids["slider_length"]:
            print(f"   ✓ 長度滑塊創建成功，ID: {component_ids['slider_length']}")
        else:
            print("   ✗ 長度滑塊創建失敗: 未找到組件 ID")
            return None
    else:
        print(f"   ✗ 長度滑塊創建失敗: {result.get('error', '未知錯誤')}")
        return None
    
    # 4. 創建 Rectangle 組件
    print("\n4. 創建 Rectangle 組件...")
    result = send_to_grasshopper("add_component", {
        "type": "Rectangle",
        "x": positions["rectangle"]["x"],
        "y": positions["rectangle"]["y"]
    })
    
    if result.get("success"):
        component_data = result.get("data") or result.get("result", {})
        component_ids["rectangle"] = component_data.get("id")
        if component_ids["rectangle"]:
            print(f"   ✓ Rectangle 創建成功，ID: {component_ids['rectangle']}")
        else:
            print("   ✗ Rectangle 創建失敗: 未找到組件 ID")
            return None
    else:
        print(f"   ✗ Rectangle 創建失敗: {result.get('error', '未知錯誤')}")
        return None
    
    # 5. 連接組件
    print("\n5. 連接組件...")
    
    # 連接 XY Plane 到 Rectangle 的 Plane 輸入
    print("   5.1 連接 XY Plane → Rectangle.Plane...")
    result = send_to_grasshopper("connect_components", {
        "sourceId": component_ids["xy_plane"],
        "targetId": component_ids["rectangle"],
        "sourceParam": "Plane",
        "targetParam": "Plane"
    })
    
    if result.get("success"):
        print("      ✓ XY Plane 連接成功")
    else:
        print(f"      ✗ XY Plane 連接失敗: {result.get('error', '未知錯誤')}")
    
    # 連接寬度滑塊到 Rectangle 的 X Size 輸入
    print("   5.2 連接寬度滑塊 → Rectangle.X Size...")
    result = send_to_grasshopper("connect_components", {
        "sourceId": component_ids["slider_width"],
        "targetId": component_ids["rectangle"],
        "sourceParam": "N",  # Number Slider 的輸出參數名
        "targetParam": "X Size"
    })
    
    if result.get("success"):
        print("      ✓ 寬度滑塊連接成功")
    else:
        print(f"      ✗ 寬度滑塊連接失敗: {result.get('error', '未知錯誤')}")
    
    # 連接長度滑塊到 Rectangle 的 Y Size 輸入
    print("   5.3 連接長度滑塊 → Rectangle.Y Size...")
    result = send_to_grasshopper("connect_components", {
        "sourceId": component_ids["slider_length"],
        "targetId": component_ids["rectangle"],
        "sourceParam": "N",  # Number Slider 的輸出參數名
        "targetParam": "Y Size"
    })
    
    if result.get("success"):
        print("      ✓ 長度滑塊連接成功")
    else:
        print(f"      ✗ 長度滑塊連接失敗: {result.get('error', '未知錯誤')}")
    
    print("\n" + "=" * 60)
    print("Rectangle 組件創建完成！")
    print("=" * 60)
    print("\n創建的組件 ID:")
    for name, comp_id in component_ids.items():
        print(f"  - {name}: {comp_id}")
    
    return component_ids


def create_rectangle_with_custom_size(width: float = 70.0, length: float = 70.0):
    """
    創建帶有自訂尺寸的 Rectangle 組件
    
    參數:
        width: 矩形的寬度（X Size）
        length: 矩形的長度（Y Size）
    """
    print(f"\n創建自訂尺寸的 Rectangle (寬度={width}, 長度={length})...")
    
    # 先創建基本組件
    component_ids = create_rectangle_component()
    
    if component_ids is None:
        print("無法創建 Rectangle 組件")
        return None
    
    # 注意：設定 Number Slider 的值需要通過 Grasshopper 的組件設定介面
    # 這裡我們只是創建了組件，實際的值需要在 Grasshopper 中手動設定
    # 或者可以通過 get_component_info 和相應的設定命令來修改
    
    print("\n提示: 請在 Grasshopper 中手動設定滑塊的值:")
    print(f"  - 寬度滑塊 (X Size): {width}")
    print(f"  - 長度滑塊 (Y Size): {length}")
    
    return component_ids


if __name__ == "__main__":
    print("Grasshopper Rectangle 組件創建程式")
    print("=" * 60)
    print("\n使用說明:")
    print("1. 確保 Grasshopper 正在執行")
    print("2. 確保 GH_MCP 組件已添加到 Grasshopper 畫布上")
    print("3. 確保 MCP Bridge 伺服器正在執行")
    print("   (執行: python -m grasshopper_mcp.bridge)")
    print("=" * 60)
    
    try:
        # 創建基本的 Rectangle 組件
        component_ids = create_rectangle_component()
        
        if component_ids:
            print("\n✓ 成功創建 Rectangle 組件及其輸入組件！")
            print("\n你可以在 Grasshopper 中看到:")
            print("  - XY Plane 組件（提供平面）")
            print("  - 兩個 Number Slider 組件（控制寬度和長度）")
            print("  - Rectangle 組件（輸出矩形曲線）")
        else:
            print("\n✗ 創建 Rectangle 組件失敗")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n程式被使用者中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

