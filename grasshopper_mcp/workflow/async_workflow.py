#!/usr/bin/env python3
"""
GH_MCP 智能設計工作流程 (Async Version)
========================================

整合 GHX Skill（知識檢索）+ Pre-Execution Checker（執行驗證）的 async 工作流程

完整流程:
    Phase 1: CLARIFY - 需求釐清
    Phase 2: RETRIEVE - 知識檢索（語義搜尋）
    Phase 3: ADAPT - 設計適配（生成修改計畫）
    Phase 3.5: QUERY - GUID 查詢
    Phase 4: CHECK - Pre-Execution 驗證
    Phase 5: EXECUTE - 執行部署
    Phase 6: ARCHIVE - 歸檔整理

Usage:
    from grasshopper_mcp.workflow.async_workflow import GHMCPWorkflow

    workflow = GHMCPWorkflow(config_dir="config")
    result = await workflow.run("幫我做一個類似日照分析的 WASP 離散設計")

Source: GHX Skill Package + GH_MCP Debug Knowledge
2026-01-24
"""

import json
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Phase(Enum):
    """工作流程階段"""
    CLARIFY = "clarify"
    RETRIEVE = "retrieve"
    ADAPT = "adapt"
    QUERY = "query"
    CHECK = "check"
    EXECUTE = "execute"
    ARCHIVE = "archive"


@dataclass
class WorkflowState:
    """工作流程狀態"""
    current_phase: Phase = Phase.CLARIFY

    # Phase 1: CLARIFY
    user_request: str = ""
    design_intent: Dict = field(default_factory=dict)
    confirmed_spec: bool = False

    # Phase 2: RETRIEVE
    similar_examples: List[Dict] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)

    # Phase 3: ADAPT
    modification_plan: Dict = field(default_factory=dict)
    component_list: List[Dict] = field(default_factory=list)

    # Phase 3.5: QUERY
    placement_info: Dict = field(default_factory=dict)

    # Phase 4: CHECK
    check_passed: bool = False
    check_report: str = ""

    # Phase 5: EXECUTE
    execution_log: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Phase 6: ARCHIVE
    output_path: Optional[str] = None


class GHMCPWorkflow:
    """
    GH_MCP 智能設計工作流程

    整合:
    - Connection Patterns: 17 個常用連接模式
    - Pre-Execution Checker: 執行前驗證 MCP/GUID/參數風險
    - Knowledge Base: trusted GUIDs + MCP commands
    """

    # 關鍵字 → 插件/模式 映射
    KEYWORDS_MAP = {
        "日照": ["Ladybug", "Solar"],
        "遮陽": ["Ladybug", "Shading"],
        "能源": ["Honeybee", "Energy"],
        "結構": ["Karamba3D", "Structural"],
        "找形": ["Kangaroo2", "Form Finding"],
        "離散": ["WASP", "Discrete"],
        "聚集": ["WASP", "Aggregation"],
        "優化": ["Galapagos", "Octopus"],
        "面板": ["Lunchbox", "Panel"],
        "細分": ["Weaverbird", "Subdivision"],
        "變形": ["Pufferfish", "Morph"],
    }

    def __init__(
        self,
        config_dir: str = "config",
        wip_dir: str = "GH_WIP"
    ):
        """
        初始化工作流程

        Args:
            config_dir: 配置目錄 (包含 trusted_guids.json, connection_patterns.json)
            wip_dir: 工作中檔案目錄
        """
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)

        self.state = WorkflowState()

        # 載入配置
        self._trusted_guids: Dict = {}
        self._connection_patterns: Dict = {}
        self._mcp_commands: Dict = {}
        self._load_configs()

        # Lazy load checker
        self._checker = None

    def _load_configs(self):
        """載入配置文件"""
        # 載入 trusted GUIDs
        guids_path = self.config_dir / "trusted_guids.json"
        if guids_path.exists():
            with open(guids_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._trusted_guids = data.get("components", {})

        # 載入連接模式
        patterns_path = self.config_dir / "connection_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._connection_patterns = data.get("patterns", {})

        # 載入 MCP 命令
        commands_path = self.config_dir / "mcp_commands.json"
        if commands_path.exists():
            with open(commands_path, 'r', encoding='utf-8') as f:
                self._mcp_commands = json.load(f)

    @property
    def checker(self):
        """Lazy load Pre-Execution Checker"""
        if self._checker is None:
            try:
                from grasshopper_mcp.pre_execution_checker import PreExecutionChecker
                self._checker = PreExecutionChecker(config_dir=self.config_dir)
            except ImportError:
                print("⚠️ Pre-Execution Checker 未安裝")
                self._checker = None
        return self._checker

    # ========== Phase 1: CLARIFY ==========

    def phase1_clarify(self, user_request: str) -> Dict:
        """
        Phase 1: 需求釐清

        分析用戶請求，提取設計意圖
        """
        self.state.current_phase = Phase.CLARIFY
        self.state.user_request = user_request

        # 提取關鍵字和意圖
        intent = self._extract_intent(user_request)
        self.state.design_intent = intent

        return {
            "phase": "CLARIFY",
            "intent": intent,
            "questions": self._generate_clarifying_questions(intent)
        }

    def _extract_intent(self, request: str) -> Dict:
        """從請求中提取設計意圖"""
        intent = {
            "raw_request": request,
            "keywords": [],
            "target_plugins": [],
            "matched_patterns": [],
            "reference_type": None,  # "similar_to", "combine", "new"
            "constraints": []
        }

        # 關鍵字匹配
        for keyword, tags in self.KEYWORDS_MAP.items():
            if keyword in request:
                intent["keywords"].append(keyword)
                intent["target_plugins"].extend(tags)

        # 去重
        intent["target_plugins"] = list(set(intent["target_plugins"]))

        # 搜尋匹配的連接模式
        for pattern_name, pattern in self._connection_patterns.items():
            pattern_keywords = pattern.get("keywords", [])
            for kw in intent["keywords"]:
                if kw.lower() in [pk.lower() for pk in pattern_keywords]:
                    if pattern_name not in intent["matched_patterns"]:
                        intent["matched_patterns"].append(pattern_name)

        # 判斷請求類型
        if "類似" in request or "像" in request:
            intent["reference_type"] = "similar_to"
        elif "結合" in request or "加上" in request:
            intent["reference_type"] = "combine"
        else:
            intent["reference_type"] = "new"

        return intent

    def _generate_clarifying_questions(self, intent: Dict) -> List[str]:
        """生成釐清問題"""
        questions = []

        if not intent["target_plugins"]:
            questions.append("需要使用哪些 Grasshopper 插件？")

        if intent["reference_type"] == "similar_to":
            questions.append("有沒有具體的參考範例或 .ghx 檔案？")

        if not intent["matched_patterns"]:
            questions.append("可以描述更具體的設計目標嗎？")

        return questions

    # ========== Phase 2: RETRIEVE ==========

    def phase2_retrieve(self) -> Dict:
        """
        Phase 2: 知識檢索

        從連接模式庫找到相關模式
        """
        self.state.current_phase = Phase.RETRIEVE

        intent = self.state.design_intent
        matched_patterns = intent.get("matched_patterns", [])

        results = {
            "phase": "RETRIEVE",
            "matched_patterns": [],
            "pattern_details": []
        }

        for pattern_name in matched_patterns:
            pattern = self._connection_patterns.get(pattern_name, {})
            if pattern:
                results["matched_patterns"].append(pattern_name)
                results["pattern_details"].append({
                    "name": pattern_name,
                    "description": pattern.get("description", ""),
                    "components": pattern.get("components", []),
                    "wiring_count": len(pattern.get("wiring", []))
                })

        self.state.matched_patterns = results["matched_patterns"]

        return results

    # ========== Phase 3: ADAPT ==========

    def phase3_adapt(self, _source_ghx: Optional[str] = None) -> Dict:
        """
        Phase 3: 設計適配

        根據匹配的模式生成組件列表
        """
        self.state.current_phase = Phase.ADAPT

        results = {
            "phase": "ADAPT",
            "component_list": [],
            "wiring_plan": []
        }

        # 如果有匹配的模式，使用模式生成組件列表
        if self.state.matched_patterns:
            pattern_name = self.state.matched_patterns[0]
            pattern = self._connection_patterns.get(pattern_name, {})

            # 收集組件
            components = set()
            for comp in pattern.get("components", []):
                components.add(comp)

            # 從 wiring 提取組件
            for wire in pattern.get("wiring", []):
                if isinstance(wire, list) and len(wire) >= 2:
                    components.add(wire[0])
                    components.add(wire[1])
                elif isinstance(wire, dict):
                    components.add(wire.get("from", ""))
                    components.add(wire.get("to", ""))

            results["component_list"] = list(components)
            results["wiring_plan"] = pattern.get("wiring", [])

        self.state.component_list = results["component_list"]

        return results

    # ========== Phase 3.5: QUERY ==========

    def phase35_query(self) -> Dict:
        """
        Phase 3.5: GUID 查詢

        從 trusted_guids.json 獲取正確 GUID，生成 placement_info.json
        """
        self.state.current_phase = Phase.QUERY

        # 生成 placement_info
        placement_info = {
            "version": "1.0",
            "design_intent": self.state.design_intent,
            "components": [],
            "connections": [],
            "mcp_calls": []
        }

        # 添加組件
        for i, comp_name in enumerate(self.state.component_list):
            comp_info = self._trusted_guids.get(comp_name, {})
            component = {
                "id": f"comp_{i}",
                "type": comp_name,
                "nickname": comp_name,
                "position": {"x": 100 + i * 150, "y": 100}
            }

            # 如果有 trusted GUID，使用它
            if "guid" in comp_info:
                component["guid"] = comp_info["guid"]

            placement_info["components"].append(component)

        # 如果有匹配的模式，添加連接
        if self.state.matched_patterns:
            pattern_name = self.state.matched_patterns[0]
            pattern = self._connection_patterns.get(pattern_name, {})

            for wire in pattern.get("wiring", []):
                if isinstance(wire, list) and len(wire) >= 4:
                    connection = {
                        "from": wire[0],
                        "to": wire[1],
                        "fromParamIndex": wire[2],
                        "toParamIndex": wire[3]
                    }
                elif isinstance(wire, dict):
                    connection = {
                        "from": wire.get("from"),
                        "to": wire.get("to"),
                        "fromParamIndex": wire.get("fromParam", 0),
                        "toParamIndex": wire.get("toParam", 0)
                    }
                else:
                    continue

                placement_info["connections"].append(connection)

        # 添加 MCP calls
        placement_info["mcp_calls"] = [
            {"command": "clear_document"},
            {"command": "add_component"},
            {"command": "set_slider_properties"},
            {"command": "set_component_value"},
            {"command": "connect_components"},
            {"command": "get_errors"}
        ]

        self.state.placement_info = placement_info

        # 保存到檔案
        output_path = self.wip_dir / "placement_info.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(placement_info, f, indent=2, ensure_ascii=False)

        return {
            "phase": "QUERY",
            "placement_info_path": str(output_path),
            "component_count": len(placement_info["components"]),
            "connection_count": len(placement_info["connections"])
        }

    # ========== Phase 4: CHECK ==========

    def phase4_check(self) -> Dict:
        """
        Phase 4: Pre-Execution Checklist

        執行前驗證
        """
        self.state.current_phase = Phase.CHECK

        results = {
            "phase": "CHECK",
            "passed": False,
            "report": ""
        }

        if self.checker:
            self.checker.check_placement_info(self.state.placement_info)
            results["report"] = self.checker.generate_report()
            results["passed"] = not self.checker.should_block_execution()
            results["critical"] = self.checker.get_critical_count()
            results["warnings"] = self.checker.get_warning_count()
        else:
            results["report"] = "⚠️ Pre-Execution Checker 未安裝，跳過驗證"
            results["passed"] = True

        self.state.check_passed = results["passed"]
        self.state.check_report = results["report"]

        return results

    # ========== Phase 5: EXECUTE ==========

    async def phase5_execute(self, mcp_client=None) -> Dict:
        """
        Phase 5: 執行部署

        實際執行 MCP 命令（需要 MCP client）
        """
        self.state.current_phase = Phase.EXECUTE

        results = {
            "phase": "EXECUTE",
            "success": False,
            "log": [],
            "errors": []
        }

        if not self.state.check_passed:
            results["errors"].append("Pre-Execution Check 未通過，無法執行")
            return results

        if mcp_client is None:
            results["log"].append("⚠️ 無 MCP client，模擬執行")
            results["log"].append("模擬: clear_document")
            for comp in self.state.placement_info.get("components", []):
                results["log"].append(f"模擬: add_component({comp['type']})")
            for conn in self.state.placement_info.get("connections", []):
                results["log"].append(
                    f"模擬: connect({conn['from']} → {conn['to']})"
                )
            results["success"] = True
        else:
            # 實際執行（需要實現 MCP client 整合）
            try:
                # await mcp_client.clear_document()
                # for comp in self.state.placement_info.get("components", []):
                #     await mcp_client.add_component(...)
                pass
            except Exception as e:
                results["errors"].append(str(e))

        self.state.execution_log = results["log"]
        self.state.errors = results["errors"]

        return results

    # ========== Phase 6: ARCHIVE ==========

    def phase6_archive(self) -> Dict:
        """
        Phase 6: 歸檔整理
        """
        self.state.current_phase = Phase.ARCHIVE

        # 保存完整狀態
        archive = {
            "user_request": self.state.user_request,
            "design_intent": self.state.design_intent,
            "matched_patterns": self.state.matched_patterns,
            "check_passed": self.state.check_passed,
            "execution_log": self.state.execution_log,
            "errors": self.state.errors
        }

        # 保存歸檔
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.wip_dir / f"archive_{timestamp}.json"

        with open(archive_path, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)

        self.state.output_path = str(archive_path)

        return {
            "phase": "ARCHIVE",
            "archive_path": str(archive_path)
        }

    # ========== Full Workflow ==========

    async def run(
        self,
        user_request: str,
        source_ghx: Optional[str] = None,
        auto_execute: bool = False
    ) -> Dict:
        """
        執行完整工作流程

        Args:
            user_request: 用戶請求
            source_ghx: 可選的參考 .ghx 檔案
            auto_execute: 是否自動執行（跳過確認）

        Returns:
            完整結果
        """
        results = {}

        # Phase 1: CLARIFY
        print("【Phase 1: CLARIFY】")
        results["clarify"] = self.phase1_clarify(user_request)
        print(f"  意圖: {self.state.design_intent.get('keywords', [])}")
        print(f"  目標插件: {self.state.design_intent.get('target_plugins', [])}")

        # Phase 2: RETRIEVE
        print("\n【Phase 2: RETRIEVE】")
        results["retrieve"] = self.phase2_retrieve()
        print(f"  匹配 {len(self.state.matched_patterns)} 個模式")

        # Phase 3: ADAPT
        print("\n【Phase 3: ADAPT】")
        results["adapt"] = self.phase3_adapt(source_ghx)
        print(f"  組件列表: {len(self.state.component_list)} 個")

        # Phase 3.5: QUERY
        print("\n【Phase 3.5: QUERY】")
        results["query"] = self.phase35_query()
        print(f"  生成 placement_info.json")

        # Phase 4: CHECK
        print("\n【Phase 4: CHECK】")
        results["check"] = self.phase4_check()
        print(self.state.check_report)

        if not self.state.check_passed:
            print("\n❌ Pre-Execution Check 未通過，流程中止")
            return results

        # Phase 5: EXECUTE
        if auto_execute:
            print("\n【Phase 5: EXECUTE】")
            results["execute"] = await self.phase5_execute()
            for log in self.state.execution_log:
                print(f"  {log}")
        else:
            print("\n【Phase 5: EXECUTE】(跳過 - 需要手動確認)")

        # Phase 6: ARCHIVE
        print("\n【Phase 6: ARCHIVE】")
        results["archive"] = self.phase6_archive()
        print(f"  歸檔: {self.state.output_path}")

        return results


# ============================================================================
# 便捷函數
# ============================================================================

def create_workflow(config_dir: str = "config", wip_dir: str = "GH_WIP") -> GHMCPWorkflow:
    """創建工作流程實例"""
    return GHMCPWorkflow(config_dir=config_dir, wip_dir=wip_dir)


# ============================================================================
# CLI
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="GH_MCP 智能設計工作流程")
    parser.add_argument("request", help="設計請求")
    parser.add_argument("--source", help="參考 .ghx 檔案")
    parser.add_argument("--config", default="config", help="配置目錄")
    parser.add_argument("--auto", action="store_true", help="自動執行")

    args = parser.parse_args()

    workflow = GHMCPWorkflow(config_dir=args.config)

    await workflow.run(
        args.request,
        source_ghx=args.source,
        auto_execute=args.auto
    )

    print("\n" + "=" * 50)
    print("完成!")


if __name__ == "__main__":
    asyncio.run(main())
