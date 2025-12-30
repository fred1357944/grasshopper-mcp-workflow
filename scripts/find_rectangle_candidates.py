"""
查找 Rectangle 組件的所有候選並測試創建

這個腳本會嘗試不同的方式創建 Rectangle 組件，以查看是否有多個候選。
"""

import socket
import json
import sys
from typing import Optional


def send_to_grasshopper(command_type: str, params: Optional[dict] = None):
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


def test_create_rectangle(method_name: str, params: dict):
    """測試創建 Rectangle 組件"""
    print(f"\n{'=' * 70}")
    print(f"測試方法: {method_name}")
    print(f"參數: {json.dumps(params, indent=2, ensure_ascii=False)}")
    print('-' * 70)
    
    result = send_to_grasshopper("add_component", params)
    
    if result.get("success"):
        component_data = result.get("data") or result.get("result", {})
        print("✓ 創建成功!")
        print(f"  組件 ID: {component_data.get('id', 'N/A')}")
        print(f"  組件類型: {component_data.get('type', 'N/A')}")
        print(f"  組件名稱: {component_data.get('name', 'N/A')}")
        
        # 檢查是否廢棄
        if 'OBSOLETE' in component_data.get('type', ''):
            print("  ⚠️  警告: 這是一個廢棄的組件!")
        
        return component_data
    else:
        error = result.get('error', '未知錯誤')
        print(f"✗ 創建失敗: {error}")
        
        # 如果錯誤資訊包含候選列表，顯示它
        if "Multiple components" in error or "candidates" in error.lower():
            print("\n錯誤資訊中可能包含候選組件列表:")
            print(f"  {error}")
        
        return None


def main():
    """主函數"""
    
    print("=" * 70)
    print("查找 Rectangle 組件的所有候選")
    print("=" * 70)
    
    # 測試 1: 基本創建（只使用名稱）
    test_create_rectangle(
        "方法 1: 只使用名稱 'Rectangle'",
        {
            "type": "Rectangle",
            "x": 100,
            "y": 100
        }
    )
    
    # 測試 2: 使用不同的名稱變體
    variants = ["rectangle", "Rectangle", "RECTANGLE", "Rect"]
    for variant in variants:
        test_create_rectangle(
            f"方法 2: 使用名稱變體 '{variant}'",
            {
                "type": variant,
                "x": 200,
                "y": 100
            }
        )
    
    # 測試 3: 嘗試使用不同的類別
    categories = ["Curve", "Primitive", "Params"]
    for category in categories:
        test_create_rectangle(
            f"方法 3: 使用類別 '{category}'",
            {
                "type": "Rectangle",
                "x": 300,
                "y": 100,
                "category": category
            }
        )
    
    # 測試 4: 嘗試使用 library 參數
    test_create_rectangle(
        "方法 4: 使用 library 'Grasshopper'",
        {
            "type": "Rectangle",
            "x": 400,
            "y": 100,
            "library": "Grasshopper"
        }
    )
    
    print("\n" + "=" * 70)
    print("測試總結")
    print("=" * 70)
    print("\n從測試結果可以看出:")
    print("1. 如果創建成功，查看組件類型名稱")
    print("2. 如果創建失敗並顯示 'Multiple components' 錯誤，")
    print("   錯誤資訊中會包含所有候選組件的詳細資訊")
    print("3. 如果只創建了一個組件（即使是廢棄的），")
    print("   說明系統中可能只有一個 Rectangle 組件")
    print("\n提示:")
    print("- 如果創建的是 OBSOLETE 組件，說明可能沒有非廢棄的版本")
    print("- 或者系統中只有一個 Rectangle 組件")
    print("- 可以嘗試在 Grasshopper 中手動搜尋 'Rectangle' 查看是否有其他版本")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程式被使用者中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

