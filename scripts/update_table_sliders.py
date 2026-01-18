#!/usr/bin/env python3
"""
更新桌子 Slider 數值

使用 MCP set_slider_value 命令更新所有滑桿到正確的桌子比例。

使用方式:
    python scripts/update_table_sliders.py

前置條件:
    1. Grasshopper 已開啟且增強版 MCP Server 運行在 port 8080
    2. GH_WIP/component_id_map.json 已存在（包含 slider GUID）
"""

import sys
import json
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient


# 目標數值（正確的桌子比例）
TABLE_SLIDER_VALUES = {
    # 桌面尺寸
    "SLIDER_LENGTH": 120.0,      # 桌長
    "SLIDER_WIDTH": 80.0,        # 桌寬
    "SLIDER_TOP_HEIGHT": 5.0,    # 桌面厚度
    "SLIDER_TOP_Z": 70.0,        # 桌面高度

    # 桌腳尺寸
    "SLIDER_RADIUS_LEG": 3.0,    # 桌腳半徑
    "SLIDER_LEG_HEIGHT": 70.0,   # 桌腳高度

    # 桌腳 1 位置（右前）
    "SLIDER_LEG1_X": 55.0,
    "SLIDER_LEG1_Y": 35.0,
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


def load_id_map(path: str) -> dict:
    """讀取 component_id_map.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_set_slider_value(client: GrasshopperClient, component_id: str, value: float) -> dict:
    """測試 set_slider_value 命令"""
    params = {
        "componentId": component_id,
        "value": value
    }
    return client.send_command("set_slider_value", params)


def batch_set_sliders(client: GrasshopperClient, slider_values: dict) -> dict:
    """批次設定 slider 數值"""
    params = {
        "sliderValues": slider_values
    }
    return client.send_command("batch_set_sliders", params)


def main():
    print("=" * 70)
    print("更新桌子 Slider 數值")
    print("=" * 70)

    # 載入 ID 映射
    id_map_path = Path("GH_WIP/component_id_map.json")
    if not id_map_path.exists():
        print(f"✗ 找不到 {id_map_path}")
        print("請先運行: python scripts/execute_table.py")
        return

    id_map = load_id_map(str(id_map_path))
    print(f"✓ 載入 {len(id_map)} 個組件 ID")

    # 連接檢查
    client = GrasshopperClient()
    response = client.send_command("get_document_info")

    if not response.get("success"):
        print(f"\n✗ 無法連接到 Grasshopper MCP: {response.get('error')}")
        return

    print("✓ Grasshopper 已連接")

    # 準備 slider GUID -> value 映射
    slider_updates = {}
    missing_sliders = []

    for slider_name, target_value in TABLE_SLIDER_VALUES.items():
        guid = id_map.get(slider_name)
        if guid:
            slider_updates[guid] = target_value
            print(f"  {slider_name}: {target_value}")
        else:
            missing_sliders.append(slider_name)
            print(f"  ⚠️  {slider_name}: 找不到 GUID")

    if missing_sliders:
        print(f"\n⚠️  有 {len(missing_sliders)} 個 slider 找不到 GUID")

    print(f"\n準備更新 {len(slider_updates)} 個 sliders")

    # 方法 1: 嘗試 batch_set_sliders（效率高）
    print("\n" + "-" * 70)
    print("嘗試方法 1: batch_set_sliders")
    print("-" * 70)

    response = batch_set_sliders(client, slider_updates)

    if response.get("success"):
        data = response.get("data", {})
        if isinstance(data, dict) and data.get("success"):
            print("✓ batch_set_sliders 成功！")
            print(f"  更新了 {data.get('updated', 0)} 個 sliders")
            return

    data = response.get("data")
    if data is None:
        error = response.get("error", "Unknown command or not supported")
    elif isinstance(data, dict):
        error = data.get("error", "Unknown")
    else:
        error = str(data)
    print(f"✗ batch_set_sliders 失敗: {error}")

    # 方法 2: 逐一使用 set_slider_value
    print("\n" + "-" * 70)
    print("嘗試方法 2: 逐一 set_slider_value")
    print("-" * 70)

    success_count = 0
    fail_count = 0

    for slider_name, target_value in TABLE_SLIDER_VALUES.items():
        guid = id_map.get(slider_name)
        if not guid:
            continue

        response = test_set_slider_value(client, guid, target_value)

        # 檢查成功
        success = response.get("success", False)
        inner_data = response.get("data", {})
        inner_success = inner_data.get("success", False) if isinstance(inner_data, dict) else False

        if success and inner_success:
            print(f"  ✓ {slider_name} = {target_value}")
            success_count += 1
        else:
            error = inner_data.get("error", "") if isinstance(inner_data, dict) else response.get("error", "Unknown")
            print(f"  ✗ {slider_name}: {error[:50]}")
            fail_count += 1

    print(f"\n更新完成: {success_count} 成功, {fail_count} 失敗")

    if fail_count > 0:
        print("\n" + "=" * 70)
        print("⚠️  set_slider_value 不支援！")
        print("=" * 70)
        print("可能原因:")
        print("  1. 當前 MCP Server 是基礎版，不支援 set_slider_value")
        print("  2. 需要安裝增強版 MCP Server（含 C# Handler）")
        print("")
        print("解決方案:")
        print("  1. 查看 grasshopper-mcp-enhanced/ 目錄的 C# 代碼")
        print("  2. 將 ComponentCommandHandler_Enhanced.cs 整合到 Grasshopper 插件")
        print("  3. 或者手動在 Grasshopper 中調整 slider 數值")


if __name__ == "__main__":
    main()
