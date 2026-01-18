#!/usr/bin/env python3
"""
簡單桌子設計 - 使用 Center Box

設計結構:
- 桌面: Center Box (寬 x 深 x 厚)
- 桌腳: Center Box (腳寬 x 腳寬 x 高), Move 移動到 Z=腳高/2
- 合併後預覽

組件流程:
  Sliders → Center Box (桌面) → Move (移到桌腳高度上) → Merge → Preview
          → Center Box (桌腳) →                       ↗
"""

import sys
import time
sys.path.insert(0, '/Users/laihongyi/Downloads/grasshopper-mcp-workflow')

from grasshopper_mcp.layout import MCPLayoutExecutor


def main():
    print("=" * 60)
    print("       簡單桌子設計 - Center Box 方案")
    print("=" * 60)

    executor = MCPLayoutExecutor()
    executor.layout_calc.config.horizontal_spacing = 200
    executor.layout_calc.config.vertical_spacing = 80

    # 1. 檢查 Canvas
    print("\n[1/6] 檢查 Canvas...")
    status = executor.check_canvas_status()

    if not status.get('success'):
        print(f"  ✗ MCP 連接失敗: {status.get('error')}")
        return

    if not status.get('is_empty'):
        count = status['component_count']
        print(f"  ⚠ Canvas 上已有 {count} 個組件")
        choice = input("  清空 Canvas? (y/n): ").strip().lower()
        if choice == 'y':
            executor.clear_canvas()
            print("  ✓ Canvas 已清空")
        else:
            executor.set_offset_from_existing(margin=200)
    else:
        print("  ✓ Canvas 為空")

    # 2. 定義組件
    print("\n[2/6] 定義組件...")

    # === 輸入參數 (Sliders) ===
    executor.define_component("TABLE_W", "Number Slider", width=200, height=20)
    executor.define_component("TABLE_D", "Number Slider", width=200, height=20)
    executor.define_component("TABLE_T", "Number Slider", width=200, height=20)  # 厚度
    executor.define_component("LEG_SIZE", "Number Slider", width=200, height=20)
    executor.define_component("LEG_H", "Number Slider", width=200, height=20)

    # === 桌面 ===
    executor.define_component("TABLE_BOX", "Center Box", width=100, height=50)

    # === 桌腳 ===
    executor.define_component("LEG_BOX", "Center Box", width=100, height=50)

    # === 向量 (用於移動桌面到正確高度) ===
    executor.define_component("UNIT_Z", "Unit Z", width=80, height=40)
    executor.define_component("TABLE_LIFT", "Amplitude", width=100, height=50)
    executor.define_component("MOVE_TABLE", "Move", width=100, height=50)

    # === 合併和預覽 ===
    executor.define_component("MERGE", "Merge", width=100, height=50)
    executor.define_component("PREVIEW", "Custom Preview", width=100, height=50)

    # === 連線定義 ===
    # 桌面 Box
    executor.define_connection("TABLE_W", "V", "TABLE_BOX", "X")
    executor.define_connection("TABLE_D", "V", "TABLE_BOX", "Y")
    executor.define_connection("TABLE_T", "V", "TABLE_BOX", "Z")

    # 桌腳 Box
    executor.define_connection("LEG_SIZE", "V", "LEG_BOX", "X")
    executor.define_connection("LEG_SIZE", "V", "LEG_BOX", "Y")
    executor.define_connection("LEG_H", "V", "LEG_BOX", "Z")

    # 移動桌面到桌腳高度
    # 移動向量 = Unit Z * (LEG_H + TABLE_T/2)
    # 簡化: 移動向量 = Unit Z * LEG_H
    executor.define_connection("UNIT_Z", "V", "TABLE_LIFT", "V")
    executor.define_connection("LEG_H", "V", "TABLE_LIFT", "A")
    executor.define_connection("TABLE_BOX", "B", "MOVE_TABLE", "G")
    executor.define_connection("TABLE_LIFT", "V", "MOVE_TABLE", "T")

    # 合併
    executor.define_connection("MOVE_TABLE", "G", "MERGE", "D1")
    executor.define_connection("LEG_BOX", "B", "MERGE", "D2")

    # 預覽
    executor.define_connection("MERGE", "R", "PREVIEW", "G")

    # 3. 計算佈局
    print("\n[3/6] 計算佈局...")
    positions = executor.calculate_layout()
    print(executor.layout_calc.get_layout_summary())

    # 4. 創建組件
    print("\n[4/6] 創建組件...")
    components = [
        # Sliders
        ("TABLE_W", "Number Slider"),
        ("TABLE_D", "Number Slider"),
        ("TABLE_T", "Number Slider"),
        ("LEG_SIZE", "Number Slider"),
        ("LEG_H", "Number Slider"),
        # Boxes
        ("TABLE_BOX", "Center Box"),
        ("LEG_BOX", "Center Box"),
        # Vector
        ("UNIT_Z", "Unit Z"),
        ("TABLE_LIFT", "Amplitude"),
        ("MOVE_TABLE", "Move"),
        # Output
        ("MERGE", "Merge"),
        ("PREVIEW", "Custom Preview"),
    ]

    created = 0
    for name, type_name in components:
        if executor.create_component(name, type_name):
            created += 1
        time.sleep(0.1)

    print(f"\n  創建了 {created}/{len(components)} 個組件")

    # 5. 創建連線
    print("\n[5/6] 創建連線...")
    connections = [
        # 桌面
        ("TABLE_W", "V", "TABLE_BOX", "X"),
        ("TABLE_D", "V", "TABLE_BOX", "Y"),
        ("TABLE_T", "V", "TABLE_BOX", "Z"),
        # 桌腳
        ("LEG_SIZE", "V", "LEG_BOX", "X"),
        ("LEG_SIZE", "V", "LEG_BOX", "Y"),
        ("LEG_H", "V", "LEG_BOX", "Z"),
        # 移動
        ("UNIT_Z", "V", "TABLE_LIFT", "V"),
        ("LEG_H", "V", "TABLE_LIFT", "A"),
        ("TABLE_BOX", "B", "MOVE_TABLE", "G"),
        ("TABLE_LIFT", "V", "MOVE_TABLE", "T"),
        # 合併
        ("MOVE_TABLE", "G", "MERGE", "D1"),
        ("LEG_BOX", "B", "MERGE", "D2"),
        # 預覽
        ("MERGE", "R", "PREVIEW", "G"),
    ]

    connected = 0
    for from_n, from_p, to_n, to_p in connections:
        if executor.create_connection(from_n, from_p, to_n, to_p):
            connected += 1
        time.sleep(0.05)

    print(f"\n  創建了 {connected}/{len(connections)} 條連線")

    # 6. 設置 Slider 值
    print("\n[6/6] 設置 Slider 值...")
    slider_configs = [
        ("TABLE_W", 50, 200, 120),   # 桌寬
        ("TABLE_D", 30, 150, 80),    # 桌深
        ("TABLE_T", 2, 10, 5),       # 桌面厚度
        ("LEG_SIZE", 5, 30, 10),     # 桌腳寬度
        ("LEG_H", 30, 100, 70),      # 桌腳高度
    ]

    for name, min_v, max_v, default_v in slider_configs:
        executor.set_slider(name, min_v, max_v, default_v)

    # 縮放視圖
    executor.zoom_to_all()

    print("\n" + "=" * 60)
    print("  ✓ 桌子設計創建完成！")
    print("  ")
    print("  設計說明:")
    print("    - 桌面: 120 x 80 x 5")
    print("    - 桌腳: 10 x 10 x 70")
    print("    - 桌面會自動移動到桌腳高度上方")
    print("=" * 60)


if __name__ == "__main__":
    main()
