#!/usr/bin/env python3
"""
Pre-Execution Checker - 執行前驗證器
=====================================

在 Phase 3.5 (QUERY) 完成後、Phase 4 (EXECUTE) 前自動執行。
解決 Claude 長對話 compaction 導致的知識遺忘問題。

核心驗證項目：
1. MCP 命令是否可用
2. 組件 GUID 是否可信（避免插件衝突）
3. 連接參數是否有 FuzzyMatcher 風險
4. Slider/Panel 是否有初始值
5. 連接完整性驗證

使用方式：
```python
from grasshopper_mcp.pre_execution_checker import PreExecutionChecker

checker = PreExecutionChecker()
with open('GH_WIP/placement_info.json') as f:
    config = json.load(f)

results = checker.check_placement_info(config)
print(checker.generate_report())
```

Source: GHX Skill Package + GH_MCP Debug Knowledge
2026-01-24
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Union
from enum import Enum


class Severity(Enum):
    """驗證結果嚴重度"""
    CRITICAL = "critical"  # 阻擋執行
    WARNING = "warning"    # 建議修復
    INFO = "info"          # 參考資訊


class Category(Enum):
    """驗證類別"""
    MCP = "mcp"           # MCP 命令問題
    GUID = "guid"         # 組件 GUID 問題
    PARAM = "param"       # 參數名風險
    VALUE = "value"       # 初始值問題
    CONNECTION = "connection"  # 連接問題


@dataclass
class CheckResult:
    """驗證結果"""
    passed: bool
    category: Union[Category, str]  # Category enum 或 string
    severity: Union[Severity, str]  # Severity enum 或 string
    message: str
    component_id: Optional[str] = None
    suggestion: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """轉換為字典"""
        cat = self.category.value if isinstance(self.category, Category) else self.category
        sev = self.severity.value if isinstance(self.severity, Severity) else self.severity
        return {
            'passed': self.passed,
            'category': cat,
            'severity': sev,
            'message': self.message,
            'component_id': self.component_id,
            'suggestion': self.suggestion,
            'details': self.details
        }


@dataclass
class CheckerConfig:
    """驗證器配置"""
    # FuzzyMatcher 高風險參數（大小寫）
    fuzzy_risk_params: Set[str] = field(default_factory=lambda: {
        'R', 'r',           # Radius / Result / Rules / Rotation
        'N', 'n',           # Number / Normal / Name
        'P', 'p',           # Point / Plane / Parameter
        'C', 'c',           # Curve / Count / Color
        'V', 'v',           # Vector / Value / Vertices
        'GEO', 'geo',       # Geometry
        'CEN', 'cen',       # Center
        'UP', 'up',         # Up Vector
    })

    # 已知衝突組件（需要使用 trusted GUID）
    conflict_components: Set[str] = field(default_factory=lambda: {
        "Rotate", "Pipe", "Series", "Line", "Point", "Circle", "Move", "Scale"
    })

    # 必須有初始值的組件類型
    require_value_types: Set[str] = field(default_factory=lambda: {"Panel", "Text Panel", "Markdown"})

    # 建議有初始值的組件類型
    suggest_value_types: Set[str] = field(default_factory=lambda: {"Number Slider"})

    # MCP 命令定義
    mcp_available: Set[str] = field(default_factory=lambda: {
        'add_component',
        'connect_components',
        'set_slider_properties',
        'set_component_value',
        'get_component_candidates',
        'get_errors',
        'clear_document',
        'get_document_info',
        'delete_component',
        'disconnect_components',
    })

    mcp_unavailable: Dict[str, str] = field(default_factory=lambda: {
        'clear_canvas': '使用 clear_document 或用戶手動 Ctrl+A → Delete',
        'new_document': '用戶手動 File → New Document',
        'get_all_components': '使用 get_document_info 獲取組件列表',
        'select_all': '用戶手動 Ctrl+A',
        'delete_selected': '用戶手動 Delete 鍵',
        'copy_components': '用戶手動 Ctrl+C',
        'paste_components': '用戶手動 Ctrl+V',
        'undo': '用戶手動 Ctrl+Z',
        'redo': '用戶手動 Ctrl+Y',
    })


class PreExecutionChecker:
    """
    執行前驗證器

    在部署到 Grasshopper 前驗證 placement_info.json，
    提前發現可能的問題，避免反覆排錯。
    """

    def __init__(
        self,
        config: Optional[CheckerConfig] = None,
        config_dir: Optional[Path] = None
    ):
        """
        初始化驗證器

        Args:
            config: 驗證器配置
            config_dir: 配置目錄路徑
        """
        self.config = config or CheckerConfig()
        self.results: List[CheckResult] = []

        # 載入知識庫
        if config_dir is None:
            possible_paths = [
                Path(__file__).parent.parent / "config",
                Path.cwd() / "config",
            ]
            for p in possible_paths:
                if p.exists():
                    config_dir = p
                    break
            else:
                config_dir = possible_paths[0]

        self.config_dir = Path(config_dir)
        self._load_knowledge()

    def _load_knowledge(self):
        """載入知識庫"""
        self._trusted_guids: Dict = {}
        self._mcp_commands: Dict = {}

        # 載入 trusted_guids.json
        trusted_path = self.config_dir / "trusted_guids.json"
        if trusted_path.exists():
            with open(trusted_path, 'r', encoding='utf-8') as f:
                self._trusted_guids = json.load(f)

        # 載入 mcp_commands.json
        commands_path = self.config_dir / "mcp_commands.json"
        if commands_path.exists():
            with open(commands_path, 'r', encoding='utf-8') as f:
                self._mcp_commands = json.load(f)

    def check_placement_info(self, placement_info: Dict) -> List[CheckResult]:
        """
        驗證 placement_info.json

        Args:
            placement_info: 解析後的 JSON 配置

        Returns:
            驗證結果列表
        """
        self.results = []

        components = placement_info.get("components", [])
        connections = placement_info.get("connections", [])
        mcp_calls = placement_info.get("mcp_calls", [])

        # 0. 檢查 MCP 命令（支持兩種格式）
        self._check_mcp_commands(mcp_calls)

        # 額外檢查 _meta.mcp_commands 格式
        meta = placement_info.get("_meta", {})
        meta_commands = meta.get("mcp_commands", [])
        if meta_commands:
            self._check_meta_mcp_commands(meta_commands)

        # 1. 檢查組件
        self._check_component_guids(components)
        self._check_component_values(components)

        # 2. 檢查連接
        self._check_connection_params(connections, components)
        self._check_connection_completeness(connections, components)

        # 3. 檢查 variable_params（如 Entwine）
        variable_params = placement_info.get("variable_params", [])
        self._check_variable_params(variable_params, components)

        return self.results

    def _check_mcp_commands(self, mcp_calls: List[Dict]):
        """檢查 MCP 命令是否可用（mcp_calls 格式）"""
        for call in mcp_calls:
            cmd = call.get('command', call.get('method', ''))
            self._validate_single_command(cmd)

    def _check_meta_mcp_commands(self, commands: List[str]):
        """檢查 MCP 命令是否可用（_meta.mcp_commands 格式）"""
        for cmd in commands:
            self._validate_single_command(cmd)

    def _validate_single_command(self, cmd: str):
        """驗證單個 MCP 命令"""
        if not cmd:
            return

        if cmd in self.config.mcp_unavailable:
            workaround = self.config.mcp_unavailable[cmd]
            self.results.append(CheckResult(
                passed=False,
                category=Category.MCP,
                severity=Severity.CRITICAL,
                message=f"MCP 命令 '{cmd}' 不存在",
                suggestion=f"替代方案: {workaround}"
            ))
        elif cmd not in self.config.mcp_available:
            self.results.append(CheckResult(
                passed=False,
                category=Category.MCP,
                severity=Severity.WARNING,
                message=f"未知的 MCP 命令 '{cmd}'",
                suggestion="請確認命令名稱是否正確"
            ))

    def _check_component_guids(self, components: List[Dict]):
        """檢查組件 GUID 是否可信"""
        trusted_components = self._trusted_guids.get("components", {})

        for comp in components:
            comp_id = comp.get("id", "unknown")
            comp_type = comp.get("type", "")
            guid = comp.get("guid")

            # 如果是已知衝突組件且沒有指定 GUID
            if comp_type in self.config.conflict_components and not guid:
                trusted_info = trusted_components.get(comp_type, {})
                trusted_guid = trusted_info.get("guid", "")

                self.results.append(CheckResult(
                    passed=False,
                    category=Category.GUID,
                    severity=Severity.WARNING,
                    message=f"組件 '{comp_type}' ({comp_id}) 有已知衝突，建議使用 trusted GUID",
                    component_id=comp_id,
                    suggestion=f"添加 guid: \"{trusted_guid[:20]}...\"" if trusted_guid else "查閱 config/trusted_guids.json",
                    details={"type": comp_type, "conflicts": trusted_info.get("known_conflicts")}
                ))

            # 如果指定了 GUID，檢查是否是 obsolete
            if guid:
                for _, info in trusted_components.items():
                    obsolete_guid = info.get("obsolete_guid")
                    if obsolete_guid and guid == obsolete_guid:
                        self.results.append(CheckResult(
                            passed=False,
                            category=Category.GUID,
                            severity=Severity.CRITICAL,
                            message=f"組件 '{comp_type}' ({comp_id}) 使用了 OBSOLETE GUID",
                            component_id=comp_id,
                            suggestion=f"改用新版 GUID: {info.get('guid', '')}",
                            details={"obsolete_guid": obsolete_guid, "correct_guid": info.get("guid")}
                        ))

    def _check_component_values(self, components: List[Dict]):
        """檢查 Slider/Panel 初始值"""
        for comp in components:
            comp_id = comp.get("id", comp.get("nickname", "unknown"))
            comp_type = comp.get("type", "")
            nickname = comp.get("nickname", comp_id)

            # 支援兩種格式：直接 value 或 properties.value
            value = comp.get("value")
            if value is None:
                properties = comp.get("properties", {})
                value = properties.get("value")

            # Panel 必須有值
            if comp_type in self.config.require_value_types and value is None:
                self.results.append(CheckResult(
                    passed=False,
                    category=Category.VALUE,
                    severity=Severity.WARNING,
                    message=f"Panel '{nickname}' ({comp_id}) 未設定內容",
                    component_id=comp_id,
                    suggestion="WASP 等組件需要 Panel 有內容，添加 value 欄位"
                ))

            # Slider 建議有值
            if comp_type in self.config.suggest_value_types:
                if value is None:
                    self.results.append(CheckResult(
                        passed=True,  # 不是錯誤，只是提醒
                        category=Category.VALUE,
                        severity=Severity.INFO,
                        message=f"Slider '{nickname}' ({comp_id}) 未設定初始值",
                        component_id=comp_id,
                        suggestion="將使用預設值，可添加 value 欄位指定"
                    ))

                # 檢查 Slider 範圍設定
                min_val = comp.get("min")
                max_val = comp.get("max")
                if value is not None and (min_val is None or max_val is None):
                    self.results.append(CheckResult(
                        passed=True,
                        category=Category.VALUE,
                        severity=Severity.INFO,
                        message=f"Slider '{nickname}' 設定了 value 但未設定 min/max",
                        component_id=comp_id,
                        suggestion="建議同時設定 min/max 避免值被 clamp"
                    ))

    def _check_connection_params(self, connections: List[Dict], components: List[Dict]):
        """檢查連接參數是否有 FuzzyMatcher 風險"""
        # 建立組件 ID → 類型的映射
        comp_types = {c.get("id"): c.get("type", "") for c in components}

        for conn in connections:
            from_id = conn.get("from", "")
            to_id = conn.get("to", "")
            from_param = conn.get("fromParam", "")
            to_param = conn.get("toParam", "")

            # 檢查是否使用了索引
            has_from_index = "fromParamIndex" in conn
            has_to_index = "toParamIndex" in conn

            # 檢查 fromParam 風險
            if not has_from_index and from_param and from_param.lower() in {p.lower() for p in self.config.fuzzy_risk_params}:
                from_type = comp_types.get(from_id, "unknown")
                self.results.append(CheckResult(
                    passed=False,
                    category=Category.PARAM,
                    severity=Severity.WARNING,
                    message=f"參數 '{from_param}' ({from_id}.{from_param} → {to_id}) 有 FuzzyMatcher 風險",
                    component_id=from_id,
                    suggestion="使用 fromParamIndex 替代 fromParam 避免參數映射錯誤",
                    details={
                        "from": f"{from_id}.{from_param}",
                        "to": f"{to_id}.{to_param}",
                        "from_type": from_type,
                        "risk": "FuzzyMatcher 可能將 'R' 映射為 'Radius'"
                    }
                ))

            # 檢查 toParam 風險（較少見，但也需要檢查）
            if not has_to_index and to_param and to_param.lower() in {p.lower() for p in self.config.fuzzy_risk_params}:
                self.results.append(CheckResult(
                    passed=False,
                    category=Category.PARAM,
                    severity=Severity.WARNING,
                    message=f"目標參數 '{to_param}' ({from_id} → {to_id}.{to_param}) 有 FuzzyMatcher 風險",
                    component_id=to_id,
                    suggestion="使用 toParamIndex 替代 toParam",
                    details={"from": from_id, "to": f"{to_id}.{to_param}"}
                ))

    def _check_connection_completeness(self, connections: List[Dict], components: List[Dict]):
        """檢查連接完整性（是否有孤立組件）"""
        comp_ids = {c.get("id") for c in components}
        connected_ids = set()

        for conn in connections:
            connected_ids.add(conn.get("from", ""))
            connected_ids.add(conn.get("to", ""))

        # 找出未連接的組件
        unconnected = comp_ids - connected_ids

        # 排除輸入組件（Slider, Panel, Toggle 等）
        input_types = {"Number Slider", "Panel", "Boolean Toggle"}
        for comp in components:
            if comp.get("type") in input_types:
                unconnected.discard(comp.get("id"))

        for comp_id in unconnected:
            comp = next((c for c in components if c.get("id") == comp_id), {})
            comp_type = comp.get("type", "unknown")

            self.results.append(CheckResult(
                passed=True,  # 不一定是錯誤
                category=Category.CONNECTION,
                severity=Severity.INFO,
                message=f"組件 '{comp_type}' ({comp_id}) 沒有任何連接",
                component_id=comp_id,
                suggestion="確認是否缺少連接"
            ))

    def _check_variable_params(self, variable_params: List[Dict], components: List[Dict]):
        """檢查 variable_params 配置"""
        comp_ids = {c.get("id") for c in components}

        for vp in variable_params:
            comp_id = vp.get("componentId")

            if comp_id and comp_id not in comp_ids:
                self.results.append(CheckResult(
                    passed=False,
                    category=Category.CONNECTION,
                    severity=Severity.CRITICAL,
                    message=f"variable_params 引用了不存在的組件 '{comp_id}'",
                    component_id=comp_id,
                    suggestion="確認 componentId 與 components 中的 id 一致"
                ))

    def _match_severity(self, result_severity: Union[Severity, str], target: Severity) -> bool:
        """匹配 severity（支持 Enum 和 string）"""
        if isinstance(result_severity, Severity):
            return result_severity == target
        return result_severity == target.value

    def get_critical_count(self) -> int:
        """獲取 Critical 問題數量"""
        return len([r for r in self.results if self._match_severity(r.severity, Severity.CRITICAL)])

    def get_warning_count(self) -> int:
        """獲取 Warning 問題數量"""
        return len([r for r in self.results if self._match_severity(r.severity, Severity.WARNING)])

    def should_block_execution(self) -> bool:
        """是否應該阻擋執行（有 Critical 問題）"""
        return self.get_critical_count() > 0

    def should_warn_user(self) -> bool:
        """是否應該警告用戶（有 Warning 問題）"""
        return self.get_warning_count() > 0

    def generate_report(self, format: str = 'markdown') -> str:
        """
        生成驗證報告

        Args:
            format: 'markdown' 或 'json'

        Returns:
            格式化的報告字串
        """
        critical = [r for r in self.results if self._match_severity(r.severity, Severity.CRITICAL)]
        warnings = [r for r in self.results if self._match_severity(r.severity, Severity.WARNING)]
        infos = [r for r in self.results if self._match_severity(r.severity, Severity.INFO)]

        if format == 'json':
            return json.dumps({
                'passed': self.get_critical_count() == 0,
                'critical': self.get_critical_count(),
                'warnings': self.get_warning_count(),
                'info': len(infos),
                'results': [r.to_dict() for r in self.results]
            }, indent=2, ensure_ascii=False)

        # Markdown 格式
        lines = ["## Pre-Execution Checklist 驗證報告\n"]

        # 統計
        lines.append(f"**統計**: {self.get_critical_count()} Critical, "
                    f"{self.get_warning_count()} Warning, "
                    f"{len(infos)} Info\n")

        def _cat_str(cat: Union[Category, str]) -> str:
            return cat.value if isinstance(cat, Category) else cat

        # Critical
        if critical:
            lines.append("### 🔴 Critical（阻擋執行）\n")
            for r in critical:
                lines.append(f"- **[{_cat_str(r.category)}]** {r.message}")
                if r.suggestion:
                    lines.append(f"  → {r.suggestion}")
        else:
            lines.append("### 🔴 Critical\n無\n")

        # Warning
        if warnings:
            lines.append("\n### 🟡 Warning（建議修復）\n")
            for r in warnings:
                lines.append(f"- **[{_cat_str(r.category)}]** {r.message}")
                if r.suggestion:
                    lines.append(f"  → {r.suggestion}")
        else:
            lines.append("\n### 🟡 Warning\n無\n")

        # Info
        if infos:
            lines.append("\n### 🟢 Info（參考資訊）\n")
            for r in infos:
                lines.append(f"- [{_cat_str(r.category)}] {r.message}")

        # 結論
        lines.append("\n---\n")
        if critical:
            lines.append("### 結論: ❌ 不通過\n")
            lines.append(f"有 {len(critical)} 個 Critical 問題必須修復後才能執行。")
        elif warnings:
            lines.append("### 結論: ⚠️ 有條件通過\n")
            lines.append(f"有 {len(warnings)} 個 Warning 建議處理。是否繼續執行？")
        else:
            lines.append("### 結論: ✅ 通過\n")
            lines.append("配置驗證通過，可以執行部署。")

        return "\n".join(lines)

    def check_and_report(self, placement_info: Dict) -> tuple:
        """
        檢查並返回結果

        Returns:
            (passed, report) - 是否通過和報告內容
        """
        self.check_placement_info(placement_info)
        report = self.generate_report()
        return not self.should_block_execution(), report

    def generate_fix_suggestions(self) -> List[Dict]:
        """
        生成修復建議清單

        Returns:
            [{"component_id": ..., "fix": ...}, ...]
        """
        fixes = []

        for r in self.results:
            if r.severity in ("critical", "warning") and r.suggestion:
                fixes.append({
                    "component_id": r.component_id,
                    "category": r.category,
                    "severity": r.severity,
                    "message": r.message,
                    "fix": r.suggestion,
                    "details": r.details
                })

        return fixes


# ==================== 便捷函數 ====================

def check_placement_file(filepath: str) -> PreExecutionChecker:
    """
    驗證 placement_info.json 文件

    Args:
        filepath: 文件路徑

    Returns:
        驗證器實例（可調用 .generate_report() 等方法）
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        config = json.load(f)

    checker = PreExecutionChecker()
    checker.check_placement_info(config)
    return checker


def quick_check(filepath: str) -> bool:
    """
    快速檢查是否通過驗證

    Args:
        filepath: placement_info.json 路徑

    Returns:
        True 如果沒有 Critical 問題
    """
    checker = check_placement_file(filepath)
    return not checker.should_block_execution()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pre_execution_checker.py <placement_info.json>")
        print("\nExample:")
        print("  python pre_execution_checker.py GH_WIP/placement_info.json")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        checker = check_placement_file(filepath)
        print(checker.generate_report())

        # 設定退出碼
        if checker.should_block_execution():
            sys.exit(1)
        elif checker.should_warn_user():
            sys.exit(2)
        else:
            sys.exit(0)

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)
