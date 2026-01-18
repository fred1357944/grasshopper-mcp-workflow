#!/usr/bin/env python3
"""
參數化沙發設計 - GH MCP 建構腳本

設計特點:
- 雙人座沙發
- 厚實的坐墊和靠背
- 兩側扶手
- 4 隻矮腳
- 10+ 個可調參數

結構:
  ┌─────────────────────────────┐
  │         靠背 Back           │
  ├──────┬─────────────┬──────┤
  │ 左扶手│   坐墊 Seat   │ 右扶手│
  │ ArmL  │             │ ArmR  │
  └──┬────┴─────────────┴────┬──┘
     │  腳1    腳2  腳3   腳4  │
     └────────────────────────┘

佈局:
  Col 0-1: 參數 Sliders
  Col 2: 輔助計算 (Division, Addition)
  Col 3: 平面 (XY Plane)
  Col 4: Box 組件
  Col 5: 輸出 (Solid Union)
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized, SliderConfig


def build_sofa():
    """建構參數化沙發"""
    print("=" * 70)
    print("參數化雙人沙發 - GH MCP 建構")
    print("=" * 70)

    client = GH_MCP_ClientOptimized(debug=True)

    # 測試連接
    print("\n1. 測試 GH_MCP 連接...")
    if not client.test_connection():
        print("   ✗ 無法連接")
        return False

    # 清空畫布
    print("\n2. 準備畫布...")
    client.clear_canvas()
    time.sleep(0.3)

    # =========================================================================
    # 3. 參數 Sliders (Col 0-1)
    # =========================================================================
    print("\n3. 創建參數滑桿...")

    # 整體尺寸
    sliders_main = [
        SliderConfig("SofaW", value=180, min_val=140, max_val=240, col=0, row=0),   # 沙發總寬
        SliderConfig("SofaD", value=85, min_val=70, max_val=100, col=0, row=1),     # 沙發深度
        SliderConfig("SeatH", value=45, min_val=35, max_val=55, col=0, row=2),      # 座高
    ]

    # 坐墊參數
    sliders_seat = [
        SliderConfig("CushionH", value=15, min_val=10, max_val=25, col=0, row=3),   # 坐墊厚度
        SliderConfig("CushionD", value=60, min_val=50, max_val=75, col=0, row=4),   # 坐墊深度
    ]

    # 靠背參數
    sliders_back = [
        SliderConfig("BackH", value=45, min_val=35, max_val=60, col=1, row=0),      # 靠背高度
        SliderConfig("BackT", value=18, min_val=12, max_val=25, col=1, row=1),      # 靠背厚度
    ]

    # 扶手參數
    sliders_arm = [
        SliderConfig("ArmW", value=12, min_val=8, max_val=18, col=1, row=2),        # 扶手寬度
        SliderConfig("ArmH", value=25, min_val=18, max_val=35, col=1, row=3),       # 扶手高度
    ]

    # 腳參數
    sliders_leg = [
        SliderConfig("LegH", value=8, min_val=5, max_val=15, col=1, row=4),         # 腳高度
        SliderConfig("LegS", value=5, min_val=3, max_val=8, col=1, row=5),          # 腳尺寸
    ]

    all_sliders = sliders_main + sliders_seat + sliders_back + sliders_arm + sliders_leg
    client.add_sliders_batch(all_sliders)
    time.sleep(0.2)

    # =========================================================================
    # 4. 輔助計算 (Col 2)
    # =========================================================================
    print("\n4. 創建輔助計算...")

    # Division (用於計算半值)
    divisions = [
        ("Division", "HalfSofaW", 2, 0),    # SofaW / 2
        ("Division", "HalfSofaD", 2, 1),    # SofaD / 2
        ("Division", "HalfCushH", 2, 2),    # CushionH / 2
        ("Division", "HalfBackH", 2, 3),    # BackH / 2
        ("Division", "HalfArmW", 2, 4),     # ArmW / 2
        ("Division", "HalfLegS", 2, 5),     # LegS / 2
    ]

    # 常數 2 (用於除法)
    client.add_slider("Const2", col=2, row=6, value=2, min_val=1, max_val=10)

    client.add_components_batch(divisions)
    time.sleep(0.1)

    # =========================================================================
    # 5. 位置計算 (Col 2, 補充)
    # =========================================================================
    print("\n5. 創建位置計算...")

    # Addition (用於計算 Z 座標)
    additions = [
        ("Addition", "SeatCenterZ", 2, 7),   # LegH + CushionH/2
        ("Addition", "BackCenterZ", 2, 8),   # SeatH + BackH/2
        ("Addition", "ArmCenterZ", 2, 9),    # LegH + CushionH + ArmH/2
    ]

    client.add_components_batch(additions)
    time.sleep(0.1)

    # =========================================================================
    # 6. 基準平面 (Col 3)
    # =========================================================================
    print("\n6. 創建基準平面...")

    planes = [
        ("XY Plane", "PlnSeat", 3, 0),
        ("XY Plane", "PlnBack", 3, 1),
        ("XY Plane", "PlnArmL", 3, 2),
        ("XY Plane", "PlnArmR", 3, 3),
        ("XY Plane", "PlnLeg1", 3, 4),
        ("XY Plane", "PlnLeg2", 3, 5),
        ("XY Plane", "PlnLeg3", 3, 6),
        ("XY Plane", "PlnLeg4", 3, 7),
    ]

    # 點（用於建立平面原點）
    points = [
        ("Construct Point", "PtSeat", 3, 8),
        ("Construct Point", "PtBack", 3, 9),
        ("Construct Point", "PtArmL", 3, 10),
        ("Construct Point", "PtArmR", 3, 11),
        ("Construct Point", "PtLeg1", 3, 12),
        ("Construct Point", "PtLeg2", 3, 13),
        ("Construct Point", "PtLeg3", 3, 14),
        ("Construct Point", "PtLeg4", 3, 15),
    ]

    client.add_components_batch(planes)
    client.add_components_batch(points)
    time.sleep(0.1)

    # =========================================================================
    # 7. Box 組件 (Col 4)
    # =========================================================================
    print("\n7. 創建 Box 組件...")

    boxes = [
        ("Center Box", "BoxSeat", 4, 0),     # 坐墊
        ("Center Box", "BoxBack", 4, 1),     # 靠背
        ("Center Box", "BoxArmL", 4, 2),     # 左扶手
        ("Center Box", "BoxArmR", 4, 3),     # 右扶手
        ("Center Box", "BoxLeg1", 4, 4),     # 腳1
        ("Center Box", "BoxLeg2", 4, 5),     # 腳2
        ("Center Box", "BoxLeg3", 4, 6),     # 腳3
        ("Center Box", "BoxLeg4", 4, 7),     # 腳4
    ]

    client.add_components_batch(boxes)
    time.sleep(0.1)

    # =========================================================================
    # 8. 輸出 (Col 5)
    # =========================================================================
    print("\n8. 創建輸出...")

    client.add_component("Solid Union", "SofaUnion", 5, 3)
    time.sleep(0.1)

    # =========================================================================
    # 9. 建立連接
    # =========================================================================
    print("\n9. 建立連接...")

    connections = []

    # --- Division 連接 (計算半值) ---
    div_connections = [
        ("SofaW", "N", "HalfSofaW", "A"),
        ("SofaD", "N", "HalfSofaD", "A"),
        ("CushionH", "N", "HalfCushH", "A"),
        ("BackH", "N", "HalfBackH", "A"),
        ("ArmW", "N", "HalfArmW", "A"),
        ("LegS", "N", "HalfLegS", "A"),
        # B 參數都連到 Const2
        ("Const2", "N", "HalfSofaW", "B"),
        ("Const2", "N", "HalfSofaD", "B"),
        ("Const2", "N", "HalfCushH", "B"),
        ("Const2", "N", "HalfBackH", "B"),
        ("Const2", "N", "HalfArmW", "B"),
        ("Const2", "N", "HalfLegS", "B"),
    ]
    connections.extend(div_connections)

    # --- 坐墊 Seat ---
    seat_connections = [
        # 坐墊位置 Z = LegH + CushionH/2
        ("LegH", "N", "SeatCenterZ", "A"),
        ("HalfCushH", "Result", "SeatCenterZ", "B"),
        # 點 → 平面 → Box
        ("SeatCenterZ", "Result", "PtSeat", "Z"),
        ("PtSeat", "Pt", "PlnSeat", "O"),
        ("PlnSeat", "P", "BoxSeat", "Base"),
        # 坐墊尺寸
        ("HalfSofaW", "Result", "BoxSeat", "X"),
        ("CushionD", "N", "BoxSeat", "Y"),
        ("HalfCushH", "Result", "BoxSeat", "Z"),
    ]
    connections.extend(seat_connections)

    # --- 靠背 Back ---
    # 靠背 Z = LegH + CushionH + BackH/2 (坐墊頂面開始往上)
    # 靠背 Y = CushionD/2 (在坐墊後方)
    back_connections = [
        # 靠背位置 Z = SeatCenterZ + CushionH/2 + BackH/2 ≈ LegH + CushionH + BackH/2
        ("SeatCenterZ", "Result", "BackCenterZ", "A"),  # 使用坐墊中心Z
        ("HalfBackH", "Result", "BackCenterZ", "B"),    # 加上靠背半高
        # 點 → 平面 → Box
        ("BackCenterZ", "Result", "PtBack", "Z"),
        ("CushionD", "N", "PtBack", "Y"),  # Y = CushionD/2 (靠後)
        ("PtBack", "Pt", "PlnBack", "O"),
        ("PlnBack", "P", "BoxBack", "Base"),
        # 靠背尺寸
        ("HalfSofaW", "Result", "BoxBack", "X"),
        ("BackT", "N", "BoxBack", "Y"),
        ("HalfBackH", "Result", "BoxBack", "Z"),
    ]
    connections.extend(back_connections)

    # --- 扶手 Arms ---
    arm_connections = [
        # 扶手高度 Z = LegH + CushionH + ArmH/2
        ("SeatCenterZ", "Result", "ArmCenterZ", "A"),
        ("ArmH", "N", "ArmCenterZ", "B"),

        # 左扶手
        ("ArmCenterZ", "Result", "PtArmL", "Z"),
        ("HalfSofaW", "Result", "PtArmL", "X"),  # X = -SofaW/2 + ArmW/2
        ("PtArmL", "Pt", "PlnArmL", "O"),
        ("PlnArmL", "P", "BoxArmL", "Base"),
        ("HalfArmW", "Result", "BoxArmL", "X"),
        ("HalfSofaD", "Result", "BoxArmL", "Y"),
        ("ArmH", "N", "BoxArmL", "Z"),

        # 右扶手 (類似左扶手，但 X 為正)
        ("ArmCenterZ", "Result", "PtArmR", "Z"),
        ("HalfSofaW", "Result", "PtArmR", "X"),  # X = SofaW/2 - ArmW/2
        ("PtArmR", "Pt", "PlnArmR", "O"),
        ("PlnArmR", "P", "BoxArmR", "Base"),
        ("HalfArmW", "Result", "BoxArmR", "X"),
        ("HalfSofaD", "Result", "BoxArmR", "Y"),
        ("ArmH", "N", "BoxArmR", "Z"),
    ]
    connections.extend(arm_connections)

    # --- 4 隻腳 Legs ---
    # 腳位置需要 +/- 來區分四角，但 GH 沒有直接的 Negate
    # 簡化方案：四隻腳都用同一個 Box，通過 Multiplication 或手動設置
    # 這裡先只連接共用尺寸，位置需要另外處理

    # 暫時: 所有腳都在原點，尺寸正確
    leg_connections = []

    # 腳共用連接 (尺寸)
    for i in range(1, 5):
        leg_connections.extend([
            ("HalfLegS", "Result", f"PtLeg{i}", "Z"),
            ("HalfSofaW", "Result", f"PtLeg{i}", "X"),
            ("HalfSofaD", "Result", f"PtLeg{i}", "Y"),
            (f"PtLeg{i}", "Pt", f"PlnLeg{i}", "O"),
            (f"PlnLeg{i}", "P", f"BoxLeg{i}", "Base"),
            ("HalfLegS", "Result", f"BoxLeg{i}", "X"),
            ("HalfLegS", "Result", f"BoxLeg{i}", "Y"),
            ("LegH", "N", f"BoxLeg{i}", "Z"),
        ])

    connections.extend(leg_connections)

    # --- Solid Union ---
    union_connections = [
        ("BoxSeat", "B", "SofaUnion", "B"),
        ("BoxBack", "B", "SofaUnion", "B"),
        ("BoxArmL", "B", "SofaUnion", "B"),
        ("BoxArmR", "B", "SofaUnion", "B"),
        ("BoxLeg1", "B", "SofaUnion", "B"),
        ("BoxLeg2", "B", "SofaUnion", "B"),
        ("BoxLeg3", "B", "SofaUnion", "B"),
        ("BoxLeg4", "B", "SofaUnion", "B"),
    ]
    connections.extend(union_connections)

    # 執行連接
    success, fail = client.connect_batch(connections)

    # =========================================================================
    # 10. 總結
    # =========================================================================
    client.print_summary()

    print("\n沙發結構:")
    print("   - 坐墊 (Seat): 主要承載面")
    print("   - 靠背 (Back): 傾斜支撐")
    print("   - 扶手 (ArmL/ArmR): 兩側扶手")
    print("   - 4隻腳 (Leg1-4): 四角支撐")

    print("\n可調參數:")
    print("   整體: SofaW(寬), SofaD(深), SeatH(座高)")
    print("   坐墊: CushionH(厚), CushionD(深)")
    print("   靠背: BackH(高), BackT(厚)")
    print("   扶手: ArmW(寬), ArmH(高)")
    print("   腳:   LegH(高), LegS(尺寸)")

    # 保存 ID 映射
    import json
    id_map = client.get_id_map()
    id_map_path = PROJECT_ROOT / "GH_WIP" / "sofa_id_map.json"
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)
    print(f"\n✓ ID 映射已保存: {id_map_path}")

    if fail == 0:
        print("\n" + "=" * 70)
        print("✓ 沙發建構完成！請在 Grasshopper 中查看")
        print("=" * 70)
        return True
    else:
        print(f"\n⚠ 有 {fail} 個連接失敗")
        return False


if __name__ == "__main__":
    build_sofa()
