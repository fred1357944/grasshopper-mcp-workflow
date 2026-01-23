#!/usr/bin/env python3
"""
課堂示範：LangGraph 自動生成螺旋曲線
=====================================

這個腳本展示如何用自然語言描述設計意圖，
讓 LangGraph 自動生成 Grasshopper 參數化設計。

使用前提：
1. 開啟 Rhino + Grasshopper
2. 載入 GH_MCP.gha
3. GH_MCP Server 運行中 (port 8080)

使用方式：
    python scripts/demo_langgraph_spiral.py
    python scripts/demo_langgraph_spiral.py "創建一個參數化的波浪曲線"
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    # 預設設計意圖
    default_intent = "創建一個可調整的螺旋曲線，要能控制圈數和半徑"

    # 如果有命令列參數，使用它
    design_intent = sys.argv[1] if len(sys.argv) > 1 else default_intent

    print("=" * 60)
    print("🎓 Grasshopper LangGraph 自動設計示範")
    print("=" * 60)
    print(f"\n設計意圖: {design_intent}\n")

    # Step 1: 檢查 GH_MCP 連接
    print("Step 1: 檢查 GH_MCP 連接...")
    from grasshopper_mcp.client_optimized import quick_test
    if not quick_test():
        print("❌ 無法連接到 GH_MCP Server")
        print("   請確保:")
        print("   1. Rhino + Grasshopper 已開啟")
        print("   2. GH_MCP.gha 已載入")
        print("   3. GH_MCP Server 運行中 (port 8080)")
        return

    print("✓ GH_MCP 連接成功\n")

    # Step 2: LangGraph 生成
    print("Step 2: LangGraph 分析與生成...")
    from src.langgraph import run_generation

    result = run_generation(
        design_intent=design_intent,
        max_iterations=3,
        acceptance_threshold=0.7,
        verbose=True  # 顯示詳細過程
    )

    gh_code = result.get("gh_code", {})
    elegance_score = result.get("elegance_score", 0)

    print(f"\n✓ 生成完成")
    print(f"  - 組件數: {len(gh_code.get('components', []))}")
    print(f"  - 連接數: {len(gh_code.get('connections', []))}")
    print(f"  - 優雅度: {elegance_score:.2f}")

    # Step 3: 部署到 Grasshopper
    print("\nStep 3: 部署到 Grasshopper...")
    from src.mcp_adapter import deploy_gh_code

    deploy_result = deploy_gh_code(gh_code, debug=True)

    print(f"\n{'=' * 60}")
    print("📊 最終結果")
    print("=" * 60)
    print(f"成功: {'✓' if deploy_result.success else '✗'}")
    print(f"組件: {deploy_result.components_created}")
    print(f"連接: {deploy_result.connections_made}")

    if deploy_result.failed_connections:
        print(f"\n⚠️  失敗的連接:")
        for fc in deploy_result.failed_connections[:5]:
            print(f"   {fc}")

    print("\n🎉 請查看 Grasshopper Canvas!")
    print("   你可以調整 Slider 來改變設計參數")


if __name__ == "__main__":
    main()
