#!/usr/bin/env python3
"""
重建桌子（優化版）

清除 Grasshopper 文檔，使用正確的 slider 數值重建桌子。

優化策略：
1. 由於 MCP 不支援 set_slider_value，使用 clear_document + 重新創建
2. add_component 支援 value 參數，可設定 slider 初始值
3. 一次完整執行，不需要手動干預

使用方式:
    python scripts/rebuild_table_optimized.py

前置條件:
    1. Grasshopper 已開啟且 MCP Server 運行在 port 8080
"""

import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient


# ============================================================================
# 正確的桌子參數（重要！）
# ============================================================================
CORRECT_SLIDER_VALUES = {
    # 桌面尺寸
    "SLIDER_LENGTH": 120.0,      # 桌長
    "SLIDER_WIDTH": 80.0,        # 桌寬 (不是 120!)
    "SLIDER_TOP_HEIGHT": 5.0,    # 桌面厚度
    "SLIDER_TOP_Z": 70.0,        # 桌面高度

    # 桌腳尺寸
    "SLIDER_RADIUS_LEG": 3.0,    # 桌腳半徑
    "SLIDER_LEG_HEIGHT": 70.0,   # 桌腳高度

    # 桌腳 1 位置（右前）- 在桌子四個角落
    "SLIDER_LEG1_X": 55.0,       # 半長 - 5 = 55
    "SLIDER_LEG1_Y": 35.0,       # 半寬 - 5 = 35
    "SLIDER_LEG1_Z": 0.0,

    # 桌腳 2 位置（左前）
    "SLIDER_LEG2_X": -55.0,
    "SLIDER_LEG2_Y": 35.0,
    "SLIDER_LEG2_Z": 0.0,

    # 桌腳 3 位置（左後）
    "SLIDER_LEG3_X": -55.0,
    "SLIDER_LEG3_Y": -35.0,
    "SLIDER_LEG3_Z": 0.0,

    # 桌腳 4 位置（右後）
    "SLIDER_LEG4_X": 55.0,
    "SLIDER_LEG4_Y": -35.0,
    "SLIDER_LEG4_Z": 0.0,
}


def load_placement_info(path: str) -> dict:
    """讀取 placement_info.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_slider_values(placement_info: dict) -> dict:
    """更新 slider 數值到正確值"""
    commands = placement_info.get("commands", [])

    for cmd in commands:
        if cmd.get("type") == "add_component":
            comp_id = cmd.get("componentId", "")
            if comp_id in CORRECT_SLIDER_VALUES:
                old_value = cmd.get("value")
                new_value = CORRECT_SLIDER_VALUES[comp_id]
                cmd["value"] = new_value
                print(f"  {comp_id}: {old_value} -> {new_value}")

    return placement_info


def execute_add_commands(client: GrasshopperClient, commands: list[dict]) -> dict:
    """執行 add_component 命令（串行，確保穩定）"""
    results = {
        "success": 0,
        "fail": 0,
        "id_map": {}
    }

    total = len(commands)
    print(f"\n創建 {total} 個組件...")

    for index, cmd in enumerate(commands, 1):
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
            if actual_id:
                results["success"] += 1
                results["id_map"][comp_id] = actual_id
                val_str = f" = {value}" if value is not None else ""
                print(f"  ✓ [{index}/{total}] {comp_type}{val_str}")
            else:
                results["fail"] += 1
                print(f"  ✗ [{index}/{total}] {comp_type}: 無法提取 ID")
        else:
            error = response.get("error", "Unknown")
            results["fail"] += 1
            print(f"  ✗ [{index}/{total}] {comp_type}: {error[:50]}")

        # 小延遲確保穩定
        time.sleep(0.02)

    return results


def execute_connect_commands(client: GrasshopperClient, commands: list[dict], id_map: dict) -> dict:
    """執行 connect_components 命令"""
    results = {
        "success": 0,
        "fail": 0,
        "skipped": 0
    }

    total = len(commands)
    print(f"\n連接 {total} 對組件...")

    for index, cmd in enumerate(commands, 1):
        params = cmd.get("parameters", {})
        source_key = params.get("sourceId")
        target_key = params.get("targetId")

        # 從 ID 映射獲取實際 ID
        source_id = id_map.get(source_key)
        target_id = id_map.get(target_key)

        if not source_id:
            results["skipped"] += 1
            continue

        if not target_id:
            results["skipped"] += 1
            continue

        connect_params = {
            "sourceId": source_id,
            "targetId": target_id
        }

        # 傳遞參數名
        source_param = params.get("sourceParam")
        target_param = params.get("targetParam")

        if source_param:
            connect_params["sourceParam"] = source_param
        if target_param:
            connect_params["targetParam"] = target_param

        response = client.send_command("connect_components", connect_params)

        # 檢查成功
        inner_response = response.get("data", {})
        success = response.get("success", False)
        inner_success = inner_response.get("success", False) if isinstance(inner_response, dict) else False

        if success and inner_success:
            results["success"] += 1
        elif "already connected" in str(inner_response).lower():
            results["success"] += 1  # 已連接也算成功
        else:
            error = inner_response.get("error", "") if isinstance(inner_response, dict) else str(inner_response)
            if len(error) > 0:
                print(f"  ✗ [{index}] {source_key} -> {target_key}: {error[:40]}")
            results["fail"] += 1

        time.sleep(0.02)

    return results


def main():
    print("=" * 70)
    print("重建桌子（優化版）")
    print("=" * 70)
    print("策略: clear_document + add_component(value=...) + connect")
    print("=" * 70)

    # 路徑
    placement_path = Path("GH_WIP/placement_info.json")

    if not placement_path.exists():
        print(f"✗ 找不到 {placement_path}")
        return

    # 連接檢查
    client = GrasshopperClient()
    response = client.send_command("get_document_info")

    if not response.get("success"):
        print(f"\n✗ 無法連接到 Grasshopper MCP: {response.get('error')}")
        return

    print("✓ Grasshopper 已連接")

    # 載入並更新 placement_info
    print("\n" + "-" * 70)
    print("更新 slider 數值")
    print("-" * 70)

    placement_info = load_placement_info(str(placement_path))
    placement_info = update_slider_values(placement_info)

    commands = placement_info.get("commands", [])
    add_commands = [c for c in commands if c["type"] == "add_component"]
    connect_commands = [c for c in commands if c["type"] == "connect_components"]

    print(f"\nadd_component: {len(add_commands)} 個")
    print(f"connect_components: {len(connect_commands)} 個")

    # 確認
    print("\n" + "-" * 70)
    print("⚠️  警告：即將清除 Grasshopper 文檔並重建！")
    print("-" * 70)
    user_input = input("輸入 'y' 繼續: ").strip().lower()

    if user_input != 'y':
        print("已取消")
        return

    start_time = time.time()

    # 階段 0: 清除文檔
    print("\n" + "=" * 70)
    print("階段 0: 清除文檔")
    print("=" * 70)

    response = client.send_command("clear_document")
    if response.get("success"):
        print("✓ 文檔已清除")
    else:
        print(f"⚠️  清除失敗: {response.get('error')}")
        print("繼續執行...")

    time.sleep(0.5)  # 等待清除完成

    # 階段 1: 創建組件
    print("\n" + "=" * 70)
    print("階段 1: 創建組件（含正確 slider 值）")
    print("=" * 70)

    add_results = execute_add_commands(client, add_commands)
    print(f"\n組件創建: {add_results['success']}/{len(add_commands)} 成功")

    # 階段 2: 連接組件
    print("\n" + "=" * 70)
    print("階段 2: 連接組件")
    print("=" * 70)

    connect_results = execute_connect_commands(client, connect_commands, add_results["id_map"])
    print(f"\n組件連接: {connect_results['success']}/{len(connect_commands)} 成功")

    if connect_results["skipped"] > 0:
        print(f"  跳過: {connect_results['skipped']} 個（組件不存在）")

    # 總結
    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("執行總結")
    print("=" * 70)
    print(f"組件創建: {add_results['success']}/{len(add_commands)}")
    print(f"組件連接: {connect_results['success']}/{len(connect_commands)}")
    print(f"總耗時: {total_time:.2f} 秒")

    # 保存新的 ID 映射
    id_map_path = Path("GH_WIP/component_id_map.json")
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(add_results["id_map"], f, indent=2, ensure_ascii=False)
    print(f"\nID 映射已保存: {id_map_path}")

    # 保存更新後的 placement_info
    placement_v2_path = Path("GH_WIP/placement_info_v2.json")
    with open(placement_v2_path, "w", encoding="utf-8") as f:
        json.dump(placement_info, f, indent=2, ensure_ascii=False)
    print(f"更新後的 placement_info: {placement_v2_path}")

    success = add_results["fail"] == 0 and connect_results["fail"] < 10
    if success:
        print("\n🎉 桌子重建完成！請在 Grasshopper/Rhino 中查看結果。")
    else:
        print("\n⚠️  部分操作失敗，請檢查 Grasshopper 中的狀態。")


if __name__ == "__main__":
    main()
