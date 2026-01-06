"""
Test: 畫桌子工作流程完整測試

測試項目：
1. 狀態初始化
2. Step 2: decomposition 節點生成 part_info.mmd
3. Step 3: connectivity 節點生成 component_info.mmd
4. 工作流程暫停等待確認機制
"""

import sys
import os
from pathlib import Path
import shutil

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.langgraph.state import create_initial_state, DesignState
from grasshopper_mcp.langgraph.nodes import (
    decompose_geometry_node,
    confirm_decomposition_node,
    plan_connectivity_node,
    confirm_connectivity_node,
    detect_conflicts_node,
)

# 測試目錄
GH_WIP_DIR = Path("GH_WIP")
GH_WIP_BACKUP = Path("GH_WIP_backup_test")


def setup_test():
    """備份並清理 GH_WIP"""
    print("\n=== 測試設置 ===")

    if GH_WIP_DIR.exists():
        if GH_WIP_BACKUP.exists():
            shutil.rmtree(GH_WIP_BACKUP)
        shutil.copytree(GH_WIP_DIR, GH_WIP_BACKUP)
        print(f"✓ 已備份 GH_WIP 到 {GH_WIP_BACKUP}")

        # 清空但保留目錄
        for f in GH_WIP_DIR.iterdir():
            if f.is_file():
                f.unlink()
        print("✓ 已清空 GH_WIP")
    else:
        GH_WIP_DIR.mkdir(exist_ok=True)
        print("✓ 已創建 GH_WIP")


def teardown_test(restore: bool = True):
    """恢復 GH_WIP"""
    print("\n=== 測試清理 ===")

    if restore and GH_WIP_BACKUP.exists():
        if GH_WIP_DIR.exists():
            shutil.rmtree(GH_WIP_DIR)
        shutil.copytree(GH_WIP_BACKUP, GH_WIP_DIR)
        shutil.rmtree(GH_WIP_BACKUP)
        print("✓ 已恢復 GH_WIP")


def test_1_state_initialization():
    """測試 1: 狀態初始化"""
    print("\n=== 測試 1: 狀態初始化 ===")

    state = create_initial_state(
        topic="設計一張 120x80 的桌子",
        max_iterations=3
    )

    # 驗證
    assert state["topic"] == "設計一張 120x80 的桌子", "topic 錯誤"
    assert state["current_stage"] == "requirements", "初始 stage 應為 requirements"
    assert state["max_iterations"] == 3, "max_iterations 錯誤"
    assert state["part_info_mmd"] == "", "part_info_mmd 應為空"
    assert state["component_info_mmd"] == "", "component_info_mmd 應為空"
    assert state["awaiting_confirmation"] == False, "初始不應等待確認"

    print("✓ 狀態初始化正確")
    print(f"  - session_id: {state['session_id'][:8]}...")
    print(f"  - topic: {state['topic']}")
    print(f"  - current_stage: {state['current_stage']}")

    return state


def test_2_decomposition_node(state: DesignState):
    """測試 2: decomposition 節點"""
    print("\n=== 測試 2: Decomposition 節點 ===")

    # 設置前置條件
    state["requirements"] = "設計一張桌子，桌面 120x80x5cm，4支圓形桌腳，半徑 2.5cm，高 70cm"
    state["current_stage"] = "decomposition"

    # 執行節點
    updates = decompose_geometry_node(state)
    state = {**state, **updates}

    # 驗證 1: 檔案已寫入
    part_info_path = GH_WIP_DIR / "part_info.mmd"
    assert part_info_path.exists(), f"part_info.mmd 未創建於 {part_info_path}"
    print(f"✓ 檔案已創建: {part_info_path}")

    # 驗證 2: 狀態已更新
    assert state.get("part_info_mmd"), "part_info_mmd 狀態未更新"
    assert "erDiagram" in state["part_info_mmd"], "part_info_mmd 應包含 erDiagram"
    print("✓ 狀態已更新 (part_info_mmd)")

    # 驗證 3: 等待確認
    assert state.get("awaiting_confirmation") == True, "應設置 awaiting_confirmation=True"
    assert state.get("confirmation_reason") == "part_info_preview", "confirmation_reason 錯誤"
    print("✓ 正確設置等待確認狀態")

    # 驗證 4: 決策問題已添加
    decisions = state.get("pending_decisions", [])
    assert len(decisions) > 0, "應添加決策問題"
    assert "part_info" in decisions[-1].get("question", ""), "決策問題應關於 part_info"
    print(f"✓ 已添加決策問題: {decisions[-1]['question'][:30]}...")

    # 驗證 5: 檔案內容包含桌子模板
    with open(part_info_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TABLE" in content or "桌" in content, "應使用桌子模板"
    print("✓ 正確識別桌子模板")

    # 顯示生成的內容預覽
    print("\n--- part_info.mmd 預覽 ---")
    print(content[:300] + "..." if len(content) > 300 else content)

    return state


def test_3_confirm_decomposition(state: DesignState):
    """測試 3: 用戶確認 decomposition"""
    print("\n=== 測試 3: 用戶確認 Decomposition ===")

    # 模擬用戶選擇「確認並繼續」
    for decision in state.get("pending_decisions", []):
        if "part_info" in decision.get("question", ""):
            decision["resolved"] = True
            decision["chosen_option"] = "確認並繼續"

    # 執行確認節點
    updates = confirm_decomposition_node(state)
    state = {**state, **updates}

    # 驗證
    assert state.get("awaiting_confirmation") == False, "確認後應清除 awaiting_confirmation"
    assert state.get("current_stage") == "connectivity", "確認後應進入 connectivity stage"

    print("✓ 用戶確認成功，進入 connectivity 階段")

    return state


def test_4_connectivity_node(state: DesignState):
    """測試 4: connectivity 節點"""
    print("\n=== 測試 4: Connectivity 節點 ===")

    # 執行節點
    updates = plan_connectivity_node(state)
    state = {**state, **updates}

    # 驗證 1: 檔案已寫入
    component_info_path = GH_WIP_DIR / "component_info.mmd"
    assert component_info_path.exists(), f"component_info.mmd 未創建於 {component_info_path}"
    print(f"✓ 檔案已創建: {component_info_path}")

    # 驗證 2: 狀態已更新
    assert state.get("component_info_mmd"), "component_info_mmd 狀態未更新"
    assert "flowchart" in state["component_info_mmd"], "component_info_mmd 應包含 flowchart"
    print("✓ 狀態已更新 (component_info_mmd)")

    # 驗證 3: 等待確認
    assert state.get("awaiting_confirmation") == True, "應設置 awaiting_confirmation=True"
    assert state.get("confirmation_reason") == "component_info_preview", "confirmation_reason 錯誤"
    print("✓ 正確設置等待確認狀態")

    # 驗證 4: 檔案內容包含桌面組件
    with open(component_info_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TABLE_TOP" in content or "桌面" in content, "應包含桌面組件"
    assert "Rectangle" in content or "Extrude" in content, "應包含 Grasshopper 組件"
    print("✓ 正確生成桌子組件連接圖")

    # 顯示生成的內容預覽
    print("\n--- component_info.mmd 預覽 ---")
    print(content[:500] + "..." if len(content) > 500 else content)

    return state


def test_5_detect_conflicts(state: DesignState):
    """測試 5: 衝突檢測"""
    print("\n=== 測試 5: 衝突檢測 ===")

    # 模擬用戶確認 connectivity
    for decision in state.get("pending_decisions", []):
        if "component_info" in decision.get("question", ""):
            decision["resolved"] = True
            decision["chosen_option"] = "確認並繼續"

    state["awaiting_confirmation"] = False

    # 執行衝突檢測
    updates = detect_conflicts_node(state)
    state = {**state, **updates}

    # 驗證
    errors = state.get("errors", [])
    if errors:
        print(f"⚠ 檢測到 {len(errors)} 個警告/錯誤:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✓ 無衝突檢測到")

    # 應該進入下一階段（guid_resolution）或留在 connectivity（如果有錯誤）
    print(f"✓ 當前階段: {state.get('current_stage')}")

    return state


def test_6_workflow_integration():
    """測試 6: 工作流程整合測試"""
    print("\n=== 測試 6: 工作流程整合 ===")

    from grasshopper_mcp.langgraph.graphs.iterative_workflow import create_iterative_workflow

    # 創建工作流程
    workflow = create_iterative_workflow()

    # 創建初始狀態
    # 注意：requirements 需要包含「桌子」關鍵字以跳過 clarification 決策
    state = create_initial_state(
        topic="設計一張桌子",
        max_iterations=3
    )
    state["requirements"] = "設計一張桌子：桌面 120x80cm，4支圓形桌腳，高度 70cm"

    # 運行工作流程
    print("運行 iterative workflow...")
    final_state = workflow.invoke(state)

    # 驗證
    current_stage = final_state.get('current_stage')
    awaiting = final_state.get('awaiting_confirmation')
    reason = final_state.get('confirmation_reason')

    print(f"✓ 工作流程結束於: {current_stage}")
    print(f"✓ 等待確認: {awaiting}")
    print(f"✓ 確認原因: {reason}")

    # 檢查是否正確停在 decomposition 階段等待確認
    if current_stage == "decomposition" and awaiting:
        print("✓ 正確！工作流程在 decomposition 階段暫停等待 Mermaid 預覽確認")
    elif current_stage == "connectivity" and awaiting:
        print("✓ 正確！工作流程在 connectivity 階段暫停等待確認")
    else:
        print(f"⚠ 工作流程停在 {current_stage}，awaiting={awaiting}")

    # 檢查 GH_WIP 是否有生成檔案
    if (GH_WIP_DIR / "part_info.mmd").exists():
        print("✓ GH_WIP/part_info.mmd 已生成")

    return final_state


def run_all_tests():
    """運行所有測試"""
    print("=" * 60)
    print("畫桌子工作流程測試")
    print("=" * 60)

    results = {}

    try:
        setup_test()

        # 測試序列
        state = test_1_state_initialization()
        results["test_1"] = "PASS"

        state = test_2_decomposition_node(state)
        results["test_2"] = "PASS"

        state = test_3_confirm_decomposition(state)
        results["test_3"] = "PASS"

        state = test_4_connectivity_node(state)
        results["test_4"] = "PASS"

        state = test_5_detect_conflicts(state)
        results["test_5"] = "PASS"

        # 單獨測試工作流程整合
        setup_test()  # 重新清理
        test_6_workflow_integration()
        results["test_6"] = "PASS"

    except AssertionError as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results[f"test_failed"] = str(e)
    except Exception as e:
        print(f"\n✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)
    finally:
        # 不恢復，保留測試生成的檔案以供檢查
        teardown_test(restore=False)

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r == "PASS")
    total = len([k for k in results.keys() if k.startswith("test_")])

    for test, result in results.items():
        status = "✓" if result == "PASS" else "✗"
        print(f"  {status} {test}: {result}")

    print(f"\n通過率: {passed}/{total}")

    return results


if __name__ == "__main__":
    run_all_tests()
