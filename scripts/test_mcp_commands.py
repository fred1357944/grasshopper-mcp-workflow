#!/usr/bin/env python3
"""
測試 MCP 支援的命令

檢查當前 MCP Server 支援哪些命令。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient


def test_command(client, command_type, params=None):
    """測試命令是否支援"""
    response = client.send_command(command_type, params or {})
    success = response.get("success", False)
    error = response.get("error", "")
    data = response.get("data", {})

    if "No handler registered" in str(error) or "No handler registered" in str(data):
        return "NOT_SUPPORTED", error or str(data)
    elif success:
        return "SUPPORTED", data
    else:
        return "ERROR", error or str(data)


def main():
    print("=" * 70)
    print("MCP 命令支援測試")
    print("=" * 70)

    client = GrasshopperClient()

    # 測試連接
    response = client.send_command("get_document_info")
    if not response.get("success"):
        print(f"✗ 無法連接到 Grasshopper MCP: {response.get('error')}")
        return

    print("✓ Grasshopper 已連接\n")

    # 測試命令列表
    commands_to_test = [
        ("get_document_info", {}),
        ("add_component", {"type": "Number Slider", "x": 0, "y": 0}),
        ("connect_components", {"sourceId": "test", "targetId": "test"}),
        ("set_slider_value", {"componentId": "test", "value": 1.0}),
        ("batch_set_sliders", {"sliderValues": {}}),
        ("delete_component", {"componentId": "test"}),
        ("update_component", {"componentId": "test"}),
        ("get_component_details", {"componentId": "test"}),
        ("find_components_by_type", {"componentType": "slider"}),
        ("clear_document", {}),
        ("save_document", {"path": "/tmp/test.gh"}),
        ("load_document", {"path": "/tmp/test.gh"}),
        ("export_graph", {}),
        ("get_all_connections", {}),
    ]

    supported = []
    not_supported = []

    print("命令支援狀態:")
    print("-" * 70)

    for cmd_name, params in commands_to_test:
        status, result = test_command(client, cmd_name, params)

        if status == "SUPPORTED":
            supported.append(cmd_name)
            print(f"  ✓ {cmd_name}: 支援")
        elif status == "NOT_SUPPORTED":
            not_supported.append(cmd_name)
            print(f"  ✗ {cmd_name}: 不支援")
        else:
            # Could be error due to invalid params, but command might still exist
            if "No handler" in str(result):
                not_supported.append(cmd_name)
                print(f"  ✗ {cmd_name}: 不支援")
            else:
                supported.append(cmd_name)
                print(f"  ? {cmd_name}: 可能支援 (錯誤: {str(result)[:40]})")

    print("\n" + "=" * 70)
    print(f"總結: {len(supported)} 個支援, {len(not_supported)} 個不支援")
    print("=" * 70)

    print(f"\n支援的命令: {', '.join(supported)}")
    print(f"不支援的命令: {', '.join(not_supported)}")

    # 測試 add_component 的 value 參數
    print("\n" + "-" * 70)
    print("測試 add_component 是否支援 value 參數")
    print("-" * 70)

    response = client.send_command("add_component", {
        "type": "Number Slider",
        "x": 1000,
        "y": 1000,
        "value": 99.0
    })

    if response.get("success"):
        data = response.get("data", {})
        comp_id = data.get("id") if isinstance(data, dict) else None
        print(f"✓ 創建成功: ID = {comp_id}")
        print("  請在 Grasshopper 中檢查新 slider 的值是否為 99.0")

        # 如果支援 delete_component，清理測試組件
        if "delete_component" in supported:
            delete_response = client.send_command("delete_component", {"componentId": comp_id})
            if delete_response.get("success"):
                print("  ✓ 已刪除測試組件")
    else:
        print(f"✗ 創建失敗: {response.get('error', response.get('data'))}")


if __name__ == "__main__":
    main()
