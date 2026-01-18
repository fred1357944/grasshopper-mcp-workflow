#!/usr/bin/env python3
"""
工業設計水杯 - 使用 Agent Orchestrator 設計

設計特點:
- 簡潔的圓柱形杯身
- 微微內收的腰線（符合人體工學）
- 平底設計，穩定性佳
- 可參數化調整高度、直徑、腰線位置
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.langgraph.core.integration import GHOrchestrator


async def design_cup():
    """設計工業風水杯"""
    print("=" * 60)
    print("工業設計水杯 - Grasshopper 參數化建模")
    print("=" * 60)

    # 初始化 Orchestrator
    gh_orch = GHOrchestrator.create()

    # 設計任務清單
    design_tasks = [
        {
            "task": "建立杯身底部圓形輪廓",
            "stage": "decomposition",
            "component_type": "Circle",
        },
        {
            "task": "建立杯身頂部圓形輪廓",
            "stage": "decomposition",
            "component_type": "Circle",
        },
        {
            "task": "建立腰線位置的內收圓形",
            "stage": "decomposition",
            "component_type": "Circle",
        },
        {
            "task": "使用 Loft 連接三個圓形成杯身",
            "stage": "connectivity",
            "component_type": "Loft",
        },
        {
            "task": "連接 Number Slider 控制杯身高度",
            "stage": "connectivity",
            "component_type": "Number Slider",
        },
        {
            "task": "連接 Number Slider 控制底部直徑",
            "stage": "connectivity",
            "component_type": "Number Slider",
        },
    ]

    print("\n設計階段分析:")
    print("-" * 60)

    results = []
    for i, task_info in enumerate(design_tasks, 1):
        task = task_info["task"]
        stage = task_info["stage"]
        comp = task_info.get("component_type", "")

        print(f"\n[{i}/{len(design_tasks)}] {task}")

        # 使用 Orchestrator 分析
        result = await gh_orch.execute(
            task=task,
            stage=stage,
            component_type=comp
        )

        print(f"    層級: {result.level_used.name}")
        print(f"    信心度: {result.confidence:.2f}")
        print(f"    狀態: {'✓ 自動處理' if result.success else '⚠ 需確認'}")

        results.append({
            "task": task,
            "result": result,
        })

    # 統計
    auto_count = sum(1 for r in results if r["result"].success)
    manual_count = len(results) - auto_count

    print("\n" + "=" * 60)
    print("設計分析總結")
    print("=" * 60)
    print(f"  自動處理: {auto_count}/{len(results)}")
    print(f"  需要確認: {manual_count}/{len(results)}")

    # 獲取連接建議
    print("\n相關連接建議:")
    print("-" * 60)

    key_components = ["Circle", "Loft", "Move"]
    for comp in key_components:
        suggestions = gh_orch.get_connection_suggestions(comp)
        if suggestions:
            print(f"\n  {comp}:")
            for s in suggestions[:3]:
                print(f"    - {s['pattern']} (freq: {s['frequency']})")

    return results


# 生成 Mermaid 檔案
def generate_mermaid_files():
    """生成設計文件"""

    # part_info.mmd - 幾何分解
    part_info = """graph TD
    subgraph 杯身主體["Cup Body"]
        底圓["底部圓 (Bottom Circle)"]
        腰圓["腰線圓 (Waist Circle)"]
        頂圓["頂部圓 (Top Circle)"]
        杯身曲面["杯身曲面 (Body Surface)"]
    end

    subgraph 參數控制["Parameters"]
        高度["高度 Height: 120mm"]
        底徑["底部直徑 Bottom Ø: 70mm"]
        頂徑["頂部直徑 Top Ø: 80mm"]
        腰徑["腰線直徑 Waist Ø: 65mm"]
        腰位["腰線位置 Waist H: 40mm"]
    end

    高度 --> 頂圓
    底徑 --> 底圓
    頂徑 --> 頂圓
    腰徑 --> 腰圓
    腰位 --> 腰圓

    底圓 --> 杯身曲面
    腰圓 --> 杯身曲面
    頂圓 --> 杯身曲面
"""

    # component_info.mmd - 組件對應
    component_info = """graph LR
    subgraph 輸入參數["Input Parameters"]
        H_Slider["Number Slider (Height)"]
        D_Bottom["Number Slider (Bottom Ø)"]
        D_Top["Number Slider (Top Ø)"]
        D_Waist["Number Slider (Waist Ø)"]
        H_Waist["Number Slider (Waist H)"]
    end

    subgraph 幾何構建["Geometry Construction"]
        Pt_Origin["Construct Point (Origin)"]
        Pt_Waist["Construct Point (Waist)"]
        Pt_Top["Construct Point (Top)"]

        Plane_Bottom["XY Plane"]
        Plane_Waist["XY Plane (Waist)"]
        Plane_Top["XY Plane (Top)"]

        Circle_Bottom["Circle (Bottom)"]
        Circle_Waist["Circle (Waist)"]
        Circle_Top["Circle (Top)"]

        Loft["Loft"]
        Cap["Cap Holes"]
    end

    subgraph 輸出["Output"]
        Preview["Custom Preview"]
        Bake["Bake (optional)"]
    end

    %% 連接
    H_Slider --> Pt_Waist
    H_Slider --> Pt_Top
    H_Waist --> Pt_Waist

    D_Bottom --> Circle_Bottom
    D_Waist --> Circle_Waist
    D_Top --> Circle_Top

    Pt_Origin --> Plane_Bottom
    Pt_Waist --> Plane_Waist
    Pt_Top --> Plane_Top

    Plane_Bottom --> Circle_Bottom
    Plane_Waist --> Circle_Waist
    Plane_Top --> Circle_Top

    Circle_Bottom --> Loft
    Circle_Waist --> Loft
    Circle_Top --> Loft

    Loft --> Cap
    Cap --> Preview
"""

    # 寫入檔案
    output_dir = PROJECT_ROOT / "GH_WIP"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "cup_part_info.mmd", "w", encoding="utf-8") as f:
        f.write(part_info)
    print(f"\n✓ 已生成: {output_dir / 'cup_part_info.mmd'}")

    with open(output_dir / "cup_component_info.mmd", "w", encoding="utf-8") as f:
        f.write(component_info)
    print(f"✓ 已生成: {output_dir / 'cup_component_info.mmd'}")

    # placement_info.json
    placement_info = {
        "name": "Industrial Design Cup",
        "description": "簡約工業風水杯 - 參數化設計",
        "parameters": {
            "height": {"value": 120, "min": 80, "max": 200, "unit": "mm"},
            "bottom_diameter": {"value": 70, "min": 50, "max": 100, "unit": "mm"},
            "top_diameter": {"value": 80, "min": 50, "max": 120, "unit": "mm"},
            "waist_diameter": {"value": 65, "min": 40, "max": 90, "unit": "mm"},
            "waist_height": {"value": 40, "min": 20, "max": 80, "unit": "mm"},
        },
        "components": [
            {"type": "Number Slider", "nickname": "Height", "value": 120},
            {"type": "Number Slider", "nickname": "BottomD", "value": 70},
            {"type": "Number Slider", "nickname": "TopD", "value": 80},
            {"type": "Number Slider", "nickname": "WaistD", "value": 65},
            {"type": "Number Slider", "nickname": "WaistH", "value": 40},
            {"type": "Construct Point", "nickname": "Origin"},
            {"type": "Construct Point", "nickname": "WaistPt"},
            {"type": "Construct Point", "nickname": "TopPt"},
            {"type": "XY Plane", "nickname": "PlnBottom"},
            {"type": "XY Plane", "nickname": "PlnWaist"},
            {"type": "XY Plane", "nickname": "PlnTop"},
            {"type": "Circle", "nickname": "CircleBottom"},
            {"type": "Circle", "nickname": "CircleWaist"},
            {"type": "Circle", "nickname": "CircleTop"},
            {"type": "Loft", "nickname": "CupBody"},
            {"type": "Cap Holes", "nickname": "CapBottom"},
        ],
        "connections": [
            {"from": "Height", "from_param": "N", "to": "TopPt", "to_param": "Z"},
            {"from": "WaistH", "from_param": "N", "to": "WaistPt", "to_param": "Z"},
            {"from": "BottomD", "from_param": "N", "to": "CircleBottom", "to_param": "R"},
            {"from": "WaistD", "from_param": "N", "to": "CircleWaist", "to_param": "R"},
            {"from": "TopD", "from_param": "N", "to": "CircleTop", "to_param": "R"},
            {"from": "PlnBottom", "from_param": "P", "to": "CircleBottom", "to_param": "P"},
            {"from": "PlnWaist", "from_param": "P", "to": "CircleWaist", "to_param": "P"},
            {"from": "PlnTop", "from_param": "P", "to": "CircleTop", "to_param": "P"},
            {"from": "WaistPt", "from_param": "Pt", "to": "PlnWaist", "to_param": "O"},
            {"from": "TopPt", "from_param": "Pt", "to": "PlnTop", "to_param": "O"},
            {"from": "CircleBottom", "from_param": "C", "to": "CupBody", "to_param": "C"},
            {"from": "CircleWaist", "from_param": "C", "to": "CupBody", "to_param": "C"},
            {"from": "CircleTop", "from_param": "C", "to": "CupBody", "to_param": "C"},
            {"from": "CupBody", "from_param": "L", "to": "CapBottom", "to_param": "B"},
        ],
    }

    import json
    with open(output_dir / "cup_placement_info.json", "w", encoding="utf-8") as f:
        json.dump(placement_info, f, indent=2, ensure_ascii=False)
    print(f"✓ 已生成: {output_dir / 'cup_placement_info.json'}")


if __name__ == "__main__":
    # 執行設計分析
    asyncio.run(design_cup())

    # 生成 Mermaid 檔案
    generate_mermaid_files()

    print("\n" + "=" * 60)
    print("設計完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 查看 GH_WIP/cup_part_info.mmd - 幾何分解")
    print("2. 查看 GH_WIP/cup_component_info.mmd - 組件對應")
    print("3. 使用 GH MCP 執行 cup_placement_info.json")
