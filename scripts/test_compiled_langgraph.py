#!/usr/bin/env python3
"""
測試編譯後的 LangGraph 工作流程

這個腳本驗證真正的 StateGraph 實作是否正常工作。
"""

import sys
from pathlib import Path

# 確保可以導入專案模組
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_graph_build():
    """測試圖建立"""
    print("=" * 60)
    print("Test 1: Build Graph")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import build_multi_mode_graph

    graph = build_multi_mode_graph()
    print(f"Graph type: {type(graph)}")
    print(f"Graph nodes: {list(graph.nodes.keys())}")
    print("✅ Graph built successfully!")
    print()


def test_graph_compile():
    """測試圖編譯"""
    print("=" * 60)
    print("Test 2: Compile Graph")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import compile_workflow

    app = compile_workflow(interrupt_before=None)
    print(f"Compiled app type: {type(app)}")
    print("✅ Graph compiled successfully!")
    print()


def test_mermaid_visualization():
    """測試 Mermaid 可視化"""
    print("=" * 60)
    print("Test 3: Mermaid Visualization")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import get_workflow_mermaid

    mermaid = get_workflow_mermaid()
    print("Mermaid Graph:")
    print("-" * 40)
    # 只顯示前 30 行
    lines = mermaid.split('\n')[:30]
    for line in lines:
        print(line)
    if len(mermaid.split('\n')) > 30:
        print(f"... ({len(mermaid.split(chr(10)))} lines total)")
    print("-" * 40)
    print("✅ Mermaid visualization generated!")
    print()


def test_workflow_runner():
    """測試工作流程執行器"""
    print("=" * 60)
    print("Test 4: Workflow Runner (Workflow Mode)")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import CompiledWorkflowRunner

    runner = CompiledWorkflowRunner(
        use_memory=False,
        interrupt_at_human_decision=False
    )

    # 測試 Workflow 模式
    result = runner.run(
        topic="create a simple box",
        requirements="width=10, height=5"
    )

    print(f"Intent type: {result.get('intent_type')}")
    print(f"Final proposal: {result.get('final_proposal', 'N/A')[:200]}...")
    print(f"User approved: {result.get('user_approved')}")
    print("✅ Workflow mode executed!")
    print()


def test_brainstorm_mode():
    """測試 Brainstorm 模式"""
    print("=" * 60)
    print("Test 5: Brainstorm Mode")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import CompiledWorkflowRunner

    runner = CompiledWorkflowRunner(
        use_memory=False,
        interrupt_at_human_decision=False
    )

    result = runner.run(
        topic="brainstorm ideas for a parametric chair",
        requirements=""
    )

    print(f"Intent type: {result.get('intent_type')}")
    print(f"Brainstorm phase: {result.get('brainstorm_phase')}")
    print(f"Ideas count: {len(result.get('brainstorm_ideas', []))}")
    print("✅ Brainstorm mode executed!")
    print()


def test_think_partner_mode():
    """測試 Think-Partner 模式"""
    print("=" * 60)
    print("Test 6: Think-Partner Mode")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import CompiledWorkflowRunner

    runner = CompiledWorkflowRunner(
        use_memory=False,
        interrupt_at_human_decision=False
    )

    result = runner.run(
        topic="/think how should I design a modern table",
        requirements=""
    )

    print(f"Intent type: {result.get('intent_type')}")
    print(f"Thinking mode: {result.get('thinking_mode')}")
    print(f"Thinking log count: {len(result.get('thinking_log', []))}")
    print(f"Insights count: {len(result.get('thinking_insights', []))}")
    print("✅ Think-Partner mode executed!")
    print()


def test_stream_execution():
    """測試串流執行"""
    print("=" * 60)
    print("Test 7: Stream Execution")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import CompiledWorkflowRunner

    runner = CompiledWorkflowRunner(
        use_memory=False,
        interrupt_at_human_decision=False
    )

    print("Streaming events:")
    event_count = 0
    for event in runner.stream("design a chair"):
        event_count += 1
        # event 是 dict，key 是節點名，value 是輸出
        for node_name, output in event.items():
            print(f"  [{event_count}] Node: {node_name}")
            if isinstance(output, dict):
                # 只顯示一些關鍵欄位
                for key in ["intent_type", "current_stage", "brainstorm_phase"]:
                    if key in output:
                        print(f"       {key}: {output[key]}")

    print(f"Total events: {event_count}")
    print("✅ Stream execution completed!")
    print()


def test_memory_checkpoint():
    """測試記憶體 checkpoint"""
    print("=" * 60)
    print("Test 8: Memory Checkpoint")
    print("=" * 60)

    from grasshopper_mcp.langgraph.graphs.compiled_workflow import CompiledWorkflowRunner

    runner = CompiledWorkflowRunner(
        use_memory=True,
        interrupt_at_human_decision=False
    )

    # 第一次執行
    thread_id = "test-session-001"
    result1 = runner.run(
        topic="design a table",
        requirements="simple",
        thread_id=thread_id
    )
    print(f"First run - Intent: {result1.get('intent_type')}")

    # 獲取狀態
    state = runner.get_state(thread_id)
    if state:
        print(f"State snapshot available: {state is not None}")

    print("✅ Memory checkpoint working!")
    print()


def main():
    """執行所有測試"""
    print("\n" + "=" * 60)
    print("   LangGraph Compiled Workflow Tests")
    print("=" * 60 + "\n")

    tests = [
        test_graph_build,
        test_graph_compile,
        test_mermaid_visualization,
        test_workflow_runner,
        test_brainstorm_mode,
        test_think_partner_mode,
        test_stream_execution,
        test_memory_checkpoint,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("\n" + "=" * 60)
    print(f"   Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
