#!/usr/bin/env python3
"""
工業設計水杯 v2 - 使用優化客戶端

設計特點:
- 簡潔的圓柱形杯身
- 微微內收的腰線（符合人體工學）
- 平底設計，穩定性佳
- 5 個可調參數

佈局:
  Col 0      Col 1       Col 2        Col 3       Col 4-5
  Sliders -> Points  -> Planes   -> Circles -> Loft/Cap

使用優化後的 GH_MCP_ClientOptimized:
- 兩步驟 slider 設置 (先 range 再 value)
- 自動 nickname → id 映射
- 統一的錯誤處理
"""

import sys
import time
from pathlib import Path

# 添加專案路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized, SliderConfig


def build_industrial_cup():
    """建構工業設計水杯 (使用優化客戶端)"""
    print("=" * 60)
    print("工業設計水杯 v2 - 優化客戶端")
    print("=" * 60)

    # 初始化客戶端
    client = GH_MCP_ClientOptimized(debug=True)

    # 測試連接
    print("\n1. 測試 GH_MCP 連接...")
    if not client.test_connection():
        print("   ✗ 無法連接，請確認 Grasshopper 已開啟")
        return False

    # 清空畫布
    print("\n2. 準備畫布...")
    client.clear_canvas()
    time.sleep(0.3)

    # =========================================================================
    # 3. 創建 Sliders (Column 0)
    # =========================================================================
    print("\n3. 創建參數滑桿 [Col 0]...")

    slider_configs = [
        SliderConfig(nickname="Height", value=120, min_val=80, max_val=200, col=0, row=0),
        SliderConfig(nickname="BottomR", value=35, min_val=25, max_val=50, col=0, row=1),
        SliderConfig(nickname="TopR", value=40, min_val=25, max_val=60, col=0, row=2),
        SliderConfig(nickname="WaistR", value=32.5, min_val=20, max_val=45, col=0, row=3),
        SliderConfig(nickname="WaistH", value=40, min_val=20, max_val=80, col=0, row=4),
    ]

    client.add_sliders_batch(slider_configs)
    time.sleep(0.2)

    # =========================================================================
    # 4. 創建 Points (Column 1)
    # =========================================================================
    print("\n4. 創建構建點 [Col 1]...")

    points = [
        ("Construct Point", "Origin", 1, 1),
        ("Construct Point", "WaistPt", 1, 3),
        ("Construct Point", "TopPt", 1, 0),
    ]

    client.add_components_batch(points)
    time.sleep(0.1)

    # =========================================================================
    # 5. 創建 Planes (Column 2)
    # =========================================================================
    print("\n5. 創建 XY 平面 [Col 2]...")

    planes = [
        ("XY Plane", "PlnBottom", 2, 1),
        ("XY Plane", "PlnWaist", 2, 3),
        ("XY Plane", "PlnTop", 2, 0),
    ]

    client.add_components_batch(planes)
    time.sleep(0.1)

    # =========================================================================
    # 6. 創建 Circles (Column 3)
    # =========================================================================
    print("\n6. 創建圓形 [Col 3]...")

    circles = [
        ("Circle", "CircleBottom", 3, 1),
        ("Circle", "CircleWaist", 3, 3),
        ("Circle", "CircleTop", 3, 2),
    ]

    client.add_components_batch(circles)
    time.sleep(0.1)

    # =========================================================================
    # 7. 創建 Loft 和 Cap (Column 4-5)
    # =========================================================================
    print("\n7. 創建曲面 [Col 4-5]...")

    surfaces = [
        ("Loft", "CupBody", 4, 2),
        ("Cap Holes", "CapBottom", 5, 2),
    ]

    client.add_components_batch(surfaces)
    time.sleep(0.2)

    # =========================================================================
    # 8. 建立連接
    # =========================================================================
    print("\n8. 建立連接...")

    connections = [
        # 高度控制
        ("Height", "N", "TopPt", "Z"),
        ("WaistH", "N", "WaistPt", "Z"),

        # 半徑控制
        ("BottomR", "N", "CircleBottom", "R"),
        ("WaistR", "N", "CircleWaist", "R"),
        ("TopR", "N", "CircleTop", "R"),

        # 點到平面
        ("Origin", "Pt", "PlnBottom", "O"),
        ("WaistPt", "Pt", "PlnWaist", "O"),
        ("TopPt", "Pt", "PlnTop", "O"),

        # 平面到圓
        ("PlnBottom", "P", "CircleBottom", "P"),
        ("PlnWaist", "P", "CircleWaist", "P"),
        ("PlnTop", "P", "CircleTop", "P"),

        # 圓到 Loft (注意: 順序重要 - 從底到頂)
        ("CircleBottom", "C", "CupBody", "C"),
        ("CircleWaist", "C", "CupBody", "C"),
        ("CircleTop", "C", "CupBody", "C"),

        # Loft 到 Cap
        ("CupBody", "L", "CapBottom", "B"),
    ]

    success, fail = client.connect_batch(connections)

    # =========================================================================
    # 9. 總結
    # =========================================================================
    client.print_summary()

    print("\n佈局說明:")
    print("   Col 0: 參數滑桿 (Height, BottomR, TopR, WaistR, WaistH)")
    print("   Col 1: 構建點 (Origin, WaistPt, TopPt)")
    print("   Col 2: XY 平面")
    print("   Col 3: 圓形截面")
    print("   Col 4-5: Loft → Cap")

    print("\n調整參數:")
    print("   - Height: 杯身高度 (80-200mm)")
    print("   - BottomR/TopR: 底部/頂部半徑")
    print("   - WaistR < BottomR/TopR: 內收腰線")
    print("   - WaistH: 腰線高度位置")

    # 保存 ID 映射
    import json
    id_map = client.get_id_map()
    id_map_path = PROJECT_ROOT / "GH_WIP" / "cup_id_map.json"
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)
    print(f"\n✓ ID 映射已保存: {id_map_path}")

    if fail == 0:
        print("\n" + "=" * 60)
        print("✓ 水杯建構完成！請在 Grasshopper 中查看")
        print("=" * 60)
        return True
    else:
        print(f"\n⚠ 有 {fail} 個連接失敗，請檢查 Grasshopper")
        return False


if __name__ == "__main__":
    build_industrial_cup()
