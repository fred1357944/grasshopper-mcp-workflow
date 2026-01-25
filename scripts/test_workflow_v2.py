#!/usr/bin/env python3
"""
WorkflowExecutor v2.1 統一測試入口
===================================

測試：
1. 兩階段 Router（Reference Match + 三維評估）
2. 優化驗證順序（Pre-Check → Semantic Review）
3. Reference-First + Dual-Mode 統一入口

Usage:
    python scripts/test_workflow_v2.py
    python scripts/test_workflow_v2.py "做一個 WASP 立方體聚集"
"""

import asyncio
import sys
from pathlib import Path

# 確保可以導入專案模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.workflow_executor_v2 import WorkflowExecutor, ExecutionMode


async def run_tests(test_cases: list[str] | None = None):
    """執行測試"""

    default_tests = [
        "做一個 WASP 立方體聚集",      # 應該匹配 Golden Config
        "WASP cube aggregation",          # 英文版
        "做一個 Karamba 結構分析",      # 應該進入 Meta-Agent（無 Golden）
        "做個東西",                       # 意圖不明確
    ]

    test_cases = test_cases or default_tests

    print("=" * 70)
    print(" WorkflowExecutor v2.1 測試")
    print("=" * 70)

    executor = WorkflowExecutor(
        reference_library_path="reference_library",
        auto_confirm=True
    )

    # 顯示索引
    print("\n📚 Reference Library 索引:")
    for entry in executor.router.reference_index.get("entries", []):
        status = "❌ deprecated" if entry.get("deprecated") else "⭐ preferred" if entry.get("preferred") else "  normal"
        print(f"  [{status}] {entry['name']} ({entry['confidence']*100:.0f}%)")

    print("\n" + "=" * 70)

    # 測試統計
    results = []

    for request in test_cases:
        print(f"\n{'─' * 70}")

        try:
            result = await executor.run(request)
            results.append({
                "request": request,
                "success": result.success,
                "mode": result.mode.value,
                "phase": result.phase.value,
                "errors": result.errors
            })
        except Exception as e:
            results.append({
                "request": request,
                "success": False,
                "mode": "error",
                "phase": "error",
                "errors": [str(e)]
            })

    # 總結
    print("\n" + "=" * 70)
    print(" 測試總結")
    print("=" * 70)

    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"{status} {r['request'][:30]:<30} → {r['mode']:<12} ({r['phase']})")
        if r["errors"]:
            for err in r["errors"][:2]:
                print(f"   └─ {err[:60]}")

    # 驗證順序測試
    print("\n" + "─" * 70)
    print(" 驗證順序測試")
    print("─" * 70)

    # 測試有語法錯誤的配置
    bad_config = {
        "components": [
            {
                "id": "mesh_box",
                "type": "Mesh Box",
                "nickname": "MeshBox",
                "properties": {
                    "X": 20,  # 超過閾值
                    "Y": 20,
                    "Z": 20
                }
            }
        ],
        "connections": []
    }

    pre_check = executor.pre_checker.check(bad_config)
    print(f"Pre-Check (語法) 攔截高細分 Mesh Box:")
    print(f"  通過: {pre_check.passed}")
    print(f"  風險: {pre_check.risk_level.value}")
    if pre_check.issues:
        print(f"  問題: {pre_check.issues[0].get('message', '')[:60]}")

    if not pre_check.passed:
        print(f"  ✅ 語法檢查成功攔截，無需消耗 tokens 做語義審查")

    print("\n" + "=" * 70)
    success_count = sum(1 for r in results if r["success"])
    print(f" 成功: {success_count}/{len(results)}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(run_tests([" ".join(sys.argv[1:])]))
    else:
        asyncio.run(run_tests())
