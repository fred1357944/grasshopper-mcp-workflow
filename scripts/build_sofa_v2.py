#!/usr/bin/env python3
"""
參數化沙發 v2 - 簡化版本，確保幾何正確

修正：
1. 靠背位置 - 在坐墊後方
2. 扶手位置 - 在坐墊兩側
3. 腳位置 - 使用 Negative 組件處理四角

結構示意 (Top View):
        Back
  ┌─────────────┐
  │  ┌───────┐  │
  │L │ Seat  │ R│
  │  └───────┘  │
  └─────────────┘
   1           2  <- Front legs
   3           4  <- Back legs
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized, SliderConfig


def build_sofa_v2():
    """建構參數化沙發 v2"""
    print("=" * 70)
    print("參數化沙發 v2 - 幾何優化版")
    print("=" * 70)

    client = GH_MCP_ClientOptimized(debug=True)

    # 測試連接
    print("\n1. 測試連接...")
    if not client.test_connection():
        return False

    # 清空
    print("\n2. 清空畫布...")
    client.clear_canvas()
    time.sleep(0.3)

    # =========================================================================
    # 參數 Sliders
    # =========================================================================
    print("\n3. 創建參數...")

    sliders = [
        # 整體尺寸 (cm)
        SliderConfig("SofaW", value=180, min_val=140, max_val=240, col=0, row=0),
        SliderConfig("SofaD", value=80, min_val=60, max_val=100, col=0, row=1),

        # 坐墊
        SliderConfig("SeatH", value=40, min_val=35, max_val=50, col=0, row=2),
        SliderConfig("CushionT", value=12, min_val=8, max_val=20, col=0, row=3),

        # 靠背
        SliderConfig("BackH", value=40, min_val=30, max_val=60, col=0, row=4),
        SliderConfig("BackT", value=15, min_val=10, max_val=25, col=0, row=5),

        # 扶手
        SliderConfig("ArmW", value=15, min_val=10, max_val=25, col=0, row=6),
        SliderConfig("ArmH", value=20, min_val=15, max_val=30, col=0, row=7),

        # 腳
        SliderConfig("LegH", value=10, min_val=5, max_val=15, col=0, row=8),
        SliderConfig("LegSize", value=6, min_val=4, max_val=10, col=0, row=9),

        # 常數
        SliderConfig("Const2", value=2, min_val=1, max_val=10, col=0, row=10),
    ]

    client.add_sliders_batch(sliders)
    time.sleep(0.2)

    # =========================================================================
    # Division 計算半值
    # =========================================================================
    print("\n4. 創建計算組件...")

    divisions = [
        ("Division", "HalfW", 1, 0),      # SofaW / 2
        ("Division", "HalfD", 1, 1),      # SofaD / 2
        ("Division", "HalfCushT", 1, 2),  # CushionT / 2
        ("Division", "HalfBackH", 1, 3),  # BackH / 2
        ("Division", "HalfBackT", 1, 4),  # BackT / 2
        ("Division", "HalfArmW", 1, 5),   # ArmW / 2
        ("Division", "HalfLegH", 1, 6),   # LegH / 2
    ]
    client.add_components_batch(divisions)

    # Negative 計算負值 (不是 Multiplication，避免 OLD)
    negs = [
        ("Negative", "NegHalfW", 1, 7),   # -HalfW
        ("Negative", "NegHalfD", 1, 8),   # -HalfD
    ]
    client.add_components_batch(negs)

    # Mass Addition 計算 Z 座標 (不是 Addition，避免 OLD)
    adds = [
        ("Mass Addition", "SeatZ", 1, 9),     # LegH + CushionT/2
        ("Mass Addition", "BackZ", 1, 10),    # SeatH + BackH/2
        ("Mass Addition", "ArmZ", 1, 11),     # LegH + CushionT + ArmH/2
    ]
    client.add_components_batch(adds)
    time.sleep(0.1)

    # =========================================================================
    # 幾何組件
    # =========================================================================
    print("\n5. 創建幾何組件...")

    # Points
    points = [
        ("Construct Point", "PtSeat", 2, 0),
        ("Construct Point", "PtBack", 2, 1),
        ("Construct Point", "PtArmL", 2, 2),
        ("Construct Point", "PtArmR", 2, 3),
        ("Construct Point", "PtLeg1", 2, 4),  # 前左 (-X, -Y)
        ("Construct Point", "PtLeg2", 2, 5),  # 前右 (+X, -Y)
        ("Construct Point", "PtLeg3", 2, 6),  # 後左 (-X, +Y)
        ("Construct Point", "PtLeg4", 2, 7),  # 後右 (+X, +Y)
    ]
    client.add_components_batch(points)

    # Planes
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
    client.add_components_batch(planes)

    # Boxes
    boxes = [
        ("Center Box", "BoxSeat", 4, 0),
        ("Center Box", "BoxBack", 4, 1),
        ("Center Box", "BoxArmL", 4, 2),
        ("Center Box", "BoxArmR", 4, 3),
        ("Center Box", "BoxLeg1", 4, 4),
        ("Center Box", "BoxLeg2", 4, 5),
        ("Center Box", "BoxLeg3", 4, 6),
        ("Center Box", "BoxLeg4", 4, 7),
    ]
    client.add_components_batch(boxes)

    # Output
    client.add_component("Solid Union", "SofaUnion", 5, 3)
    time.sleep(0.2)

    # =========================================================================
    # 連接
    # =========================================================================
    print("\n6. 建立連接...")

    connections = []

    # --- Division 連接 ---
    div_conns = [
        ("SofaW", "N", "HalfW", "A"),
        ("SofaD", "N", "HalfD", "A"),
        ("CushionT", "N", "HalfCushT", "A"),
        ("BackH", "N", "HalfBackH", "A"),
        ("BackT", "N", "HalfBackT", "A"),
        ("ArmW", "N", "HalfArmW", "A"),
        ("LegH", "N", "HalfLegH", "A"),
        # B = 2
        ("Const2", "N", "HalfW", "B"),
        ("Const2", "N", "HalfD", "B"),
        ("Const2", "N", "HalfCushT", "B"),
        ("Const2", "N", "HalfBackH", "B"),
        ("Const2", "N", "HalfBackT", "B"),
        ("Const2", "N", "HalfArmW", "B"),
        ("Const2", "N", "HalfLegH", "B"),
    ]
    connections.extend(div_conns)

    # --- Negative 連接 (負值) ---
    # Negative: 輸入 x, 輸出 y
    neg_conns = [
        ("HalfW", "Result", "NegHalfW", "x"),
        ("HalfD", "Result", "NegHalfD", "x"),
    ]
    connections.extend(neg_conns)

    # --- Mass Addition 連接 ---
    # Mass Addition: 輸入 I (可多個), 輸出 R
    add_conns = [
        # SeatZ = LegH + CushionT/2
        ("LegH", "N", "SeatZ", "I"),
        ("HalfCushT", "Result", "SeatZ", "I"),
        # BackZ = LegH + CushionT + BackH/2 (從地面算起)
        ("LegH", "N", "BackZ", "I"),
        ("CushionT", "N", "BackZ", "I"),
        ("HalfBackH", "Result", "BackZ", "I"),
        # ArmZ = LegH + CushionT/2 + ArmH/2
        ("LegH", "N", "ArmZ", "I"),
        ("HalfCushT", "Result", "ArmZ", "I"),
        ("ArmH", "N", "ArmZ", "I"),
    ]
    connections.extend(add_conns)

    # --- 坐墊 Seat ---
    seat_conns = [
        ("SeatZ", "R", "PtSeat", "Z"),
        ("PtSeat", "Pt", "PlnSeat", "O"),
        ("PlnSeat", "P", "BoxSeat", "Base"),
        ("HalfW", "Result", "BoxSeat", "X"),
        ("HalfD", "Result", "BoxSeat", "Y"),
        ("HalfCushT", "Result", "BoxSeat", "Z"),
    ]
    connections.extend(seat_conns)

    # --- 靠背 Back ---
    # Y = HalfD (後方)
    back_conns = [
        ("BackZ", "R", "PtBack", "Z"),
        ("HalfD", "Result", "PtBack", "Y"),  # 在後方
        ("PtBack", "Pt", "PlnBack", "O"),
        ("PlnBack", "P", "BoxBack", "Base"),
        ("HalfW", "Result", "BoxBack", "X"),
        ("HalfBackT", "Result", "BoxBack", "Y"),
        ("HalfBackH", "Result", "BoxBack", "Z"),
    ]
    connections.extend(back_conns)

    # --- 扶手 Arms ---
    # 左扶手 X = -HalfW + ArmW/2 ≈ -HalfW (簡化)
    arm_l_conns = [
        ("ArmZ", "R", "PtArmL", "Z"),
        ("NegHalfW", "y", "PtArmL", "X"),  # 左側
        ("PtArmL", "Pt", "PlnArmL", "O"),
        ("PlnArmL", "P", "BoxArmL", "Base"),
        ("HalfArmW", "Result", "BoxArmL", "X"),
        ("HalfD", "Result", "BoxArmL", "Y"),
        ("ArmH", "N", "BoxArmL", "Z"),
    ]
    connections.extend(arm_l_conns)

    # 右扶手 X = +HalfW
    arm_r_conns = [
        ("ArmZ", "R", "PtArmR", "Z"),
        ("HalfW", "Result", "PtArmR", "X"),  # 右側
        ("PtArmR", "Pt", "PlnArmR", "O"),
        ("PlnArmR", "P", "BoxArmR", "Base"),
        ("HalfArmW", "Result", "BoxArmR", "X"),
        ("HalfD", "Result", "BoxArmR", "Y"),
        ("ArmH", "N", "BoxArmR", "Z"),
    ]
    connections.extend(arm_r_conns)

    # --- 4隻腳 ---
    # Leg1: 前左 (-X, -Y)
    leg1_conns = [
        ("HalfLegH", "Result", "PtLeg1", "Z"),
        ("NegHalfW", "y", "PtLeg1", "X"),
        ("NegHalfD", "y", "PtLeg1", "Y"),
        ("PtLeg1", "Pt", "PlnLeg1", "O"),
        ("PlnLeg1", "P", "BoxLeg1", "Base"),
        ("LegSize", "N", "BoxLeg1", "X"),
        ("LegSize", "N", "BoxLeg1", "Y"),
        ("HalfLegH", "Result", "BoxLeg1", "Z"),
    ]
    connections.extend(leg1_conns)

    # Leg2: 前右 (+X, -Y)
    leg2_conns = [
        ("HalfLegH", "Result", "PtLeg2", "Z"),
        ("HalfW", "Result", "PtLeg2", "X"),
        ("NegHalfD", "y", "PtLeg2", "Y"),
        ("PtLeg2", "Pt", "PlnLeg2", "O"),
        ("PlnLeg2", "P", "BoxLeg2", "Base"),
        ("LegSize", "N", "BoxLeg2", "X"),
        ("LegSize", "N", "BoxLeg2", "Y"),
        ("HalfLegH", "Result", "BoxLeg2", "Z"),
    ]
    connections.extend(leg2_conns)

    # Leg3: 後左 (-X, +Y)
    leg3_conns = [
        ("HalfLegH", "Result", "PtLeg3", "Z"),
        ("NegHalfW", "y", "PtLeg3", "X"),
        ("HalfD", "Result", "PtLeg3", "Y"),
        ("PtLeg3", "Pt", "PlnLeg3", "O"),
        ("PlnLeg3", "P", "BoxLeg3", "Base"),
        ("LegSize", "N", "BoxLeg3", "X"),
        ("LegSize", "N", "BoxLeg3", "Y"),
        ("HalfLegH", "Result", "BoxLeg3", "Z"),
    ]
    connections.extend(leg3_conns)

    # Leg4: 後右 (+X, +Y)
    leg4_conns = [
        ("HalfLegH", "Result", "PtLeg4", "Z"),
        ("HalfW", "Result", "PtLeg4", "X"),
        ("HalfD", "Result", "PtLeg4", "Y"),
        ("PtLeg4", "Pt", "PlnLeg4", "O"),
        ("PlnLeg4", "P", "BoxLeg4", "Base"),
        ("LegSize", "N", "BoxLeg4", "X"),
        ("LegSize", "N", "BoxLeg4", "Y"),
        ("HalfLegH", "Result", "BoxLeg4", "Z"),
    ]
    connections.extend(leg4_conns)

    # --- Solid Union ---
    union_conns = [
        ("BoxSeat", "B", "SofaUnion", "B"),
        ("BoxBack", "B", "SofaUnion", "B"),
        ("BoxArmL", "B", "SofaUnion", "B"),
        ("BoxArmR", "B", "SofaUnion", "B"),
        ("BoxLeg1", "B", "SofaUnion", "B"),
        ("BoxLeg2", "B", "SofaUnion", "B"),
        ("BoxLeg3", "B", "SofaUnion", "B"),
        ("BoxLeg4", "B", "SofaUnion", "B"),
    ]
    connections.extend(union_conns)

    # 執行
    success, fail = client.connect_batch(connections)

    # 總結
    client.print_summary()

    print("\n沙發參數:")
    print("   SofaW=180, SofaD=80 (整體)")
    print("   SeatH=40, CushionT=12 (坐墊)")
    print("   BackH=40, BackT=15 (靠背)")
    print("   ArmW=15, ArmH=20 (扶手)")
    print("   LegH=10, LegSize=6 (腳)")

    # 保存
    import json
    id_map = client.get_id_map()
    id_map_path = PROJECT_ROOT / "GH_WIP" / "sofa_v2_id_map.json"
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)
    print(f"\n✓ ID 映射: {id_map_path}")

    if fail == 0:
        print("\n" + "=" * 70)
        print("✓ 沙發 v2 建構完成！")
        print("=" * 70)
        return True
    else:
        print(f"\n⚠ {fail} 個連接失敗")
        return False


if __name__ == "__main__":
    build_sofa_v2()
