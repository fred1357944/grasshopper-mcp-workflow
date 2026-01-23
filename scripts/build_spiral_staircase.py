#!/usr/bin/env python3
"""
參數化螺旋樓梯 (Spiral Staircase) - GH_MCP 建模腳本

結構示意 (Top View):

            OuterR
         _____↓_____
       ,'     .     ',
      /    ,--+--.    \
     |   ,'  | |  ',   |
     |  |  InnerR  |   |
     |   ',  | |  ,'   |
      \    '--+--'    /
       ',_____|_____,'
            Step

結構示意 (Side View):

                    ___  Step 12
               ___/
          ___/
     ___/
    |  |   ← CenterPole
    |  |
    |  |  TotalH
    |  |
    |__|
   Ground

設計參數：
- Steps: 階梯數量 (10-30)
- TotalH: 總高度 (300cm)
- OuterR: 外半徑 (150cm)
- InnerR: 內半徑/中心柱半徑 (30cm)
- Rotation: 總旋轉圈數 (1-3)
- StepT: 踏板厚度 (5cm)
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized


def build_spiral_staircase():
    """建構參數化螺旋樓梯"""
    print("=" * 70)
    print("參數化螺旋樓梯 (Spiral Staircase)")
    print("=" * 70)

    client = GH_MCP_ClientOptimized(debug=True)

    # 測試連接
    print("\n1. 測試連接...")
    if not client.test_connection():
        print("   無法連接到 GH_MCP 服務器")
        return False

    # 清空畫布
    print("\n2. 清空畫布...")
    client.clear_canvas()
    time.sleep(0.3)

    # =========================================================================
    # 參數 Sliders
    # =========================================================================
    print("\n3. 創建參數 Sliders...")

    # 創建 sliders
    client.add_slider("Steps", col=0, row=0, value=12, min_val=6, max_val=30)
    client.add_slider("TotalH", col=0, row=1, value=300, min_val=150, max_val=500)
    client.add_slider("OuterR", col=0, row=2, value=120, min_val=80, max_val=200)
    client.add_slider("InnerR", col=0, row=3, value=25, min_val=15, max_val=50)
    client.add_slider("Rotation", col=0, row=4, value=1.0, min_val=0.5, max_val=3.0)
    client.add_slider("StepT", col=0, row=5, value=5, min_val=3, max_val=10)

    time.sleep(0.3)

    # =========================================================================
    # 計算邏輯 - 產生階梯位置序列
    # =========================================================================
    print("\n4. 建立計算邏輯...")

    # Series: 產生 0, 1, 2, ..., Steps-1 的序列
    client.add_component("Series", "StepSeries", col=1, row=0)
    # 連接 Steps -> Series.Count (C)
    client.connect("Steps", "N", "StepSeries", "C")
    print("   Series: 0 to Steps-1")

    time.sleep(0.2)

    # =========================================================================
    # 極座標計算 - 角度和高度
    # =========================================================================
    print("\n5. 極座標計算...")

    # 360 度常數
    client.add_component("Number", "Num360", col=1, row=1)
    time.sleep(0.1)
    # 設置值為 360
    result = client.send_command(
        'set_slider_properties',
        id=client.components["Num360"].comp_id,
        value=360
    )

    # Rotation * 360 = 總旋轉角度
    client.add_component("Multiplication", "TotalAngle", col=2, row=1)
    client.connect("Rotation", "N", "TotalAngle", "A")
    client.connect("Num360", "N", "TotalAngle", "B")
    print("   TotalAngle = Rotation * 360")

    # TotalAngle / Steps = 每階角度
    client.add_component("Division", "AnglePerStep", col=3, row=1)
    client.connect("TotalAngle", "Result", "AnglePerStep", "A")
    client.connect("Steps", "N", "AnglePerStep", "B")
    print("   AnglePerStep = TotalAngle / Steps")

    # TotalH / Steps = 每階高度
    client.add_component("Division", "HeightPerStep", col=3, row=2)
    client.connect("TotalH", "N", "HeightPerStep", "A")
    client.connect("Steps", "N", "HeightPerStep", "B")
    print("   HeightPerStep = TotalH / Steps")

    # StepIndex * AnglePerStep = 每階的實際角度
    client.add_component("Multiplication", "StepAngles", col=4, row=0)
    client.connect("StepSeries", "S", "StepAngles", "A")
    client.connect("AnglePerStep", "Result", "StepAngles", "B")
    print("   StepAngles = Index * AnglePerStep")

    # StepIndex * HeightPerStep = 每階的實際高度
    client.add_component("Multiplication", "StepHeights", col=4, row=2)
    client.connect("StepSeries", "S", "StepHeights", "A")
    client.connect("HeightPerStep", "Result", "StepHeights", "B")
    print("   StepHeights = Index * HeightPerStep")

    time.sleep(0.3)

    # =========================================================================
    # 極座標轉直角座標
    # =========================================================================
    print("\n6. 座標轉換...")

    # 角度轉弧度
    client.add_component("Radians", "Rads", col=5, row=0)
    client.connect("StepAngles", "Result", "Rads", "D")
    print("   Radians 轉換")

    # 計算階梯中心半徑 = (OuterR + InnerR) / 2
    client.add_component("Addition", "SumRadii", col=5, row=1)
    client.connect("OuterR", "N", "SumRadii", "A")
    client.connect("InnerR", "N", "SumRadii", "B")

    client.add_component("Number", "Num2", col=5, row=2)
    time.sleep(0.1)
    client.send_command(
        'set_slider_properties',
        id=client.components["Num2"].comp_id,
        value=2
    )

    client.add_component("Division", "MidRadius", col=6, row=1)
    client.connect("SumRadii", "Result", "MidRadius", "A")
    client.connect("Num2", "N", "MidRadius", "B")
    print("   MidRadius = (OuterR + InnerR) / 2")

    # X = MidRadius * cos(Rads)
    # Y = MidRadius * sin(Rads)
    # 使用 Evaluate 組件或分開計算

    # 使用 Sin 和 Cos 組件
    client.add_component("Sine", "SinA", col=6, row=0)
    client.connect("Rads", "Radians", "SinA", "x")  # 用完整參數名 Radians

    client.add_component("Cosine", "CosA", col=6, row=2)
    client.connect("Rads", "Radians", "CosA", "x")  # 用完整參數名 Radians

    # X = MidRadius * Cos
    client.add_component("Multiplication", "Xs", col=7, row=2)
    client.connect("MidRadius", "Result", "Xs", "A")
    client.connect("CosA", "y", "Xs", "B")
    print("   X = MidRadius * cos(angle)")

    # Y = MidRadius * Sin
    client.add_component("Multiplication", "Ys", col=7, row=0)
    client.connect("MidRadius", "Result", "Ys", "A")
    client.connect("SinA", "y", "Ys", "B")
    print("   Y = MidRadius * sin(angle)")

    time.sleep(0.3)

    # =========================================================================
    # 構建階梯幾何
    # =========================================================================
    print("\n7. 構建階梯幾何...")

    # 組合成 Point (X, Y, Z)
    client.add_component("Construct Point", "StepCenters", col=8, row=1)
    client.connect("Xs", "Result", "StepCenters", "X")
    client.connect("Ys", "Result", "StepCenters", "Y")
    client.connect("StepHeights", "Result", "StepCenters", "Z")
    print("   StepCenters 點陣列")

    # 計算階梯寬度 = OuterR - InnerR
    client.add_component("Subtraction", "StepWidth", col=8, row=0)
    client.connect("OuterR", "N", "StepWidth", "A")
    client.connect("InnerR", "N", "StepWidth", "B")
    print("   StepWidth = OuterR - InnerR")

    # 創建 Center Box 作為每個階梯
    client.add_component("Center Box", "StepBoxes", col=9, row=1)
    client.connect("StepCenters", "Pt", "StepBoxes", "B")
    client.connect("StepWidth", "Result", "StepBoxes", "X")
    client.connect("StepWidth", "Result", "StepBoxes", "Y")
    client.connect("StepT", "N", "StepBoxes", "Z")
    print("   StepBoxes (Center Box)")

    # 旋轉每個階梯使其指向外
    client.add_component("Rotate", "RotatedSteps", col=10, row=1)
    client.connect("StepBoxes", "B", "RotatedSteps", "G")
    client.connect("Rads", "Radians", "RotatedSteps", "A")  # 用完整參數名 Radians
    print("   RotatedSteps (旋轉對齊)")

    time.sleep(0.3)

    # =========================================================================
    # 中心柱
    # =========================================================================
    print("\n8. 建立中心柱...")

    # 原點
    client.add_component("Construct Point", "Origin", col=8, row=3)
    # 保持預設 (0, 0, 0)

    # 中心柱 Cylinder
    client.add_component("Cylinder", "CenterPole", col=9, row=3)
    client.connect("Origin", "Pt", "CenterPole", "B")
    client.connect("InnerR", "N", "CenterPole", "R")
    client.connect("TotalH", "N", "CenterPole", "L")
    print("   CenterPole (中心柱)")

    time.sleep(0.3)

    # =========================================================================
    # 扶手 (螺旋曲線)
    # =========================================================================
    print("\n9. 建立扶手...")

    # 扶手高度 (階梯上方 90cm)
    client.add_slider("HandrailH", col=0, row=6, value=90, min_val=60, max_val=120)

    # 扶手 Z = StepHeights + HandrailH
    client.add_component("Addition", "HandrailZ", col=10, row=3)
    client.connect("StepHeights", "Result", "HandrailZ", "A")
    client.connect("HandrailH", "N", "HandrailZ", "B")

    # 外側扶手點 X = OuterR * cos
    client.add_component("Multiplication", "HandX", col=10, row=4)
    client.connect("OuterR", "N", "HandX", "A")
    client.connect("CosA", "y", "HandX", "B")

    # 外側扶手點 Y = OuterR * sin
    client.add_component("Multiplication", "HandY", col=10, row=5)
    client.connect("OuterR", "N", "HandY", "A")
    client.connect("SinA", "y", "HandY", "B")

    # 扶手點
    client.add_component("Construct Point", "HandrailPts", col=11, row=4)
    client.connect("HandX", "Result", "HandrailPts", "X")
    client.connect("HandY", "Result", "HandrailPts", "Y")
    client.connect("HandrailZ", "Result", "HandrailPts", "Z")
    print("   HandrailPts (扶手點陣列)")

    # 穿過扶手點的曲線
    client.add_component("Interpolate", "HandrailCurve", col=12, row=4)
    client.connect("HandrailPts", "Pt", "HandrailCurve", "V")
    print("   HandrailCurve (扶手曲線)")

    # 扶手管徑
    client.add_slider("PipeR", col=0, row=7, value=3, min_val=2, max_val=6)

    # Pipe
    client.add_component("Pipe", "HandrailPipe", col=13, row=4)
    client.connect("HandrailCurve", "C", "HandrailPipe", "C")
    client.connect("PipeR", "N", "HandrailPipe", "R")
    print("   HandrailPipe (扶手管)")

    time.sleep(0.3)

    # =========================================================================
    # 完成
    # =========================================================================
    print("\n" + "=" * 70)
    print(" 螺旋樓梯建構完成！")
    print("=" * 70)
    print("""
可調整的參數：
- Steps: 階梯數量 (目前 12 階)
- TotalH: 總高度 (目前 300cm)
- OuterR: 外半徑 (目前 120cm)
- InnerR: 內半徑 (目前 25cm)
- Rotation: 旋轉圈數 (目前 1 圈)
- StepT: 踏板厚度 (目前 5cm)
- HandrailH: 扶手高度 (目前 90cm)
- PipeR: 扶手管徑 (目前 3cm)

嘗試調整這些 slider 看看效果！
""")

    # 顯示統計
    client.print_summary()

    return True


if __name__ == "__main__":
    success = build_spiral_staircase()
    sys.exit(0 if success else 1)
