#!/usr/bin/env python3
"""
桌子設計腳本 - 使用自動佈局

特點:
- 自動計算組件位置（從左到右，按數據流排列）
- 清晰的層級結構
- 支持 Slider 配置
"""

import sys
import time
sys.path.insert(0, '/Users/laihongyi/Downloads/grasshopper-mcp-workflow')

from grasshopper_mcp.layout import MCPLayoutExecutor, LayoutConfig


def create_award_table_executor() -> MCPLayoutExecutor:
    """
    創建獲獎級桌子設計

    設計概念: "懸浮張力桌 (Tensegrity Table)"
    - 桌面看起來像懸浮在空中
    - 使用單一斜腿支撐
    - 張力線維持平衡
    """
    executor = MCPLayoutExecutor()

    # 使用更大的間距
    executor.layout_calc.config.horizontal_spacing = 220
    executor.layout_calc.config.vertical_spacing = 70

    # ========== 定義組件 ==========

    # --- 輸入參數層 ---
    executor.define_component("TABLE_WIDTH", "Number Slider", width=200, height=22)
    executor.define_component("TABLE_DEPTH", "Number Slider", width=200, height=22)
    executor.define_component("TABLE_THICK", "Number Slider", width=200, height=22)
    executor.define_component("LEG_SIZE", "Number Slider", width=200, height=22)
    executor.define_component("LEG_HEIGHT", "Number Slider", width=200, height=22)
    executor.define_component("LEG_ANGLE", "Number Slider", width=200, height=22)

    # --- 參考平面和點 ---
    executor.define_component("XY_PLANE", "XY Plane", width=80, height=40)
    executor.define_component("ORIGIN", "Construct Point", width=100, height=50)
    executor.define_component("LEG_CENTER", "Construct Point", width=100, height=50)

    # --- 桌面幾何 ---
    executor.define_component("TABLE_RECT", "Rectangle", width=100, height=60)
    executor.define_component("TABLE_SURFACE", "Extrude", width=100, height=50)

    # --- 桌腳幾何 ---
    executor.define_component("LEG_CIRCLE", "Circle", width=100, height=50)
    executor.define_component("LEG_EXTRUDE", "Extrude", width=100, height=50)

    # --- 變形操作 ---
    executor.define_component("UNIT_Z", "Unit Z", width=80, height=40)
    executor.define_component("LEG_VECTOR", "Amplitude", width=100, height=50)
    executor.define_component("MOVE_TABLE", "Move", width=100, height=50)

    # --- 輸出 ---
    executor.define_component("MERGE_GEO", "Merge", width=100, height=50)
    executor.define_component("PREVIEW", "Custom Preview", width=100, height=50)

    # ========== 定義連線 ==========

    # 桌面
    executor.define_connection("XY_PLANE", "Plane", "TABLE_RECT", "Plane")
    executor.define_connection("TABLE_WIDTH", "Number", "TABLE_RECT", "X")
    executor.define_connection("TABLE_DEPTH", "Number", "TABLE_RECT", "Y")
    executor.define_connection("TABLE_RECT", "Rectangle", "TABLE_SURFACE", "Base")
    executor.define_connection("TABLE_THICK", "Number", "TABLE_SURFACE", "Direction")

    # 移動桌面到桌腳高度
    executor.define_connection("UNIT_Z", "Unit vector", "LEG_VECTOR", "Base")
    executor.define_connection("LEG_HEIGHT", "Number", "LEG_VECTOR", "Amplitude")
    executor.define_connection("TABLE_SURFACE", "Extrusion", "MOVE_TABLE", "Geometry")
    executor.define_connection("LEG_VECTOR", "Vector", "MOVE_TABLE", "Motion")

    # 桌腳
    executor.define_connection("LEG_CENTER", "Point", "LEG_CIRCLE", "Base")
    executor.define_connection("LEG_SIZE", "Number", "LEG_CIRCLE", "Radius")
    executor.define_connection("LEG_CIRCLE", "Circle", "LEG_EXTRUDE", "Base")
    executor.define_connection("LEG_HEIGHT", "Number", "LEG_EXTRUDE", "Direction")

    # 合併
    executor.define_connection("MOVE_TABLE", "Geometry", "MERGE_GEO", "Data 1")
    executor.define_connection("LEG_EXTRUDE", "Extrusion", "MERGE_GEO", "Data 2")

    # 預覽
    executor.define_connection("MERGE_GEO", "Result", "PREVIEW", "Geometry")

    return executor


def main():
    print("=" * 60)
    print("       桌子設計腳本 - 使用自動佈局")
    print("=" * 60)

    # 創建執行器
    executor = create_award_table_executor()

    # 1. 檢查 MCP 連接和 Canvas 狀態
    print("\n[1/6] 檢查 Canvas 狀態...")
    status = executor.check_canvas_status()

    if not status.get('success'):
        print(f"  ✗ MCP 連接失敗: {status.get('error')}")
        print("\n  請確保:")
        print("  1. Rhino 正在運行")
        print("  2. Grasshopper 已開啟")
        print("  3. GH_MCP 插件已載入")
        return

    # 2. 處理現有組件
    if not status.get('is_empty'):
        count = status['component_count']
        bounds = status['bounds']
        print(f"  ⚠ Canvas 上已有 {count} 個組件")
        print(f"    範圍: X({bounds['min_x']:.0f} ~ {bounds['max_x']:.0f}), "
              f"Y({bounds['min_y']:.0f} ~ {bounds['max_y']:.0f})")

        print("\n  選擇操作:")
        print("    1. 清空 Canvas 重新開始")
        print("    2. 在現有組件右側創建")
        print("    3. 取消")

        choice = input("\n  請選擇 (1/2/3): ").strip()

        if choice == '1':
            print("\n  正在清空 Canvas...")
            if executor.clear_canvas():
                print("  ✓ Canvas 已清空")
            else:
                print("  ⚠ 清空失敗，將在右側創建")
                executor.set_offset_from_existing(margin=200)
        elif choice == '2':
            executor.set_offset_from_existing(margin=200)
            print(f"  ✓ 將在 X={executor.canvas_offset_x:.0f} 處創建新組件")
        else:
            print("  已取消")
            return
    else:
        print("  ✓ Canvas 為空，可以開始創建")

    # 3. 計算佈局
    print("\n[2/6] 計算佈局...")
    positions = executor.calculate_layout()
    print(executor.layout_calc.get_layout_summary())

    # 4. 創建組件
    print("\n[3/6] 創建組件...")
    components_to_create = [
        # 輸入參數
        ("TABLE_WIDTH", "Number Slider"),
        ("TABLE_DEPTH", "Number Slider"),
        ("TABLE_THICK", "Number Slider"),
        ("LEG_SIZE", "Number Slider"),
        ("LEG_HEIGHT", "Number Slider"),
        ("LEG_ANGLE", "Number Slider"),
        # 平面和點
        ("XY_PLANE", "XY Plane"),
        ("ORIGIN", "Construct Point"),
        ("LEG_CENTER", "Construct Point"),
        # 桌面
        ("TABLE_RECT", "Rectangle"),
        ("TABLE_SURFACE", "Extrude"),
        # 桌腳
        ("LEG_CIRCLE", "Circle"),
        ("LEG_EXTRUDE", "Extrude"),
        # 變形
        ("UNIT_Z", "Unit Z"),
        ("LEG_VECTOR", "Amplitude"),
        ("MOVE_TABLE", "Move"),
        # 輸出
        ("MERGE_GEO", "Merge"),
        ("PREVIEW", "Custom Preview"),
    ]

    created_count = 0
    for name, type_name in components_to_create:
        if executor.create_component(name, type_name):
            created_count += 1
        time.sleep(0.1)  # 避免請求過快

    print(f"\n  創建了 {created_count}/{len(components_to_create)} 個組件")

    # 5. 創建連線
    print("\n[4/6] 創建連線...")
    connections_to_make = [
        # 桌面
        ("XY_PLANE", "Plane", "TABLE_RECT", "P"),
        ("TABLE_WIDTH", "Number", "TABLE_RECT", "X"),
        ("TABLE_DEPTH", "Number", "TABLE_RECT", "Y"),
        ("TABLE_RECT", "Rectangle", "TABLE_SURFACE", "B"),
        ("TABLE_THICK", "Number", "TABLE_SURFACE", "H"),
        # 移動
        ("UNIT_Z", "V", "LEG_VECTOR", "V"),
        ("LEG_HEIGHT", "Number", "LEG_VECTOR", "A"),
        ("TABLE_SURFACE", "E", "MOVE_TABLE", "G"),
        ("LEG_VECTOR", "V", "MOVE_TABLE", "T"),
        # 桌腳
        ("LEG_CENTER", "Pt", "LEG_CIRCLE", "P"),
        ("LEG_SIZE", "Number", "LEG_CIRCLE", "R"),
        ("LEG_CIRCLE", "C", "LEG_EXTRUDE", "B"),
        ("LEG_HEIGHT", "Number", "LEG_EXTRUDE", "H"),
        # 合併
        ("MOVE_TABLE", "G", "MERGE_GEO", "D1"),
        ("LEG_EXTRUDE", "E", "MERGE_GEO", "D2"),
        # 預覽
        ("MERGE_GEO", "R", "PREVIEW", "G"),
    ]

    connected_count = 0
    for from_n, from_p, to_n, to_p in connections_to_make:
        if executor.create_connection(from_n, from_p, to_n, to_p):
            connected_count += 1
        time.sleep(0.05)

    print(f"\n  創建了 {connected_count}/{len(connections_to_make)} 條連線")

    # 6. 設置 Slider 值
    print("\n[5/6] 設置 Slider 值...")
    slider_configs = [
        ("TABLE_WIDTH", 60, 200, 120),
        ("TABLE_DEPTH", 40, 150, 80),
        ("TABLE_THICK", 2, 10, 5),
        ("LEG_SIZE", 5, 30, 15),
        ("LEG_HEIGHT", 30, 100, 70),
        ("LEG_ANGLE", 0, 45, 15),
    ]

    for name, min_v, max_v, default_v in slider_configs:
        executor.set_slider(name, min_v, max_v, default_v)

    # 7. 縮放視圖
    print("\n[6/6] 調整視圖...")
    executor.zoom_to_all()

    print("\n" + "=" * 60)
    print("  ✓ 桌子設計創建完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
