#!/usr/bin/env python3
"""
簡單測試腳本 - 使用正確的組件名稱

目標: 創建一個簡單的 Box 並預覽
組件:
- Number Slider x3 (Width, Depth, Height)
- Center Box
- Custom Preview
"""

import sys
import time
sys.path.insert(0, '/Users/laihongyi/Downloads/grasshopper-mcp-workflow')

from grasshopper_mcp.layout import MCPLayoutExecutor


def main():
    print("=" * 60)
    print("       簡單 Box 測試 - 使用正確組件名稱")
    print("=" * 60)

    executor = MCPLayoutExecutor()

    # 1. 檢查 Canvas 狀態
    print("\n[1/5] 檢查 Canvas 狀態...")
    status = executor.check_canvas_status()

    if not status.get('success'):
        print(f"  ✗ MCP 連接失敗: {status.get('error')}")
        return

    if not status.get('is_empty'):
        count = status['component_count']
        print(f"  ⚠ Canvas 上已有 {count} 個組件")
        print("\n  選擇操作:")
        print("    1. 清空 Canvas")
        print("    2. 在右側創建")
        print("    3. 取消")

        choice = input("\n  請選擇 (1/2/3): ").strip()
        if choice == '1':
            executor.clear_canvas()
            print("  ✓ Canvas 已清空")
        elif choice == '2':
            executor.set_offset_from_existing(margin=200)
        else:
            print("  已取消")
            return
    else:
        print("  ✓ Canvas 為空")

    # 2. 定義組件 (使用正確的組件類型名稱)
    print("\n[2/5] 定義組件...")

    # Sliders
    executor.define_component("WIDTH", "Number Slider", width=200, height=20)
    executor.define_component("DEPTH", "Number Slider", width=200, height=20)
    executor.define_component("HEIGHT", "Number Slider", width=200, height=20)

    # Box 和 Preview
    executor.define_component("BOX", "Center Box", width=100, height=50)
    executor.define_component("PREVIEW", "Custom Preview", width=100, height=50)

    # 連線
    executor.define_connection("WIDTH", "V", "BOX", "X")
    executor.define_connection("DEPTH", "V", "BOX", "Y")
    executor.define_connection("HEIGHT", "V", "BOX", "Z")
    executor.define_connection("BOX", "B", "PREVIEW", "G")

    # 3. 計算佈局
    print("\n[3/5] 計算佈局...")
    positions = executor.calculate_layout()
    print(executor.layout_calc.get_layout_summary())

    # 4. 創建組件
    print("\n[4/5] 創建組件...")
    components_to_create = [
        ("WIDTH", "Number Slider"),
        ("DEPTH", "Number Slider"),
        ("HEIGHT", "Number Slider"),
        ("BOX", "Center Box"),
        ("PREVIEW", "Custom Preview"),
    ]

    created_count = 0
    for name, type_name in components_to_create:
        if executor.create_component(name, type_name):
            created_count += 1
        time.sleep(0.1)

    print(f"\n  創建了 {created_count}/{len(components_to_create)} 個組件")

    # 5. 創建連線
    print("\n[5/5] 創建連線...")
    connections = [
        ("WIDTH", "V", "BOX", "X"),
        ("DEPTH", "V", "BOX", "Y"),
        ("HEIGHT", "V", "BOX", "Z"),
        ("BOX", "B", "PREVIEW", "G"),
    ]

    connected_count = 0
    for from_n, from_p, to_n, to_p in connections:
        if executor.create_connection(from_n, from_p, to_n, to_p):
            connected_count += 1
        time.sleep(0.05)

    print(f"\n  創建了 {connected_count}/{len(connections)} 條連線")

    # 設置 Slider
    print("\n設置 Slider 值...")
    executor.set_slider("WIDTH", 10, 200, 100)
    executor.set_slider("DEPTH", 10, 200, 60)
    executor.set_slider("HEIGHT", 10, 200, 75)

    # 縮放視圖
    executor.zoom_to_all()

    print("\n" + "=" * 60)
    print("  ✓ 測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
