#!/usr/bin/env python3
"""
Test Agent Orchestrator

測試 Cascade + Confidence + Expert Routing 策略
"""

import asyncio
import sys
from pathlib import Path

# 添加專案路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from grasshopper_mcp.langgraph.core.integration import GHOrchestrator


async def test_orchestrator():
    """測試調度器"""
    print("=" * 60)
    print("Agent Orchestrator Test")
    print("=" * 60)

    # 建立 Orchestrator
    print("\n1. 建立 GHOrchestrator...")
    gh_orch = GHOrchestrator.create()

    stats = gh_orch.get_statistics()
    print(f"   - 嵌入向量: {stats['embeddings_loaded']}")
    print(f"   - 連接模式: {stats['patterns_loaded']}")
    print(f"   - GH 組件知識: {stats['gh_knowledge']['components']}")

    # 測試任務
    test_tasks = [
        ("連接 Number Slider 到 Box 的 X 參數", "connectivity"),
        ("建立一個 Box 組件", "decomposition"),
        ("優化 Slider 的數值範圍", "optimization"),
        ("驗證所有連接是否正確", "evaluation"),
    ]

    print("\n2. 測試任務執行...")
    print("-" * 60)

    for task, stage in test_tasks:
        print(f"\n   任務: {task}")
        print(f"   階段: {stage}")

        # 先解釋決策
        explanation = gh_orch.explain_task(task)
        print(f"   預測路徑: {explanation['predicted_path']}")
        print(f"   選擇專家: {explanation['routing']['chosen_expert']}")

        # 執行任務
        result = await gh_orch.execute(task, stage=stage)

        print(f"   結果: {'成功' if result.success else '需要人工介入'}")
        print(f"   使用層級: {result.level_used.name}")
        print(f"   信心度: {result.confidence:.2f}")
        print(f"   升級路徑: {[l.name for l in result.escalation_path]}")
        print(f"   執行時間: {result.execution_time_ms:.1f}ms")

    # 測試組件建議
    print("\n3. 測試組件建議...")
    print("-" * 60)

    test_components = ["Number Slider", "Box", "Move"]
    for comp in test_components:
        suggestions = gh_orch.suggest_components(comp, top_k=3)
        if suggestions:
            print(f"\n   與 '{comp}' 相似的組件:")
            for name, sim in suggestions:
                print(f"     - {name}: {sim:.2%}")
        else:
            print(f"\n   未找到 '{comp}' 的相似組件")

    # 測試連接建議
    print("\n4. 測試連接建議...")
    print("-" * 60)

    suggestions = gh_orch.get_connection_suggestions("Number Slider")
    if suggestions:
        print(f"\n   Number Slider 的常見連接模式:")
        for s in suggestions[:5]:
            print(f"     - {s['pattern']} (頻率: {s['frequency']})")
    else:
        print("\n   未找到連接建議")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
