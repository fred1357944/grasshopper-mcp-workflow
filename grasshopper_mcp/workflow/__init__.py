"""
設計先行工作流程模組
====================

兩種工作流程：

1. DesignWorkflow - 六階段同步互動式設計
   - 需求釐清 (Clarify) - Claude Code 對話
   - 幾何分解 (Decompose) - 生成 part_info.mmd → VSCode 預覽
   - 組件規劃 (Plan) - 生成 component_info.mmd → VSCode 預覽
   - GUID 查詢 (Query) - 更新組件 GUID
   - 執行部署 (Execute) - 部署到 Grasshopper
   - 歸檔整理 (Archive) - 移至 GH_PKG

2. GHMCPWorkflow - 七階段 async 智能工作流程
   - CLARIFY - 需求釐清
   - RETRIEVE - 知識檢索（語義搜尋連接模式）
   - ADAPT - 設計適配
   - QUERY - GUID 查詢
   - CHECK - Pre-Execution 驗證
   - EXECUTE - 執行部署
   - ARCHIVE - 歸檔整理

使用方式：
    # 同步版
    from grasshopper_mcp.workflow import DesignWorkflow, new_design
    wf = new_design("spiral_staircase")
    wf.print_status()

    # Async 版
    from grasshopper_mcp.workflow import GHMCPWorkflow, create_workflow
    workflow = create_workflow()
    result = await workflow.run("設計一個 WASP 離散聚集")

Source: GHX Skill Package + GH_MCP Debug Knowledge
"""

from .design_workflow import (
    DesignWorkflow,
    DesignSpec,
    WorkflowPhase,
    new_design,
    check_progress,
)

from .async_workflow import (
    GHMCPWorkflow,
    WorkflowState,
    Phase,
    create_workflow,
)

__all__ = [
    # Sync workflow
    "DesignWorkflow",
    "DesignSpec",
    "WorkflowPhase",
    "new_design",
    "check_progress",
    # Async workflow
    "GHMCPWorkflow",
    "WorkflowState",
    "Phase",
    "create_workflow",
]
