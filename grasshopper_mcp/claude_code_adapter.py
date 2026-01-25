#!/usr/bin/env python3
"""
Claude Code Adapter - 在 Claude Code 環境中執行 GH_MCP Workflow
================================================================

這個模組讓 WorkflowExecutor 可以在 Claude Code 對話中執行，
使用 AskUserQuestion 工具進行使用者交互。

設計理念：
- 將使用者交互抽象為 callback 函數
- 在 Claude Code 中，這些 callback 會被 AskUserQuestion 工具取代
- 在未來的 Web UI 中，可以換成 HTTP 請求

Usage (在 Claude Code 對話中):
    # Claude 會執行這段程式碼，並在需要時使用 AskUserQuestion
    from grasshopper_mcp.claude_code_adapter import GrasshopperWorkflow

    workflow = GrasshopperWorkflow()
    result = await workflow.run("做一個 WASP 立方體聚集")

2026-01-24
"""

import json
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pathlib import Path
from enum import Enum

from .workflow_executor_v2 import (
    WorkflowExecutor,
    ExecutionMode,
    ExecutionResult,
    RouterDecision,
    ValidationResult,
    RiskLevel
)


class InteractionType(Enum):
    """交互類型"""
    CONFIRM_REFERENCE = "confirm_reference"      # 確認使用參考配置
    MODIFY_PARAMS = "modify_params"              # 修改參數
    CONFIRM_VALIDATION = "confirm_validation"    # 確認驗證結果
    CONFIRM_EXECUTE = "confirm_execute"          # 確認執行
    REPORT_RESULT = "report_result"              # 報告結果


@dataclass
class InteractionRequest:
    """交互請求"""
    type: InteractionType
    title: str
    message: str
    options: List[Dict[str, str]] = field(default_factory=list)
    data: Optional[Dict] = None
    allow_custom_input: bool = False


@dataclass
class InteractionResponse:
    """交互回應"""
    choice: str  # 選項 ID 或自訂輸入
    custom_input: Optional[str] = None


class GrasshopperWorkflow:
    """
    Grasshopper 工作流程 - Claude Code 版本

    這個類別封裝了 WorkflowExecutor，並提供：
    1. 友善的交互介面（會生成 AskUserQuestion 格式）
    2. 狀態追蹤和報告
    3. 錯誤處理和重試機制

    使用方式：
        workflow = GrasshopperWorkflow()

        # 方式 1：完全自動（用於測試）
        result = await workflow.run("WASP cube", auto_mode=True)

        # 方式 2：交互模式（在 Claude Code 中）
        result = await workflow.run("WASP cube", auto_mode=False)
        # Claude 會在適當時機使用 AskUserQuestion
    """

    def __init__(
        self,
        reference_library_path: str = "reference_library",
        config_dir: str = "config",
        wip_dir: str = "GH_WIP"
    ):
        self.ref_path = Path(reference_library_path)
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)

        # 狀態
        self.current_request: Optional[str] = None
        self.current_config: Optional[Dict] = None
        self.interaction_log: List[Dict] = []

        # 初始化 executor
        self._executor: Optional[WorkflowExecutor] = None

    def _get_executor(self, auto_mode: bool = False) -> WorkflowExecutor:
        """取得或創建 executor"""
        return WorkflowExecutor(
            reference_library_path=str(self.ref_path),
            auto_confirm=auto_mode
        )

    async def run(
        self,
        request: str,
        auto_mode: bool = False,
        modifications: Optional[Dict] = None
    ) -> Dict:
        """
        執行工作流程

        Args:
            request: 使用者請求（如「做一個 WASP 立方體聚集」）
            auto_mode: 自動模式（不需要使用者確認）
            modifications: 預設的參數修改

        Returns:
            執行結果字典，包含：
            - success: 是否成功
            - mode: 執行模式 (reference/workflow/meta_agent)
            - config: 使用的配置
            - interactions: 交互記錄
            - next_action: 建議的下一步操作
        """
        self.current_request = request
        self.interaction_log = []

        executor = self._get_executor(auto_mode)

        # 執行 routing
        decision = executor.router.route(request)

        result = {
            "success": False,
            "request": request,
            "mode": decision.mode.value,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "config": None,
            "interactions": [],
            "next_action": None
        }

        # 根據模式處理
        if decision.mode == ExecutionMode.REFERENCE:
            return await self._handle_reference_mode(executor, decision, auto_mode, modifications)
        elif decision.mode == ExecutionMode.WORKFLOW:
            return await self._handle_workflow_mode(executor, decision, auto_mode)
        else:
            return await self._handle_meta_agent_mode(executor, decision, auto_mode)

    async def _handle_reference_mode(
        self,
        executor: WorkflowExecutor,
        decision: RouterDecision,
        auto_mode: bool,
        modifications: Optional[Dict] = None
    ) -> Dict:
        """處理 Reference 模式"""

        reference = decision.reference
        if not reference:
            return self._error_result("找不到參考配置")

        # 載入配置
        config_path = Path(reference["path"])
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            return self._error_result(f"載入配置失敗: {e}")

        self.current_config = config
        meta = config.get("_meta", {})

        # === 生成確認交互 ===
        interaction = self._build_reference_confirm_interaction(reference, config)
        self.interaction_log.append(interaction)

        # 如果不是自動模式，返回交互請求
        if not auto_mode:
            return {
                "success": True,
                "status": "awaiting_confirmation",
                "request": self.current_request,
                "mode": "reference",
                "reference_name": reference["name"],
                "confidence": reference["confidence"],
                "interaction": interaction,
                "config_preview": self._build_config_preview(config),
                "next_action": "請使用 AskUserQuestion 詢問使用者選擇"
            }

        # 自動模式：直接繼續
        return await self._continue_with_config(executor, config, auto_mode, modifications)

    async def _continue_with_config(
        self,
        executor: WorkflowExecutor,
        config: Dict,
        auto_mode: bool,
        modifications: Optional[Dict] = None
    ) -> Dict:
        """繼續執行配置"""

        # 應用修改
        if modifications:
            config = self._apply_modifications(config, modifications)

        # === Phase: Pre-Check ===
        pre_check = executor.pre_checker.check(config)

        if not pre_check.passed:
            return {
                "success": False,
                "status": "pre_check_failed",
                "mode": "reference",
                "config": config,
                "validation": {
                    "phase": "pre_check",
                    "passed": False,
                    "issues": pre_check.issues,
                    "risk_level": pre_check.risk_level.value
                },
                "next_action": "Pre-Check 失敗，需要修改配置"
            }

        # === Phase: Semantic Review ===
        semantic_result = await executor.semantic_reviewer.review(config, self.current_request or "")

        if not semantic_result.passed and not auto_mode:
            # 需要使用者確認
            interaction = self._build_validation_confirm_interaction(semantic_result)
            self.interaction_log.append(interaction)

            return {
                "success": True,
                "status": "awaiting_validation_confirm",
                "mode": "reference",
                "config": config,
                "validation": {
                    "phase": "semantic_review",
                    "passed": semantic_result.passed,
                    "issues": semantic_result.issues,
                    "risk_level": semantic_result.risk_level.value,
                    "data_flow": semantic_result.data_flow_trace
                },
                "interaction": interaction,
                "next_action": "請使用 AskUserQuestion 詢問使用者是否繼續"
            }

        # === Phase: Execute ===
        # 保存配置
        output_path = self.wip_dir / "placement_info.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "status": "ready_to_execute",
            "mode": "reference",
            "config": config,
            "config_path": str(output_path),
            "validation": {
                "pre_check": {"passed": True},
                "semantic_review": {
                    "passed": semantic_result.passed,
                    "risk_level": semantic_result.risk_level.value
                }
            },
            "execute_command": f"python -m grasshopper_tools.cli execute-placement {output_path} --clear-first",
            "next_action": "配置已準備好，可以執行部署"
        }

    async def _handle_workflow_mode(
        self,
        executor: WorkflowExecutor,
        decision: RouterDecision,
        auto_mode: bool
    ) -> Dict:
        """處理 Workflow 模式"""

        # 如果有部分匹配的 reference，嘗試使用
        if decision.reference:
            return await self._handle_reference_mode(executor, decision, auto_mode)

        return {
            "success": False,
            "status": "no_reference",
            "mode": "workflow",
            "scores": decision.scores,
            "next_action": "沒有匹配的參考配置，需要使用 /grasshopper 命令進行完整設計流程"
        }

    async def _handle_meta_agent_mode(
        self,
        executor: WorkflowExecutor,
        decision: RouterDecision,
        auto_mode: bool
    ) -> Dict:
        """處理 Meta-Agent 模式"""

        return {
            "success": False,
            "status": "need_clarification",
            "mode": "meta_agent",
            "reason": decision.reason,
            "scores": decision.scores,
            "partial_matches": decision.partial_matches,
            "next_action": "請求不夠明確，建議使用 AskUserQuestion 詢問更多細節"
        }

    def _build_reference_confirm_interaction(self, reference: Dict, config: Dict) -> Dict:
        """建構參考配置確認交互"""

        meta = config.get("_meta", {})
        components = config.get("components", [])
        connections = config.get("connections", [])

        return {
            "type": "confirm_reference",
            "title": f"找到參考配置: {reference['name']}",
            "message": f"""
## {reference['name']}

**信心度**: {reference['confidence']:.0%}
**描述**: {meta.get('description', '無')}

### 配置摘要
- 組件數: {len(components)}
- 連接數: {len(connections)}

### 經驗教訓
{chr(10).join(f"- {lesson}" for lesson in meta.get('lessons_learned', []))}
""",
            "options": [
                {"id": "use", "label": "使用", "description": "直接使用這個配置"},
                {"id": "modify", "label": "修改", "description": "調整參數後使用"},
                {"id": "new", "label": "新建", "description": "從頭設計新配置"}
            ],
            "ask_user_question_format": {
                "questions": [{
                    "question": f"找到參考配置「{reference['name']}」(信心度 {reference['confidence']:.0%})，要如何處理？",
                    "header": "配置選擇",
                    "options": [
                        {"label": "直接使用", "description": f"使用這個配置（{len(components)} 組件）"},
                        {"label": "修改參數", "description": "調整參數後再使用"},
                        {"label": "重新設計", "description": "不使用參考，從頭設計"}
                    ],
                    "multiSelect": False
                }]
            }
        }

    def _build_validation_confirm_interaction(self, validation: ValidationResult) -> Dict:
        """建構驗證確認交互"""

        issues_text = "\n".join(f"- {i.get('message', 'Unknown')}" for i in validation.issues)

        return {
            "type": "confirm_validation",
            "title": "語義審查發現問題",
            "message": f"""
## 語義審查結果

**風險等級**: {validation.risk_level.value}

### 發現的問題
{issues_text}

### 資料流追蹤
```mermaid
{validation.data_flow_trace or 'N/A'}
```
""",
            "options": [
                {"id": "proceed", "label": "繼續", "description": "忽略警告繼續執行"},
                {"id": "abort", "label": "取消", "description": "取消執行，修改配置"}
            ],
            "ask_user_question_format": {
                "questions": [{
                    "question": f"語義審查發現 {len(validation.issues)} 個問題（風險等級: {validation.risk_level.value}），要繼續嗎？",
                    "header": "確認執行",
                    "options": [
                        {"label": "繼續執行", "description": "忽略警告繼續"},
                        {"label": "取消", "description": "回去修改配置"}
                    ],
                    "multiSelect": False
                }]
            }
        }

    def _build_config_preview(self, config: Dict) -> Dict:
        """建構配置預覽"""

        components = config.get("components", [])
        connections = config.get("connections", [])

        # 分類組件
        sliders = [c for c in components if "Slider" in c.get("type", "")]
        others = [c for c in components if "Slider" not in c.get("type", "")]

        return {
            "total_components": len(components),
            "total_connections": len(connections),
            "sliders": [
                {
                    "name": s.get("nickname", s.get("id")),
                    "min": s.get("properties", {}).get("min"),
                    "max": s.get("properties", {}).get("max"),
                    "default": s.get("properties", {}).get("default")
                }
                for s in sliders
            ],
            "main_components": [c.get("type") for c in others[:5]],
            "customization_points": config.get("customization_points", [])
        }

    def _apply_modifications(self, config: Dict, modifications: Dict) -> Dict:
        """應用參數修改"""

        config = config.copy()
        components = config.get("components", [])

        for comp in components:
            nickname = comp.get("nickname", comp.get("id", ""))
            if nickname in modifications:
                if "properties" not in comp:
                    comp["properties"] = {}

                value = modifications[nickname]
                if isinstance(value, dict):
                    comp["properties"].update(value)
                else:
                    comp["properties"]["default"] = value
                    comp["properties"]["value"] = value

        config["_modifications"] = modifications
        return config

    def _error_result(self, message: str) -> Dict:
        """建構錯誤結果"""
        return {
            "success": False,
            "status": "error",
            "error": message,
            "next_action": "請修正錯誤後重試"
        }


# ============================================================================
# 便捷函數
# ============================================================================

async def quick_run(request: str, auto_mode: bool = True) -> Dict:
    """
    快速執行工作流程

    Usage:
        result = await quick_run("做一個 WASP 立方體聚集")
    """
    workflow = GrasshopperWorkflow()
    return await workflow.run(request, auto_mode=auto_mode)


def get_reference_index() -> List[Dict]:
    """
    取得 Reference Library 索引

    Usage:
        index = get_reference_index()
        for entry in index:
            print(f"{entry['name']} ({entry['confidence']:.0%})")
    """
    from .workflow_executor_v2 import IntegratedRouter

    router = IntegratedRouter(reference_library_path=Path("reference_library"))
    return router.reference_index.get("entries", [])


# ============================================================================
# CLI
# ============================================================================

async def main():
    """測試入口"""
    import sys

    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "做一個 WASP 立方體聚集"

    print("=" * 60)
    print("GrasshopperWorkflow 測試")
    print("=" * 60)

    workflow = GrasshopperWorkflow()
    result = await workflow.run(request, auto_mode=True)

    print("\n" + "=" * 60)
    print("結果:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
