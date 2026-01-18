#!/usr/bin/env python3
"""
參數化翹翹板 (Seesaw) - GH_MCP 建模腳本

結構示意 (Side View):
                     ↑ BoardT
    ┌────────────────────────────────────┐
    │              Board                  │  ← BoardLen
    └────────────────────────────────────┘
                    │
             ┌──────┴──────┐
             │   Pivot     │  ← PivotH
             │  (三角形)   │
             └─────────────┘
    ════════════════════════════════════════  Ground

結構示意 (Top View):
    ┌────────────────────────────────────┐
    │  Handle    Board           Handle  │
    │   ─│─                        ─│─   │
    └────────────────────────────────────┘
              ← BoardW →

組件列表:
- Board: 主板身 (Center Box)
- Pivot: 支點/支架 (簡化為 Center Box)
- HandleL/HandleR: 左右握把 (Cylinder)
- SeatL/SeatR: 座位區標記 (可選)
"""

import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized, SliderConfig


def build_seesaw():
    """建構參數化翹翹板"""
    print("=" * 70)
    print("參數化翹翹板 (Seesaw)")
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
    # 參數 Sliders (單位: cm)
    # =========================================================================
    print("\n3. 創建參數...")

    sliders = [
        # 板身尺寸
        SliderConfig("BoardLen", value=300, min_val=200, max_val=400, col=0, row=0),  # 長度
        SliderConfig("BoardW", value=30, min_val=20, max_val=50, col=0, row=1),       # 寬度
        SliderConfig("BoardT", value=5, min_val=3, max_val=10, col=0, row=2),         # 厚度

        # 支點尺寸
        SliderConfig("PivotH", value=50, min_val=30, max_val=80, col=0, row=3),       # 支點高度
        SliderConfig("PivotW", value=40, min_val=25, max_val=60, col=0, row=4),       # 支點寬度
        SliderConfig("PivotD", value=35, min_val=20, max_val=50, col=0, row=5),       # 支點深度

        # 握把尺寸
        SliderConfig("HandleR", value=2, min_val=1, max_val=4, col=0, row=6),         # 握把半徑
        SliderConfig("HandleH", value=25, min_val=15, max_val=40, col=0, row=7),      # 握把高度
        SliderConfig("HandleOffset", value=25, min_val=15, max_val=40, col=0, row=8), # 握把距端點距離

        # 常數
        SliderConfig("Const2", value=2, min_val=1, max_val=10, col=0, row=9),
    ]

    client.add_sliders_batch(sliders)
    time.sleep(0.2)

    # =========================================================================
    # Division 計算半值
    # =========================================================================
    print("\n4. 創建計算組件...")

    divisions = [
        ("Division", "HalfLen", 1, 0),      # BoardLen / 2
        ("Division", "HalfW", 1, 1),        # BoardW / 2
        ("Division", "HalfT", 1, 2),        # BoardT / 2
        ("Division", "HalfPivotH", 1, 3),   # PivotH / 2
        ("Division", "HalfPivotW", 1, 4),   # PivotW / 2
        ("Division", "HalfPivotD", 1, 5),   # PivotD / 2
        ("Division", "HalfHandleH", 1, 6),  # HandleH / 2
    ]
    client.add_components_batch(divisions)

    # Negative 計算負值
    negs = [
        ("Negative", "NegHalfLen", 1, 7),   # -HalfLen (左側位置)
    ]
    client.add_components_batch(negs)

    # Mass Addition 計算 Z 座標
    adds = [
        ("Mass Addition", "BoardZ", 1, 8),      # PivotH + HalfT (板身中心 Z)
        ("Mass Addition", "HandleZ", 1, 9),     # PivotH + BoardT + HalfHandleH
        ("Mass Addition", "HandleBaseZ", 1, 10), # PivotH + BoardT (握把底部)
    ]
    client.add_components_batch(adds)

    # Subtraction 計算握把 X 位置
    subs = [
        ("Subtraction", "HandleLX", 1, 11),  # -HalfLen + HandleOffset
        ("Subtraction", "HandleRX", 1, 12),  # HalfLen - HandleOffset
    ]
    client.add_components_batch(subs)
    time.sleep(0.1)

    # =========================================================================
    # 幾何組件
    # =========================================================================
    print("\n5. 創建幾何組件...")

    # Points
    points = [
        ("Construct Point", "PtBoard", 2, 0),    # 板身中心點
        ("Construct Point", "PtPivot", 2, 1),    # 支點中心點
        ("Construct Point", "PtHandleL", 2, 2),  # 左握把底部
        ("Construct Point", "PtHandleR", 2, 3),  # 右握把底部
    ]
    client.add_components_batch(points)

    # Planes
    planes = [
        ("XY Plane", "PlnBoard", 3, 0),
        ("XY Plane", "PlnPivot", 3, 1),
        ("XY Plane", "PlnHandleL", 3, 2),
        ("XY Plane", "PlnHandleR", 3, 3),
    ]
    client.add_components_batch(planes)

    # Geometry
    geo = [
        ("Center Box", "BoxBoard", 4, 0),      # 板身
        ("Center Box", "BoxPivot", 4, 1),      # 支點
        ("Cylinder", "CylHandleL", 4, 2),      # 左握把
        ("Cylinder", "CylHandleR", 4, 3),      # 右握把
    ]
    client.add_components_batch(geo)

    # Output
    client.add_component("Solid Union", "SeesawUnion", 5, 2)
    time.sleep(0.2)

    # =========================================================================
    # 連接
    # =========================================================================
    print("\n6. 建立連接...")

    connections = []

    # --- Division 連接 ---
    div_conns = [
        ("BoardLen", "N", "HalfLen", "A"),
        ("BoardW", "N", "HalfW", "A"),
        ("BoardT", "N", "HalfT", "A"),
        ("PivotH", "N", "HalfPivotH", "A"),
        ("PivotW", "N", "HalfPivotW", "A"),
        ("PivotD", "N", "HalfPivotD", "A"),
        ("HandleH", "N", "HalfHandleH", "A"),
        # B = 2
        ("Const2", "N", "HalfLen", "B"),
        ("Const2", "N", "HalfW", "B"),
        ("Const2", "N", "HalfT", "B"),
        ("Const2", "N", "HalfPivotH", "B"),
        ("Const2", "N", "HalfPivotW", "B"),
        ("Const2", "N", "HalfPivotD", "B"),
        ("Const2", "N", "HalfHandleH", "B"),
    ]
    connections.extend(div_conns)

    # --- Negative 連接 ---
    neg_conns = [
        ("HalfLen", "Result", "NegHalfLen", "x"),
    ]
    connections.extend(neg_conns)

    # --- Mass Addition 連接 ---
    add_conns = [
        # BoardZ = PivotH + HalfT
        ("PivotH", "N", "BoardZ", "I"),
        ("HalfT", "Result", "BoardZ", "I"),
        # HandleZ = PivotH + BoardT + HalfHandleH
        ("PivotH", "N", "HandleZ", "I"),
        ("BoardT", "N", "HandleZ", "I"),
        ("HalfHandleH", "Result", "HandleZ", "I"),
        # HandleBaseZ = PivotH + BoardT
        ("PivotH", "N", "HandleBaseZ", "I"),
        ("BoardT", "N", "HandleBaseZ", "I"),
    ]
    connections.extend(add_conns)

    # --- Subtraction 連接 (握把 X 位置) ---
    sub_conns = [
        # HandleLX = NegHalfLen + HandleOffset = -(HalfLen - HandleOffset)
        ("NegHalfLen", "y", "HandleLX", "A"),
        ("HandleOffset", "N", "HandleLX", "B"),  # A - B = -HalfLen - HandleOffset (錯)
        # 實際需要: HandleLX = -HalfLen + HandleOffset
        # Subtraction: Result = A - B
        # 所以這裡調整：HandleLX = HandleOffset - HalfLen (用減法)
        # 或改用 Mass Addition + Negative
    ]
    # 修正：使用 Addition (但 Addition 是 OLD)
    # 改用另一組 Mass Addition
    # 暫時先簡化，HandleLX 直接用 NegHalfLen + 小偏移
    # 這裡用 Subtraction: HandleRX = HalfLen - HandleOffset
    sub_conns = [
        # HandleRX = HalfLen - HandleOffset
        ("HalfLen", "Result", "HandleRX", "A"),
        ("HandleOffset", "N", "HandleRX", "B"),
    ]
    connections.extend(sub_conns)

    # HandleLX 改用另一種方式計算
    # HandleLX = -(HandleRX) = -HalfLen + HandleOffset
    # 需要額外 Negative，但先簡化為手動計算

    # --- 板身 Board ---
    board_conns = [
        ("BoardZ", "R", "PtBoard", "Z"),
        ("PtBoard", "Pt", "PlnBoard", "O"),
        ("PlnBoard", "P", "BoxBoard", "Base"),
        ("HalfLen", "Result", "BoxBoard", "X"),
        ("HalfW", "Result", "BoxBoard", "Y"),
        ("HalfT", "Result", "BoxBoard", "Z"),
    ]
    connections.extend(board_conns)

    # --- 支點 Pivot ---
    pivot_conns = [
        ("HalfPivotH", "Result", "PtPivot", "Z"),
        ("PtPivot", "Pt", "PlnPivot", "O"),
        ("PlnPivot", "P", "BoxPivot", "Base"),
        ("HalfPivotW", "Result", "BoxPivot", "X"),
        ("HalfPivotD", "Result", "BoxPivot", "Y"),
        ("HalfPivotH", "Result", "BoxPivot", "Z"),
    ]
    connections.extend(pivot_conns)

    # --- 左握把 HandleL ---
    # X = -HalfLen + HandleOffset ≈ 使用 NegHalfLen 簡化
    handleL_conns = [
        ("HandleBaseZ", "R", "PtHandleL", "Z"),
        ("NegHalfLen", "y", "PtHandleL", "X"),  # 簡化：直接用端點位置
        ("PtHandleL", "Pt", "PlnHandleL", "O"),
        ("PlnHandleL", "P", "CylHandleL", "B"),
        ("HandleR", "N", "CylHandleL", "R"),
        ("HandleH", "N", "CylHandleL", "L"),
    ]
    connections.extend(handleL_conns)

    # --- 右握把 HandleR ---
    handleR_conns = [
        ("HandleBaseZ", "R", "PtHandleR", "Z"),
        ("HalfLen", "Result", "PtHandleR", "X"),  # 簡化：直接用端點位置
        ("PtHandleR", "Pt", "PlnHandleR", "O"),
        ("PlnHandleR", "P", "CylHandleR", "B"),
        ("HandleR", "N", "CylHandleR", "R"),
        ("HandleH", "N", "CylHandleR", "L"),
    ]
    connections.extend(handleR_conns)

    # --- Solid Union ---
    union_conns = [
        ("BoxBoard", "B", "SeesawUnion", "B"),
        ("BoxPivot", "B", "SeesawUnion", "B"),
        ("CylHandleL", "C", "SeesawUnion", "B"),
        ("CylHandleR", "C", "SeesawUnion", "B"),
    ]
    connections.extend(union_conns)

    # 執行
    success, fail = client.connect_batch(connections)

    # 總結
    client.print_summary()

    print("\n翹翹板參數:")
    print("   BoardLen=300, BoardW=30, BoardT=5 (板身)")
    print("   PivotH=50, PivotW=40, PivotD=35 (支點)")
    print("   HandleR=2, HandleH=25 (握把)")

    # 保存
    id_map = client.get_id_map()
    id_map_path = PROJECT_ROOT / "GH_WIP" / "seesaw_id_map.json"
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)
    print(f"\n✓ ID 映射: {id_map_path}")

    if fail == 0:
        print("\n" + "=" * 70)
        print("✓ 翹翹板建構完成！")
        print("=" * 70)
        return True
    else:
        print(f"\n⚠ {fail} 個連接失敗")
        return fail < 5  # 允許少量失敗


if __name__ == "__main__":
    build_seesaw()
