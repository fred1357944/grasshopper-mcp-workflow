"""
查詢 Rectangle 組件的所有候選組件

這個腳本會搜尋 Grasshopper 中所有名為 "Rectangle" 的組件候選，
並顯示它們的詳細資訊，包括 GUID、類別、是否廢棄等。
"""

import socket
import json
import sys


def send_to_grasshopper(command_type: str, params: dict = None):
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
    """主函數：查詢 Rectangle 候選組件"""
    
    print("=" * 70)
    print("查詢 Rectangle 組件的所有候選組件")
    print("=" * 70)
    
    # 搜尋所有包含 "Rectangle" 的組件
    print("\n正在搜尋所有 Rectangle 組件候選...")
    result = send_to_grasshopper("search_components", {
        "query": "Rectangle"
    })
    
    if result.get("success"):
        component_data = result.get("data") or result.get("result", {})
        candidates = component_data if isinstance(component_data, list) else component_data.get("components", [])
        
        if candidates:
            print(f"\n找到 {len(candidates)} 個 Rectangle 候選組件:\n")
            
            for i, candidate in enumerate(candidates, 1):
                print(f"{'=' * 70}")
                print(f"候選 {i}:")
                print(f"  名稱: {candidate.get('name', 'N/A')}")
                print(f"  完整名稱: {candidate.get('fullName', 'N/A')}")
                print(f"  GUID: {candidate.get('guid', 'N/A')}")
                print(f"  類別: {candidate.get('category', 'N/A')}")
                print(f"  子類別: {candidate.get('subCategory', 'N/A')}")
                print(f"  庫/插件: {candidate.get('library', 'N/A')}")
                print(f"  是否內建: {candidate.get('isBuiltIn', False)}")
                print(f"  是否廢棄: {candidate.get('obsolete', False)}")
                print(f"  描述: {candidate.get('description', 'N/A')}")
                
                # 顯示輸入參數
                if candidate.get('inputs'):
                    print("  輸入參數:")
                    for inp in candidate.get('inputs', []):
                        inp_name = inp.get('name', 'N/A') if isinstance(inp, dict) else str(inp)
                        inp_type = inp.get('type', 'N/A') if isinstance(inp, dict) else 'N/A'
                        print(f"    - {inp_name} ({inp_type})")
                
                # 顯示輸出參數
                if candidate.get('outputs'):
                    print("  輸出參數:")
                    for out in candidate.get('outputs', []):
                        out_name = out.get('name', 'N/A') if isinstance(out, dict) else str(out)
                        out_type = out.get('type', 'N/A') if isinstance(out, dict) else 'N/A'
                        print(f"    - {out_name} ({out_type})")
                
                print()
        else:
            print("\n未找到 Rectangle 候選組件")
    else:
        print(f"\n搜尋失敗: {result.get('error', '未知錯誤')}")
        print("\n嘗試直接創建 Rectangle 組件以查看錯誤資訊...")
        
        # 嘗試創建一個 Rectangle 組件，看看會返回什麼錯誤資訊
        print("\n嘗試創建 Rectangle 組件...")
        create_result = send_to_grasshopper("add_component", {
            "type": "Rectangle",
            "x": 100,
            "y": 100
        })
        
        if create_result.get("success"):
            component_data = create_result.get("data") or create_result.get("result", {})
            print("\n成功創建 Rectangle 組件:")
            print(f"  ID: {component_data.get('id', 'N/A')}")
            print(f"  類型: {component_data.get('type', 'N/A')}")
            print(f"  名稱: {component_data.get('name', 'N/A')}")
            print(f"\n注意: 創建的是 '{component_data.get('type', 'N/A')}' 類型")
            if 'OBSOLETE' in component_data.get('type', ''):
                print("  ⚠️  這是一個廢棄的組件！")
        else:
            error_msg = create_result.get('error', '未知錯誤')
            print(f"\n創建失敗: {error_msg}")
            
            # 如果錯誤資訊包含候選列表，顯示它
            if "candidates" in error_msg.lower() or "multiple" in error_msg.lower():
                print("\n錯誤資訊中可能包含候選組件列表，請查看上面的完整錯誤資訊。")
    
    print("\n" + "=" * 70)
    print("查詢完成")
    print("=" * 70)
    
    print("\n提示:")
    print("如果找到多個候選組件，你可以使用以下參數來指定要創建的組件:")
    print("  - guid: 使用組件的 GUID（最可靠）")
    print("  - category: 使用組件的類別")
    print("  - library: 使用組件所屬的庫/插件名稱")
    print("\n範例:")
    print('  send_to_grasshopper("add_component", {')
    print('      "type": "Rectangle",')
    print('      "x": 100,')
    print('      "y": 100,')
    print('      "guid": "your-guid-here"  # 或使用 category/library')
    print('  })')


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

