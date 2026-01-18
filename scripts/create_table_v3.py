#!/usr/bin/env python3
"""
Simple Table v3 - 使用 Orient 複製桌腳 + MCPLayoutExecutor

設計來源: GH_WIP/component_info_v2.mmd

設計策略:
1. 基礎桌腳 (LEG_BASE): Center Box 在原點, Z中心在 LEG_H/2
2. 4個目標平面: 用 Construct Point + XY Plane 定義角落位置
3. Orient: 將基礎桌腳複製到 4 個角落
4. 桌面: Center Box 在桌腳高度上方
5. Merge 所有幾何體 → Custom Preview

組件清單 (來自 Mermaid):
- 輸入參數: LEG_SIZE, LEG_H, TABLE_W, TABLE_D, TABLE_T, CONST_2
- 桌腳位置: POS1_X/Y, POS2_X/Y, POS3_X/Y, POS4_X/Y
- 基礎桌腳: DIV_LEG_Z, PT_LEG_BASE, PLANE_LEG_BASE, BOX_LEG_BASE
- 目標平面: PT_LEG1-4, PLANE_LEG1-4
- Orient: ORIENT1-4
- 桌面: DIV_TABLE_Z, ADD_TABLE_Z, PT_TABLE, PLANE_TABLE, BOX_TABLE
- 輸出: MERGE1-4, PREVIEW
"""

import sys
import time
sys.path.insert(0, '/Users/laihongyi/Downloads/grasshopper-mcp-workflow')

from grasshopper_mcp.layout import MCPLayoutExecutor


def main():
    print("=" * 70)
    print("       Simple Table v3 - Orient 複製桌腳")
    print("       設計來源: GH_WIP/component_info_v2.mmd")
    print("=" * 70)

    executor = MCPLayoutExecutor()
    executor.layout_calc.config.horizontal_spacing = 200
    executor.layout_calc.config.vertical_spacing = 80

    # ========================================
    # 1. 檢查 Canvas
    # ========================================
    print("\n[1/7] 檢查 Canvas...")
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
            executor.set_offset_from_existing(margin=300)
    else:
        print("  ✓ Canvas 為空")

    # ========================================
    # 2. 定義組件 (依照 Mermaid 流程圖)
    # ========================================
    print("\n[2/7] 定義組件...")

    # === 輸入參數 Sliders ===
    executor.define_component("SLIDER_LEG_SIZE", "Number Slider", width=200, height=20)
    executor.define_component("SLIDER_LEG_H", "Number Slider", width=200, height=20)
    executor.define_component("SLIDER_TABLE_W", "Number Slider", width=200, height=20)
    executor.define_component("SLIDER_TABLE_D", "Number Slider", width=200, height=20)
    executor.define_component("SLIDER_TABLE_T", "Number Slider", width=200, height=20)
    executor.define_component("CONST_2", "Number Slider", width=200, height=20)

    # === 桌腳位置 Sliders ===
    executor.define_component("SLIDER_POS1_X", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS1_Y", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS2_X", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS2_Y", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS3_X", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS3_Y", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS4_X", "Number Slider", width=150, height=20)
    executor.define_component("SLIDER_POS4_Y", "Number Slider", width=150, height=20)

    # === 基礎桌腳 ===
    executor.define_component("DIV_LEG_Z", "Division", width=80, height=40)
    executor.define_component("PT_LEG_BASE", "Construct Point", width=100, height=50)
    executor.define_component("PLANE_LEG_BASE", "XY Plane", width=80, height=40)
    executor.define_component("BOX_LEG_BASE", "Center Box", width=100, height=50)

    # === 桌腳目標平面 ===
    executor.define_component("PT_LEG1", "Construct Point", width=100, height=50)
    executor.define_component("PT_LEG2", "Construct Point", width=100, height=50)
    executor.define_component("PT_LEG3", "Construct Point", width=100, height=50)
    executor.define_component("PT_LEG4", "Construct Point", width=100, height=50)
    executor.define_component("PLANE_LEG1", "XY Plane", width=80, height=40)
    executor.define_component("PLANE_LEG2", "XY Plane", width=80, height=40)
    executor.define_component("PLANE_LEG3", "XY Plane", width=80, height=40)
    executor.define_component("PLANE_LEG4", "XY Plane", width=80, height=40)

    # === Orient 複製 ===
    executor.define_component("ORIENT1", "Orient", width=100, height=50)
    executor.define_component("ORIENT2", "Orient", width=100, height=50)
    executor.define_component("ORIENT3", "Orient", width=100, height=50)
    executor.define_component("ORIENT4", "Orient", width=100, height=50)

    # === 桌面 ===
    executor.define_component("DIV_TABLE_Z", "Division", width=80, height=40)
    executor.define_component("ADD_TABLE_Z", "Addition", width=80, height=40)
    executor.define_component("PT_TABLE", "Construct Point", width=100, height=50)
    executor.define_component("PLANE_TABLE", "XY Plane", width=80, height=40)
    executor.define_component("BOX_TABLE", "Center Box", width=100, height=50)

    # === 合併輸出 ===
    executor.define_component("MERGE1", "Merge", width=80, height=50)
    executor.define_component("MERGE2", "Merge", width=80, height=50)
    executor.define_component("MERGE3", "Merge", width=80, height=50)
    executor.define_component("MERGE4", "Merge", width=80, height=50)
    executor.define_component("PREVIEW", "Custom Preview", width=100, height=50)

    # ========================================
    # 3. 定義連線 (依照 Mermaid 流程圖)
    # ========================================
    print("\n[3/7] 定義連線...")

    # --- 基礎桌腳 ---
    # 注意: 參數名需要匹配 Grasshopper 的實際名稱
    # Division: A, B → R
    # Construct Point: X coordinate, Y coordinate, Z coordinate → Point (或簡寫)
    # XY Plane: Origin → Plane
    # Center Box: Base, X, Y, Z → Box
    executor.define_connection("SLIDER_LEG_H", "V", "DIV_LEG_Z", "A")
    executor.define_connection("CONST_2", "V", "DIV_LEG_Z", "B")
    executor.define_connection("DIV_LEG_Z", "Result", "PT_LEG_BASE", "Z coordinate")
    executor.define_connection("PT_LEG_BASE", "Point", "PLANE_LEG_BASE", "O")
    executor.define_connection("PLANE_LEG_BASE", "Pl", "BOX_LEG_BASE", "Base")  # P→Pl, P→Base
    executor.define_connection("SLIDER_LEG_SIZE", "V", "BOX_LEG_BASE", "X")
    executor.define_connection("SLIDER_LEG_SIZE", "V", "BOX_LEG_BASE", "Y")
    executor.define_connection("SLIDER_LEG_H", "V", "BOX_LEG_BASE", "Z")

    # --- 桌腳目標平面 ---
    # Leg 1 (前右: +50, +30)
    executor.define_connection("SLIDER_POS1_X", "V", "PT_LEG1", "X coordinate")
    executor.define_connection("SLIDER_POS1_Y", "V", "PT_LEG1", "Y coordinate")
    executor.define_connection("DIV_LEG_Z", "Result", "PT_LEG1", "Z coordinate")
    executor.define_connection("PT_LEG1", "Point", "PLANE_LEG1", "O")

    # Leg 2 (前左: -50, +30)
    executor.define_connection("SLIDER_POS2_X", "V", "PT_LEG2", "X coordinate")
    executor.define_connection("SLIDER_POS2_Y", "V", "PT_LEG2", "Y coordinate")
    executor.define_connection("DIV_LEG_Z", "Result", "PT_LEG2", "Z coordinate")
    executor.define_connection("PT_LEG2", "Point", "PLANE_LEG2", "O")

    # Leg 3 (後左: -50, -30)
    executor.define_connection("SLIDER_POS3_X", "V", "PT_LEG3", "X coordinate")
    executor.define_connection("SLIDER_POS3_Y", "V", "PT_LEG3", "Y coordinate")
    executor.define_connection("DIV_LEG_Z", "Result", "PT_LEG3", "Z coordinate")
    executor.define_connection("PT_LEG3", "Point", "PLANE_LEG3", "O")

    # Leg 4 (後右: +50, -30)
    executor.define_connection("SLIDER_POS4_X", "V", "PT_LEG4", "X coordinate")
    executor.define_connection("SLIDER_POS4_Y", "V", "PT_LEG4", "Y coordinate")
    executor.define_connection("DIV_LEG_Z", "Result", "PT_LEG4", "Z coordinate")
    executor.define_connection("PT_LEG4", "Point", "PLANE_LEG4", "O")

    # --- Orient ---
    # Orient 參數: Geometry, Source, Target → Geometry, Transform
    executor.define_connection("BOX_LEG_BASE", "Box", "ORIENT1", "Geometry")
    executor.define_connection("BOX_LEG_BASE", "Box", "ORIENT2", "Geometry")
    executor.define_connection("BOX_LEG_BASE", "Box", "ORIENT3", "Geometry")
    executor.define_connection("BOX_LEG_BASE", "Box", "ORIENT4", "Geometry")

    executor.define_connection("PLANE_LEG_BASE", "Pl", "ORIENT1", "Source")
    executor.define_connection("PLANE_LEG_BASE", "Pl", "ORIENT2", "Source")
    executor.define_connection("PLANE_LEG_BASE", "Pl", "ORIENT3", "Source")
    executor.define_connection("PLANE_LEG_BASE", "Pl", "ORIENT4", "Source")

    executor.define_connection("PLANE_LEG1", "Pl", "ORIENT1", "Target")
    executor.define_connection("PLANE_LEG2", "Pl", "ORIENT2", "Target")
    executor.define_connection("PLANE_LEG3", "Pl", "ORIENT3", "Target")
    executor.define_connection("PLANE_LEG4", "Pl", "ORIENT4", "Target")

    # --- 桌面 ---
    executor.define_connection("SLIDER_TABLE_T", "V", "DIV_TABLE_Z", "A")
    executor.define_connection("CONST_2", "V", "DIV_TABLE_Z", "B")
    executor.define_connection("SLIDER_LEG_H", "V", "ADD_TABLE_Z", "A")
    executor.define_connection("DIV_TABLE_Z", "Result", "ADD_TABLE_Z", "B")
    executor.define_connection("ADD_TABLE_Z", "Result", "PT_TABLE", "Z coordinate")
    executor.define_connection("PT_TABLE", "Point", "PLANE_TABLE", "O")
    executor.define_connection("PLANE_TABLE", "Pl", "BOX_TABLE", "Base")  # P→Pl, P→Base
    executor.define_connection("SLIDER_TABLE_W", "V", "BOX_TABLE", "X")
    executor.define_connection("SLIDER_TABLE_D", "V", "BOX_TABLE", "Y")
    executor.define_connection("SLIDER_TABLE_T", "V", "BOX_TABLE", "Z")

    # --- 合併 ---
    # Merge: Data 1, Data 2, ... → Result (注意空格!)
    # Orient 輸出: Geometry
    # Center Box 輸出: Box
    executor.define_connection("BOX_TABLE", "Box", "MERGE1", "Data 1")
    executor.define_connection("ORIENT1", "Geometry", "MERGE1", "Data 2")
    executor.define_connection("MERGE1", "Result", "MERGE2", "Data 1")
    executor.define_connection("ORIENT2", "Geometry", "MERGE2", "Data 2")
    executor.define_connection("MERGE2", "Result", "MERGE3", "Data 1")
    executor.define_connection("ORIENT3", "Geometry", "MERGE3", "Data 2")
    executor.define_connection("MERGE3", "Result", "MERGE4", "Data 1")
    executor.define_connection("ORIENT4", "Geometry", "MERGE4", "Data 2")
    executor.define_connection("MERGE4", "Result", "PREVIEW", "Geometry")

    # ========================================
    # 4. 計算佈局
    # ========================================
    print("\n[4/7] 計算佈局...")
    positions = executor.calculate_layout()
    print(executor.layout_calc.get_layout_summary())

    # ========================================
    # 5. 創建組件
    # ========================================
    print("\n[5/7] 創建組件...")

    components_to_create = [
        # 輸入參數
        ("SLIDER_LEG_SIZE", "Number Slider"),
        ("SLIDER_LEG_H", "Number Slider"),
        ("SLIDER_TABLE_W", "Number Slider"),
        ("SLIDER_TABLE_D", "Number Slider"),
        ("SLIDER_TABLE_T", "Number Slider"),
        ("CONST_2", "Number Slider"),
        # 桌腳位置
        ("SLIDER_POS1_X", "Number Slider"),
        ("SLIDER_POS1_Y", "Number Slider"),
        ("SLIDER_POS2_X", "Number Slider"),
        ("SLIDER_POS2_Y", "Number Slider"),
        ("SLIDER_POS3_X", "Number Slider"),
        ("SLIDER_POS3_Y", "Number Slider"),
        ("SLIDER_POS4_X", "Number Slider"),
        ("SLIDER_POS4_Y", "Number Slider"),
        # 基礎桌腳
        ("DIV_LEG_Z", "Division"),
        ("PT_LEG_BASE", "Construct Point"),
        ("PLANE_LEG_BASE", "XY Plane"),
        ("BOX_LEG_BASE", "Center Box"),
        # 目標平面
        ("PT_LEG1", "Construct Point"),
        ("PT_LEG2", "Construct Point"),
        ("PT_LEG3", "Construct Point"),
        ("PT_LEG4", "Construct Point"),
        ("PLANE_LEG1", "XY Plane"),
        ("PLANE_LEG2", "XY Plane"),
        ("PLANE_LEG3", "XY Plane"),
        ("PLANE_LEG4", "XY Plane"),
        # Orient
        ("ORIENT1", "Orient"),
        ("ORIENT2", "Orient"),
        ("ORIENT3", "Orient"),
        ("ORIENT4", "Orient"),
        # 桌面
        ("DIV_TABLE_Z", "Division"),
        ("ADD_TABLE_Z", "Addition"),
        ("PT_TABLE", "Construct Point"),
        ("PLANE_TABLE", "XY Plane"),
        ("BOX_TABLE", "Center Box"),
        # 輸出
        ("MERGE1", "Merge"),
        ("MERGE2", "Merge"),
        ("MERGE3", "Merge"),
        ("MERGE4", "Merge"),
        ("PREVIEW", "Custom Preview"),
    ]

    created_count = 0
    for name, type_name in components_to_create:
        if executor.create_component(name, type_name):
            created_count += 1
        time.sleep(0.08)

    print(f"\n  創建了 {created_count}/{len(components_to_create)} 個組件")

    # ========================================
    # 6. 創建連線
    # ========================================
    print("\n[6/7] 創建連線...")

    connections_to_create = [
        # 基礎桌腳 - 使用 Name 而非 NickName
        ("SLIDER_LEG_H", "V", "DIV_LEG_Z", "A"),
        ("CONST_2", "V", "DIV_LEG_Z", "B"),
        ("DIV_LEG_Z", "Result", "PT_LEG_BASE", "Z coordinate"),  # R→Result
        ("PT_LEG_BASE", "Point", "PLANE_LEG_BASE", "O"),         # Pt→Point
        ("PLANE_LEG_BASE", "Pl", "BOX_LEG_BASE", "Base"),
        ("SLIDER_LEG_SIZE", "V", "BOX_LEG_BASE", "X"),
        ("SLIDER_LEG_SIZE", "V", "BOX_LEG_BASE", "Y"),
        ("SLIDER_LEG_H", "V", "BOX_LEG_BASE", "Z"),
        # Leg 1
        ("SLIDER_POS1_X", "V", "PT_LEG1", "X coordinate"),
        ("SLIDER_POS1_Y", "V", "PT_LEG1", "Y coordinate"),
        ("DIV_LEG_Z", "Result", "PT_LEG1", "Z coordinate"),
        ("PT_LEG1", "Point", "PLANE_LEG1", "O"),
        # Leg 2
        ("SLIDER_POS2_X", "V", "PT_LEG2", "X coordinate"),
        ("SLIDER_POS2_Y", "V", "PT_LEG2", "Y coordinate"),
        ("DIV_LEG_Z", "Result", "PT_LEG2", "Z coordinate"),
        ("PT_LEG2", "Point", "PLANE_LEG2", "O"),
        # Leg 3
        ("SLIDER_POS3_X", "V", "PT_LEG3", "X coordinate"),
        ("SLIDER_POS3_Y", "V", "PT_LEG3", "Y coordinate"),
        ("DIV_LEG_Z", "Result", "PT_LEG3", "Z coordinate"),
        ("PT_LEG3", "Point", "PLANE_LEG3", "O"),
        # Leg 4
        ("SLIDER_POS4_X", "V", "PT_LEG4", "X coordinate"),
        ("SLIDER_POS4_Y", "V", "PT_LEG4", "Y coordinate"),
        ("DIV_LEG_Z", "Result", "PT_LEG4", "Z coordinate"),
        ("PT_LEG4", "Point", "PLANE_LEG4", "O"),
        # Orient - 使用正確的參數名
        ("BOX_LEG_BASE", "Box", "ORIENT1", "Geometry"),
        ("BOX_LEG_BASE", "Box", "ORIENT2", "Geometry"),
        ("BOX_LEG_BASE", "Box", "ORIENT3", "Geometry"),
        ("BOX_LEG_BASE", "Box", "ORIENT4", "Geometry"),
        ("PLANE_LEG_BASE", "Pl", "ORIENT1", "Source"),
        ("PLANE_LEG_BASE", "Pl", "ORIENT2", "Source"),
        ("PLANE_LEG_BASE", "Pl", "ORIENT3", "Source"),
        ("PLANE_LEG_BASE", "Pl", "ORIENT4", "Source"),
        ("PLANE_LEG1", "Pl", "ORIENT1", "Target"),
        ("PLANE_LEG2", "Pl", "ORIENT2", "Target"),
        ("PLANE_LEG3", "Pl", "ORIENT3", "Target"),
        ("PLANE_LEG4", "Pl", "ORIENT4", "Target"),
        # 桌面 - 使用 Name 而非 NickName
        ("SLIDER_TABLE_T", "V", "DIV_TABLE_Z", "A"),
        ("CONST_2", "V", "DIV_TABLE_Z", "B"),
        ("SLIDER_LEG_H", "V", "ADD_TABLE_Z", "A"),
        ("DIV_TABLE_Z", "Result", "ADD_TABLE_Z", "B"),    # R→Result
        ("ADD_TABLE_Z", "Result", "PT_TABLE", "Z coordinate"),  # R→Result
        ("PT_TABLE", "Point", "PLANE_TABLE", "O"),        # Pt→Point
        ("PLANE_TABLE", "Pl", "BOX_TABLE", "Base"),
        ("SLIDER_TABLE_W", "V", "BOX_TABLE", "X"),
        ("SLIDER_TABLE_D", "V", "BOX_TABLE", "Y"),
        ("SLIDER_TABLE_T", "V", "BOX_TABLE", "Z"),
        # 合併 - Merge 使用 "Data 1/2" 和 "Result" (注意空格!)
        ("BOX_TABLE", "Box", "MERGE1", "Data 1"),        # D1→Data 1
        ("ORIENT1", "Geometry", "MERGE1", "Data 2"),     # D2→Data 2
        ("MERGE1", "Result", "MERGE2", "Data 1"),        # R→Result
        ("ORIENT2", "Geometry", "MERGE2", "Data 2"),
        ("MERGE2", "Result", "MERGE3", "Data 1"),
        ("ORIENT3", "Geometry", "MERGE3", "Data 2"),
        ("MERGE3", "Result", "MERGE4", "Data 1"),
        ("ORIENT4", "Geometry", "MERGE4", "Data 2"),
        ("MERGE4", "Result", "PREVIEW", "Geometry"),
    ]

    connected_count = 0
    for from_n, from_p, to_n, to_p in connections_to_create:
        if executor.create_connection(from_n, from_p, to_n, to_p):
            connected_count += 1
        time.sleep(0.03)

    print(f"\n  創建了 {connected_count}/{len(connections_to_create)} 條連線")

    # ========================================
    # 7. 設置 Slider 值
    # ========================================
    print("\n[7/7] 設置 Slider 值...")

    slider_configs = [
        # 主要參數
        ("SLIDER_LEG_SIZE", 5, 30, 10),     # 桌腳寬度
        ("SLIDER_LEG_H", 30, 100, 70),      # 桌腳高度
        ("SLIDER_TABLE_W", 50, 200, 120),   # 桌寬
        ("SLIDER_TABLE_D", 30, 150, 80),    # 桌深
        ("SLIDER_TABLE_T", 2, 15, 5),       # 桌面厚度
        ("CONST_2", 1, 5, 2),               # 常數 2 (用於除法)
        # 桌腳位置 (四角落)
        ("SLIDER_POS1_X", -100, 100, 50),   # 前右 X
        ("SLIDER_POS1_Y", -100, 100, 30),   # 前右 Y
        ("SLIDER_POS2_X", -100, 100, -50),  # 前左 X
        ("SLIDER_POS2_Y", -100, 100, 30),   # 前左 Y
        ("SLIDER_POS3_X", -100, 100, -50),  # 後左 X
        ("SLIDER_POS3_Y", -100, 100, -30),  # 後左 Y
        ("SLIDER_POS4_X", -100, 100, 50),   # 後右 X
        ("SLIDER_POS4_Y", -100, 100, -30),  # 後右 Y
    ]

    for name, min_v, max_v, default_v in slider_configs:
        executor.set_slider(name, min_v, max_v, default_v)
        time.sleep(0.02)

    # 縮放視圖
    executor.zoom_to_all()

    # ========================================
    # 完成報告
    # ========================================
    print("\n" + "=" * 70)
    print("  ✓ Simple Table v3 創建完成！")
    print()
    print("  設計說明:")
    print("    - 桌面: 120 x 80 x 5 (位於 Z = 72.5)")
    print("    - 桌腳: 10 x 10 x 70 (中心在 Z = 35)")
    print("    - 4 腳位置: (+50,+30), (-50,+30), (-50,-30), (+50,-30)")
    print()
    print("  組件統計:")
    print(f"    - 組件: {created_count}/{len(components_to_create)}")
    print(f"    - 連線: {connected_count}/{len(connections_to_create)}")
    print()
    print("  設計來源: GH_WIP/component_info_v2.mmd")
    print("=" * 70)


if __name__ == "__main__":
    main()
