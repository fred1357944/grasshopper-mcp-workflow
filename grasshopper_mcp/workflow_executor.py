#!/usr/bin/env python3
"""
Workflow Executor - 工作流程執行器 (v2.0)
=========================================

整合 ReferenceFirstWorkflow + DualModeWorkflow + PlacementExecutor，
提供完整的從意圖到 Grasshopper 執行的管線。

v2.0 重大改進：
    1. 整合 ReferenceFirstWorkflow (含 LLM Semantic Review)
    2. 優先使用 Reference Mode，失敗再切換 Dual Mode
    3. 支持 LLM 語義審查

架構：
    用戶請求
        ↓
    ReferenceFirstWorkflow (v2.0)
        ├─→ Reference Search
        ├─→ Semantic Review (LLM 自我審查) ← NEW!
        └─→ Pre-Execution Check
        ↓
    [失敗/無匹配]
        ↓
    DualModeWorkflow (Fallback)
        ↓
    placement_info.json
        ↓
    PlacementExecutor
        ↓
    GrasshopperClient (MCP)
        ↓
    Rhino/Grasshopper

Usage:
    from grasshopper_mcp.workflow_executor import WorkflowExecutor

    executor = WorkflowExecutor()
    result = await executor.run("做一個 WASP 離散聚集")

    # 使用 Reference-First 模式
    result = await executor.run_reference_first("做一個 WASP 離散聚集")
"""

import asyncio
import json
from typing import Dict, Optional, Callable
from pathlib import Path

from .dual_mode_workflow import DualModeWorkflow, WorkflowPhase
from .reference_first_workflow import ReferenceFirstWorkflow, WorkflowResult


class WorkflowExecutor:
    """
    工作流程執行器 (v2.0)

    整合三種工作流程與 Grasshopper MCP 執行：
    1. ReferenceFirstWorkflow (含 LLM Semantic Review) - 優先
    2. DualModeWorkflow - Fallback
    3. 直接執行 placement_info.json

    v2.0 特性：
    - LLM 語義審查：追蹤資料流，識別「資料爆炸」風險
    - Reference-First：優先搜索已驗證配置
    - Fail-Safe Learning：成功升級 confidence，失敗記錄 lessons
    """

    def __init__(
        self,
        config_dir: str = "config",
        wip_dir: str = "GH_WIP",
        reference_library_path: str = "reference_library",
        mcp_host: str = "localhost",
        mcp_port: int = 8080,
        ghx_skill_db: Optional[str] = None
    ):
        """
        初始化執行器

        Args:
            config_dir: 配置目錄
            wip_dir: 工作目錄
            reference_library_path: Reference Library 路徑
            mcp_host: MCP 服務器地址
            mcp_port: MCP 服務器端口
            ghx_skill_db: GHX Skill 資料庫路徑
        """
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port

        # 初始化 Reference-First 工作流程 (v2.0)
        self.ref_workflow = ReferenceFirstWorkflow(
            reference_library_path=reference_library_path,
            config_dir=str(config_dir),
            wip_dir=str(wip_dir)
        )

        # 設置執行回調
        self.ref_workflow.on_execute = self._execute_placement_async

        # 初始化 Dual-Mode 工作流程 (Fallback)
        self.dual_workflow = DualModeWorkflow(
            config_dir=str(config_dir),
            ghx_skill_db=ghx_skill_db,
            wip_dir=str(wip_dir),
            reference_library_path=reference_library_path
        )

        # 設置執行回調
        self.dual_workflow.on_execute = self._execute_placement_async
        self.dual_workflow.on_phase_change = self._on_phase_change

        # PlacementExecutor (lazy load)
        self._executor = None

    @property
    def placement_executor(self):
        """Lazy load PlacementExecutor"""
        if self._executor is None:
            from grasshopper_tools import PlacementExecutor
            from grasshopper_tools.client import GrasshopperClient

            # 創建 MCP 客戶端
            client = GrasshopperClient(
                host=self.mcp_host,
                port=self.mcp_port
            )
            self._executor = PlacementExecutor(client=client)
        return self._executor

    async def run(
        self,
        request: str,
        auto_execute: bool = False,
        auto_confirm: bool = False,
        clear_first: bool = True,
        use_smart_layout: bool = True,
        prefer_reference: bool = True,
        user_callback: Optional[Callable] = None
    ) -> Dict:
        """
        執行完整工作流程（自動選擇模式）

        優先順序：
        1. Reference-First (如果有匹配)
        2. Dual-Mode (Fallback)

        Args:
            request: 用戶請求
            auto_execute: 是否自動執行（不詢問確認）
            auto_confirm: 是否自動確認 Reference
            clear_first: 執行前清空畫布
            use_smart_layout: 使用智能佈局
            prefer_reference: 優先嘗試 Reference-First 模式
            user_callback: 用戶輸入回調

        Returns:
            工作流程結果
        """
        # 保存執行選項
        self._execute_options = {
            "clear_first": clear_first,
            "use_smart_layout": use_smart_layout
        }

        result = {"mode": None, "phases": [], "success": False}

        # 優先嘗試 Reference-First 模式
        if prefer_reference:
            print("\n" + "=" * 60)
            print("【Reference-First Workflow v2.0】")
            print("=" * 60)

            ref_result = await self.ref_workflow.run(
                request=request,
                auto_confirm=auto_confirm,
                auto_execute=auto_execute
            )

            result["reference_first"] = ref_result.to_dict()

            if ref_result.success:
                result["mode"] = "reference_first"
                result["success"] = True
                result["phases"] = ref_result.phases_completed
                result["semantic_review"] = ref_result.semantic_review
                return result

            # Reference-First 未成功，檢查是否需要切換到 Design-First
            if "請使用 /grasshopper 命令" in str(ref_result.errors):
                print("\n⚠️ 無匹配 Reference，切換到 Dual-Mode...")

        # Fallback 到 Dual-Mode 工作流程
        print("\n" + "=" * 60)
        print("【Dual-Mode Workflow】")
        print("=" * 60)

        dual_result = await self.dual_workflow.run(
            request=request,
            auto_execute=auto_execute,
            auto_confirm_reference=auto_confirm,
            user_callback=user_callback
        )

        result["dual_mode"] = dual_result
        result["mode"] = dual_result.get("final_state", {}).get("mode", "dual")
        result["success"] = dual_result.get("final_state", {}).get("check_passed", False)
        result["phases"] = [p for p in dual_result.get("phases", [])]

        return result

    async def run_reference_first(
        self,
        request: str,
        auto_confirm: bool = False,
        auto_execute: bool = False,
        modifications: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        僅使用 Reference-First 模式執行（含 LLM 語義審查）

        Args:
            request: 用戶請求
            auto_confirm: 自動確認 Reference
            auto_execute: 自動執行
            modifications: 預設修改項目

        Returns:
            WorkflowResult
        """
        self._execute_options = {
            "clear_first": True,
            "use_smart_layout": True
        }

        return await self.ref_workflow.run(
            request=request,
            auto_confirm=auto_confirm,
            auto_execute=auto_execute,
            modifications=modifications
        )

    def _on_phase_change(self, phase: WorkflowPhase):
        """階段變更回調"""
        phase_names = {
            WorkflowPhase.ROUTING: "路由分析",
            WorkflowPhase.CLARIFY: "需求釐清",
            WorkflowPhase.PLAN: "組件規劃",
            WorkflowPhase.QUERY: "GUID 查詢",
            WorkflowPhase.PRE_CHECK: "預執行檢查",
            WorkflowPhase.EXECUTE: "執行部署",
            WorkflowPhase.ARCHIVE: "歸檔",
            WorkflowPhase.EXPLORE: "探索",
            WorkflowPhase.ASK: "提問",
            WorkflowPhase.SYNTHESIZE: "模式合成",
            WorkflowPhase.COMPLETE: "完成",
            WorkflowPhase.FAILED: "失敗"
        }
        print(f"\n>>> Phase: {phase_names.get(phase, phase.value)}")

    async def _execute_placement_async(self, placement_info: Dict) -> Dict:
        """異步執行回調（供 ReferenceFirstWorkflow 使用）"""
        return await asyncio.to_thread(self._execute_placement_sync, placement_info)

    def _execute_placement_sync(self, placement_info: Dict) -> Dict:
        """
        執行 placement_info 到 Grasshopper

        Args:
            placement_info: 部署配置

        Returns:
            執行結果
        """
        # 保存 placement_info
        placement_path = self.wip_dir / "placement_info.json"

        with open(placement_path, 'w', encoding='utf-8') as f:
            json.dump(placement_info, f, indent=2, ensure_ascii=False)

        # 執行
        options = getattr(self, '_execute_options', {})
        result = self.placement_executor.execute_placement_info(
            json_path=str(placement_path),
            clear_first=options.get("clear_first", True),
            use_smart_layout=options.get("use_smart_layout", True),
            save_id_map=True,
            id_map_path=str(self.wip_dir / "component_id_map.json")
        )

        return result

    def execute_from_file(
        self,
        json_path: str,
        clear_first: bool = True,
        use_smart_layout: bool = True
    ) -> Dict:
        """
        直接從 JSON 檔案執行（跳過工作流程）

        Args:
            json_path: placement_info.json 路徑
            clear_first: 執行前清空畫布
            use_smart_layout: 使用智能佈局

        Returns:
            執行結果
        """
        return self.placement_executor.execute_placement_info(
            json_path=json_path,
            clear_first=clear_first,
            use_smart_layout=use_smart_layout,
            save_id_map=True
        )

    def test_connection(self) -> bool:
        """
        測試 MCP 連接

        Returns:
            True 如果連接成功
        """
        from grasshopper_tools.client import GrasshopperClient
        client = GrasshopperClient(host=self.mcp_host, port=self.mcp_port)

        try:
            response = client.send_command("ping")
            return response.get("success", False)
        except Exception:
            return False


# ============================================================================
# 便捷函數
# ============================================================================

def create_executor(
    config_dir: str = "config",
    mcp_host: str = "localhost",
    mcp_port: int = 8080
) -> WorkflowExecutor:
    """創建執行器實例"""
    return WorkflowExecutor(
        config_dir=config_dir,
        mcp_host=mcp_host,
        mcp_port=mcp_port
    )


async def run_request(request: str, **kwargs) -> Dict:
    """快速執行請求"""
    executor = create_executor()
    return await executor.run(request, **kwargs)


# ============================================================================
# CLI
# ============================================================================

async def main():
    """命令行測試 v2.0"""
    import sys

    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = "做一個 WASP 離散聚集"

    print("=" * 60)
    print(f"Workflow Executor v2.0 測試")
    print(f"請求: {request}")
    print("=" * 60)

    executor = WorkflowExecutor()

    # 測試連接
    print("\n測試 MCP 連接...")
    if executor.test_connection():
        print("  ✅ MCP 連接成功")
    else:
        print("  ⚠️ MCP 未連接（將使用模擬模式）")

    # 執行工作流程（優先 Reference-First）
    result = await executor.run(
        request,
        auto_execute=False,
        prefer_reference=True
    )

    print("\n" + "=" * 60)
    print("【最終結果】")
    print(f"  模式: {result.get('mode', 'unknown')}")
    print(f"  成功: {result.get('success', False)}")
    print(f"  階段: {result.get('phases', [])}")

    # 顯示語義審查結果（如果有）
    if result.get("semantic_review"):
        print("\n【語義審查摘要】")
        review = result["semantic_review"]
        # 只顯示結論部分
        if "結論" in review:
            conclusion_start = review.find("結論")
            print(f"  {review[conclusion_start:conclusion_start+50]}...")


if __name__ == "__main__":
    asyncio.run(main())
