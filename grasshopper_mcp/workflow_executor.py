#!/usr/bin/env python3
"""
Workflow Executor - 工作流程執行器
==================================

整合 DualModeWorkflow 與 PlacementExecutor，
提供完整的從意圖到 Grasshopper 執行的管線。

架構：
    用戶請求
        ↓
    DualModeWorkflow
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
"""

import asyncio
from typing import Dict, Optional, Callable
from pathlib import Path

from .dual_mode_workflow import DualModeWorkflow, WorkflowPhase


class WorkflowExecutor:
    """
    工作流程執行器

    整合雙軌工作流程與 Grasshopper MCP 執行
    """

    def __init__(
        self,
        config_dir: str = "config",
        wip_dir: str = "GH_WIP",
        mcp_host: str = "localhost",
        mcp_port: int = 8080,
        ghx_skill_db: Optional[str] = None
    ):
        """
        初始化執行器

        Args:
            config_dir: 配置目錄
            wip_dir: 工作目錄
            mcp_host: MCP 服務器地址
            mcp_port: MCP 服務器端口
            ghx_skill_db: GHX Skill 資料庫路徑
        """
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port

        # 初始化工作流程
        self.workflow = DualModeWorkflow(
            config_dir=str(config_dir),
            ghx_skill_db=ghx_skill_db,
            wip_dir=str(wip_dir)
        )

        # 設置執行回調
        self.workflow.on_execute = self._execute_placement
        self.workflow.on_phase_change = self._on_phase_change

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
        clear_first: bool = True,
        use_smart_layout: bool = True,
        user_callback: Optional[Callable] = None
    ) -> Dict:
        """
        執行完整工作流程

        Args:
            request: 用戶請求
            auto_execute: 是否自動執行（不詢問確認）
            clear_first: 執行前清空畫布
            use_smart_layout: 使用智能佈局
            user_callback: 用戶輸入回調

        Returns:
            工作流程結果
        """
        # 保存執行選項
        self._execute_options = {
            "clear_first": clear_first,
            "use_smart_layout": use_smart_layout
        }

        # 執行工作流程
        result = await self.workflow.run(
            request=request,
            auto_execute=auto_execute,
            user_callback=user_callback
        )

        return result

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

    async def _execute_placement(self, placement_info: Dict) -> Dict:
        """
        執行 placement_info 到 Grasshopper

        Args:
            placement_info: 部署配置

        Returns:
            執行結果
        """
        # 保存 placement_info
        placement_path = self.wip_dir / "placement_info.json"

        import json
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
    """命令行測試"""
    import sys

    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = "做一個 WASP 離散聚集"

    print("=" * 60)
    print(f"Workflow Executor 測試")
    print(f"請求: {request}")
    print("=" * 60)

    executor = WorkflowExecutor()

    # 測試連接
    print("\n測試 MCP 連接...")
    if executor.test_connection():
        print("  ✅ MCP 連接成功")
    else:
        print("  ⚠️ MCP 未連接（將使用模擬模式）")

    # 執行工作流程
    result = await executor.run(request, auto_execute=False)

    print("\n" + "=" * 60)
    print("【最終結果】")
    print(f"  模式: {result['final_state']['mode']}")
    print(f"  階段: {result['final_state']['phase']}")
    print(f"  通過: {result['final_state']['check_passed']}")


if __name__ == "__main__":
    asyncio.run(main())
