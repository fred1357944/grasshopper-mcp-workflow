"""
設計先行工作流程模組
====================

六階段互動式 Grasshopper 參數化設計：

1. 需求釐清 (Clarify) - Claude Code 對話
2. 幾何分解 (Decompose) - 生成 part_info.mmd → VSCode 預覽
3. 組件規劃 (Plan) - 生成 component_info.mmd → VSCode 預覽
4. GUID 查詢 (Query) - 更新組件 GUID
5. 執行部署 (Execute) - 部署到 Grasshopper
6. 歸檔整理 (Archive) - 移至 GH_PKG

使用方式：
    from grasshopper_mcp.workflow import DesignWorkflow, new_design

    # 開始新設計
    wf = new_design("spiral_staircase")

    # 或檢查進度
    wf.print_status()
"""

from .design_workflow import (
    DesignWorkflow,
    DesignSpec,
    WorkflowPhase,
    new_design,
    check_progress,
)

__all__ = [
    "DesignWorkflow",
    "DesignSpec",
    "WorkflowPhase",
    "new_design",
    "check_progress",
]
