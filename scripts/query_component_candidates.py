"""
查詢組件候選工具

這個腳本可以查詢指定名稱的所有組件候選，並顯示詳細信息：
- 組件名稱和 GUID
- 所屬類別和子類別
- 所屬庫/插件名稱
- 是否廢棄
- 是否內置組件
- 描述
- 輸入輸出參數
"""

import socket
import json
import sys
from typing import Dict, Any, Optional


def send_to_grasshopper(command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """向 Grasshopper MCP 發送命令"""
    if params is None:
        params = {}
    
    command = {
        "type": command_type,
        "parameters": params
    }
    
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
        return {
            "success": False,
            "error": f"與 Grasshopper 通信時出錯: {str(e)}"
        }


def query_component_candidates(component_name: str):
    """
    查詢組件候選
    
    參數:
        component_name: 要查詢的組件名稱（如 "Rectangle", "Number Slider"）
    
    返回:
        包含所有候選組件信息的字典
    """
    print("=" * 80)
    print(f"查詢組件候選: '{component_name}'")
    print("=" * 80)
    
    result = send_to_grasshopper("get_component_candidates", {
        "name": component_name
    })
    
    if result.get("success"):
        response_data = result.get("data") or result.get("result", {})
        
        query = response_data.get("query", component_name)
        normalized_query = response_data.get("normalizedQuery", component_name)
        count = response_data.get("count", 0)
        candidates = response_data.get("candidates", [])
        
        print(f"\n查詢: '{query}'")
        print(f"標準化查詢: '{normalized_query}'")
        print(f"找到 {count} 個候選組件\n")
        
        if count == 0:
            print("未找到匹配的組件。")
            print("\n提示:")
            print("- 檢查組件名稱是否正確")
            print("- 嘗試使用部分名稱搜索")
            return None
        
        # 顯示每個候選組件的詳細信息
        for i, candidate in enumerate(candidates, 1):
            print("=" * 80)
            print(f"候選 {i}/{count}: {candidate.get('name', 'N/A')}")
            print("=" * 80)
            
            # 基本信息
            print(f"  名稱: {candidate.get('name', 'N/A')}")
            print(f"  完整名稱: {candidate.get('fullName', 'N/A')}")
            print(f"  類型名稱: {candidate.get('typeName', 'N/A')}")
            print(f"  GUID: {candidate.get('guid', 'N/A')}")
            
            # 類別信息
            print("\n  類別信息:")
            print(f"    類別: {candidate.get('category', 'N/A')}")
            print(f"    子類別: {candidate.get('subCategory', 'N/A')}")
            
            # 庫/插件信息
            print("\n  庫/插件信息:")
            library = candidate.get('library', 'N/A')
            is_built_in = candidate.get('isBuiltIn', False)
            print(f"    庫名稱: {library}")
            if is_built_in:
                print("    ✓ 內置組件 (Built-in Grasshopper component)")
            else:
                print("    - 第三方插件組件")
            
            # 狀態信息
            print("\n  狀態信息:")
            is_obsolete = candidate.get('obsolete', False)
            if is_obsolete:
                print("    ⚠️  廢棄組件 (Obsolete/Deprecated)")
                print("    ⚠️  不推薦使用")
            else:
                print("    ✓ 正常組件 (Not Obsolete)")
                print("    ✓ 推薦使用")
            
            # 描述
            description = candidate.get('description', 'N/A')
            print("\n  描述:")
            if description and description != "No description available":
                # 如果描述太長，換行顯示
                desc_lines = description.split('\n')
                for line in desc_lines[:5]:  # 最多顯示5行
                    print(f"    {line}")
                if len(desc_lines) > 5:
                    print(f"    ... (還有 {len(desc_lines) - 5} 行)")
            else:
                print(f"    {description}")
            
            # 輸入參數
            inputs = candidate.get('inputs', [])
            if inputs and len(inputs) > 0:
                print(f"\n  輸入參數 ({len(inputs)} 個):")
                for inp in inputs:
                    if isinstance(inp, dict):
                        inp_name = inp.get('name', 'N/A')
                        inp_nickname = inp.get('nickname', '')
                        inp_type = inp.get('type', 'N/A')
                        inp_desc = inp.get('description', '')
                        nickname_str = f" ({inp_nickname})" if inp_nickname else ""
                        desc_str = f" - {inp_desc}" if inp_desc else ""
                        print(f"    - {inp_name}{nickname_str} [{inp_type}]{desc_str}")
                    else:
                        print(f"    - {inp}")
            else:
                print("\n  輸入參數: 無")
            
            # 輸出參數
            outputs = candidate.get('outputs', [])
            if outputs and len(outputs) > 0:
                print(f"\n  輸出參數 ({len(outputs)} 個):")
                for out in outputs:
                    if isinstance(out, dict):
                        out_name = out.get('name', 'N/A')
                        out_nickname = out.get('nickname', '')
                        out_type = out.get('type', 'N/A')
                        out_desc = out.get('description', '')
                        nickname_str = f" ({out_nickname})" if out_nickname else ""
                        desc_str = f" - {out_desc}" if out_desc else ""
                        print(f"    - {out_name}{nickname_str} [{out_type}]{desc_str}")
                    else:
                        print(f"    - {out}")
            else:
                print("\n  輸出參數: 無")
            
            print()
        
        # 總結和建議
        print("=" * 80)
        print("總結和建議")
        print("=" * 80)
        
        # 統計
        non_obsolete = [c for c in candidates if not c.get('obsolete', False)]
        built_in = [c for c in candidates if c.get('isBuiltIn', False)]
        recommended = [c for c in candidates if not c.get('obsolete', False) and c.get('isBuiltIn', False)]
        
        print("\n統計:")
        print(f"  總候選數: {count}")
        print(f"  非廢棄組件: {len(non_obsolete)}")
        print(f"  內置組件: {len(built_in)}")
        print(f"  推薦組件 (非廢棄 + 內置): {len(recommended)}")
        
        if len(recommended) > 0:
            print("\n✓ 推薦使用的組件:")
            for i, rec in enumerate(recommended, 1):
                print(f"  {i}. {rec.get('name', 'N/A')} (GUID: {rec.get('guid', 'N/A')})")
        elif len(non_obsolete) > 0:
            print("\n✓ 可用的非廢棄組件:")
            for i, rec in enumerate(non_obsolete, 1):
                print(f"  {i}. {rec.get('name', 'N/A')} (GUID: {rec.get('guid', 'N/A')})")
        else:
            print("\n⚠️  警告: 所有候選組件都是廢棄的!")
            print("  雖然可以繼續使用，但建議查找替代方案。")
        
        print("\n使用建議:")
        print("  1. 優先使用非廢棄的內置組件")
        print("  2. 如果只有一個候選，可以直接使用組件名稱創建")
        print("  3. 如果有多個候選，使用 GUID 來精確指定:")
        print("     send_to_grasshopper('add_component', {")
        print(f"         'type': '{component_name}',")
        print("         'x': 100,")
        print("         'y': 100,")
        print("         'guid': 'your-guid-here'")
        print("     })")
        
        return {
            "query": query,
            "normalizedQuery": normalized_query,
            "count": count,
            "candidates": candidates,
            "recommended": recommended,
            "nonObsolete": non_obsolete
        }
    else:
        error = result.get('error', '未知錯誤')
        print(f"\n✗ 查詢失敗: {error}")
        return None


def main():
    """主函數"""
    if len(sys.argv) > 1:
        component_name = sys.argv[1]
    else:
        # 如果沒有提供參數，使用默認值或提示用戶
        print("組件候選查詢工具")
        print("=" * 80)
        print("\n使用方法:")
        print("  python query_component_candidates.py <組件名稱>")
        print("\n示例:")
        print("  python query_component_candidates.py Rectangle")
        print("  python query_component_candidates.py \"Number Slider\"")
        print("  python query_component_candidates.py Circle")
        print("\n" + "=" * 80)
        
        # 交互式輸入
        component_name = input("\n請輸入要查詢的組件名稱 (或按 Enter 使用 'Rectangle'): ").strip()
        if not component_name:
            component_name = "Rectangle"
    
    try:
        result = query_component_candidates(component_name)
        
        if result:
            print("\n" + "=" * 80)
            print("查詢完成!")
            print("=" * 80)
    except KeyboardInterrupt:
        print("\n\n程式被使用者中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

