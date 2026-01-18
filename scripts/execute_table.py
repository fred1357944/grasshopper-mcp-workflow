#!/usr/bin/env python3
"""
執行完整的桌子創建流程

從 GH_WIP/placement_info.json 讀取命令，在 Grasshopper 中創建完整的桌子。

使用方式:
    python scripts/execute_table.py

前置條件:
    1. Grasshopper 已開啟且 MCP Server 運行在 port 8080
    2. GH_WIP/placement_info.json 已生成（運行 tests/test_full_table_workflow.py）
"""

import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient


def load_placement_info(path: str) -> dict:
    """讀取 placement_info.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def execute_add_commands(client: GrasshopperClient, commands: list[dict], max_workers: int = 5) -> dict:
    """
    執行 add_component 命令（並行）

    Returns:
        {
            "success": int,
            "fail": int,
            "id_map": {componentId: actualId}
        }
    """
    results = {
        "success": 0,
        "fail": 0,
        "id_map": {}
    }

    def execute_single(cmd: dict, index: int, total: int) -> tuple[str, str | None]:
        comp_type = cmd["componentType"]
        comp_id = cmd["componentId"]
        x = cmd["x"]
        y = cmd["y"]
        value = cmd.get("value")

        add_params = {
            "type": comp_type,
            "x": x,
            "y": y
        }

        if value is not None:
            add_params["value"] = value

        response = client.send_command("add_component", add_params)

        if response.get("success"):
            actual_id = client.extract_component_id(response)
            print(f"  ✓ [{index}/{total}] {comp_type} -> {comp_id} (ID: {actual_id[:8]}...)")
            return comp_id, actual_id
        else:
            error = response.get("error", "Unknown")
            print(f"  ✗ [{index}/{total}] {comp_type} -> {comp_id}: {error[:50]}")
            return comp_id, None

    total = len(commands)
    print(f"\n創建 {total} 個組件...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_single, cmd, i, total): cmd
            for i, cmd in enumerate(commands, 1)
        }

        for future in as_completed(futures):
            comp_id, actual_id = future.result()
            if actual_id:
                results["success"] += 1
                results["id_map"][comp_id] = actual_id
            else:
                results["fail"] += 1

    return results


def execute_connect_commands(client: GrasshopperClient, commands: list[dict], id_map: dict, sequential: bool = True) -> dict:
    """
    執行 connect_components 命令

    Args:
        sequential: True 使用串行執行（更可靠），False 使用並行

    Returns:
        {
            "success": int,
            "fail": int
        }
    """
    results = {
        "success": 0,
        "fail": 0
    }

    total = len(commands)
    print(f"\n連接 {total} 對組件（{'串行' if sequential else '並行'}）...")

    for index, cmd in enumerate(commands, 1):
        params = cmd.get("parameters", {})
        source_key = params.get("sourceId")
        target_key = params.get("targetId")
        source_param = params.get("sourceParam")
        target_param = params.get("targetParam")

        # 從 ID 映射獲取實際 ID
        source_id = id_map.get(source_key)
        target_id = id_map.get(target_key)

        if not source_id:
            print(f"  ✗ [{index}/{total}] 找不到源組件: {source_key}")
            results["fail"] += 1
            continue

        if not target_id:
            print(f"  ✗ [{index}/{total}] 找不到目標組件: {target_key}")
            results["fail"] += 1
            continue

        # 傳遞參數名（多輸入組件必需）
        connect_params = {
            "sourceId": source_id,
            "targetId": target_id
        }

        # 如果有指定 targetParam，傳遞它（關鍵！）
        target_param = params.get("targetParam")
        if target_param and target_param != "output":
            connect_params["targetParam"] = target_param

        response = client.send_command("connect_components", connect_params)

        # 檢查嵌套的 success
        inner_response = response.get("data", {})
        success = inner_response.get("success", False) if isinstance(inner_response, dict) else False

        if response.get("success") and success:
            print(f"  ✓ [{index}/{total}] {source_key} -> {target_key}")
            results["success"] += 1
        else:
            error = inner_response.get("error", "") if isinstance(inner_response, dict) else response.get("error", "Unknown")
            print(f"  ✗ [{index}/{total}] {source_key} -> {target_key}: {error[:40]}")
            results["fail"] += 1

        # 串行執行時加入小延遲
        if sequential:
            time.sleep(0.05)

    return results


def main():
    print("=" * 70)
    print("執行桌子創建流程")
    print("=" * 70)

    # 路徑
    placement_path = Path("GH_WIP/placement_info.json")

    if not placement_path.exists():
        print(f"✗ 找不到 {placement_path}")
        print("請先運行: python tests/test_full_table_workflow.py")
        return

    # 載入命令
    placement_info = load_placement_info(str(placement_path))
    commands = placement_info.get("commands", [])

    add_commands = [c for c in commands if c["type"] == "add_component"]
    connect_commands = [c for c in commands if c["type"] == "connect_components"]

    print(f"\n描述: {placement_info.get('description', 'N/A')}")
    print(f"add_component: {len(add_commands)} 個")
    print(f"connect_components: {len(connect_commands)} 個")

    # 連接檢查
    client = GrasshopperClient()
    response = client.send_command("get_document_info")

    if not response.get("success"):
        print(f"\n✗ 無法連接到 Grasshopper MCP: {response.get('error')}")
        return

    print(f"\n✓ Grasshopper 已連接")

    # 確認
    print("\n" + "-" * 70)
    print("即將在 Grasshopper 中創建桌子組件。繼續嗎？")
    print("-" * 70)
    user_input = input("輸入 'y' 繼續，其他取消: ").strip().lower()

    if user_input != 'y':
        print("已取消")
        return

    # 執行
    start_time = time.time()

    # 階段 1: 創建組件
    print("\n" + "=" * 70)
    print("階段 1: 創建組件")
    print("=" * 70)

    add_results = execute_add_commands(client, add_commands)
    print(f"\n組件創建完成: {add_results['success']}/{len(add_commands)} 成功")

    if add_results["fail"] > 0:
        print("⚠️  有組件創建失敗，連接可能會受影響")

    # 階段 2: 連接組件
    print("\n" + "=" * 70)
    print("階段 2: 連接組件")
    print("=" * 70)

    connect_results = execute_connect_commands(client, connect_commands, add_results["id_map"])
    print(f"\n組件連接完成: {connect_results['success']}/{len(connect_commands)} 成功")

    # 總結
    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("執行總結")
    print("=" * 70)
    print(f"組件創建: {add_results['success']}/{len(add_commands)} 成功")
    print(f"組件連接: {connect_results['success']}/{len(connect_commands)} 成功")
    print(f"總耗時: {total_time:.2f} 秒")

    if add_results["fail"] == 0 and connect_results["fail"] == 0:
        print("\n🎉 桌子創建完成！請在 Grasshopper 中查看結果。")
    else:
        print("\n⚠️  部分操作失敗，請檢查 Grasshopper 中的錯誤。")

    # 保存 ID 映射
    id_map_path = Path("GH_WIP/component_id_map.json")
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(add_results["id_map"], f, indent=2, ensure_ascii=False)
    print(f"\nID 映射已保存到: {id_map_path}")


if __name__ == "__main__":
    main()
