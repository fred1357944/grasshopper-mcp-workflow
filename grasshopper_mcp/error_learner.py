"""
錯誤學習器 - 從執行錯誤中學習
=============================================
實現錯誤學習閉環：記錄 → 分析 → 歸納 → 預防

功能：
1. 記錄 MCP 執行錯誤和上下文
2. 自動分析錯誤模式
3. 生成預防規則
4. 與 PreExecutionChecker 整合
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class LearnedError:
    """已學習的錯誤"""
    error_id: str                   # 唯一識別符
    error_pattern: str              # 錯誤訊息模式 (regex)
    root_cause: str                 # 根因分析
    prevention_rule: str            # 預防規則
    prevention_check: Optional[str] # 自動檢查邏輯（Python 表達式）
    examples: List[Dict] = field(default_factory=list)  # 實際案例
    learned_at: str = ""            # 學習時間
    occurrence_count: int = 1       # 發生次數
    tags: List[str] = field(default_factory=list)  # 標籤 (如 "wasp", "type", "guid")


@dataclass
class ErrorContext:
    """錯誤上下文"""
    command: str                    # MCP 命令
    parameters: Dict                # 命令參數
    connection: Optional[Dict]      # 相關連接（如果是連接錯誤）
    component: Optional[Dict]       # 相關組件（如果是組件錯誤）
    timestamp: str = ""             # 發生時間


class ErrorLearner:
    """錯誤學習器"""

    # 錯誤模式識別規則
    ERROR_PATTERNS = [
        {
            "pattern": r"Data conversion failed from (\w+) to (\w+)",
            "id_template": "type_conversion_{0}_{1}",
            "root_cause_template": "嘗試將 {0} 類型連接到需要 {1} 類型的參數",
            "rule_template": "RULE: {0} 不能直接連接到 {1} 類型的參數",
            "tags": ["type", "conversion"]
        },
        {
            "pattern": r"(not found|does not exist|Cannot find)",
            "id_template": "component_not_found",
            "root_cause_template": "組件 GUID 不存在或已過期",
            "rule_template": "RULE: 使用 query-guid 命令驗證 GUID 是否有效",
            "tags": ["guid", "not_found"]
        },
        {
            "pattern": r"index.*(out of range|invalid|exceeded)",
            "id_template": "index_out_of_range",
            "root_cause_template": "參數索引超出組件的有效範圍",
            "rule_template": "RULE: 使用 component_specs.json 驗證參數索引",
            "tags": ["index", "param"]
        },
        {
            "pattern": r"(OBSOLETE|obsolete|deprecated)",
            "id_template": "obsolete_component",
            "root_cause_template": "使用了已過期的組件版本",
            "rule_template": "RULE: 使用 trusted_guids.json 中的最新 GUID",
            "tags": ["guid", "obsolete"]
        },
        {
            "pattern": r"(Null|null|None).*(input|parameter|data)",
            "id_template": "null_input",
            "root_cause_template": "輸入參數為空或未連接",
            "rule_template": "RULE: 確保所有必要輸入都已連接",
            "tags": ["null", "input"]
        },
        {
            "pattern": r"(GEO|Geometry).*(Mesh|mesh)",
            "id_template": "geo_mesh_type",
            "root_cause_template": "WASP Connection 的 GEO 參數需要 Mesh 類型，不是 Brep",
            "rule_template": "RULE: WASP Connection.GEO 必須接收 Mesh（使用 Mesh Box 而非 Box）",
            "tags": ["wasp", "mesh", "type"]
        },
        {
            "pattern": r"(slider|Slider).*(range|value|min|max)",
            "id_template": "slider_range",
            "root_cause_template": "Slider 的值被 clamp 到預設範圍",
            "rule_template": "RULE: 設定 Slider 時先設 min/max，再設 value",
            "tags": ["slider", "range"]
        },
    ]

    def __init__(self, errors_path: Optional[Path] = None):
        if errors_path is None:
            errors_path = Path(__file__).parent.parent / "config" / "learned_errors.json"

        self.errors_path = errors_path
        self.errors: List[LearnedError] = []
        self._load()

    def _load(self):
        """載入已學習的錯誤"""
        if self.errors_path.exists():
            try:
                with open(self.errors_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.errors = [
                    LearnedError(**e) for e in data.get("errors", [])
                ]
                logger.info(f"已載入 {len(self.errors)} 個已學習的錯誤模式")
            except Exception as e:
                logger.warning(f"載入錯誤文件失敗: {e}")
                self.errors = []
        else:
            logger.info("錯誤學習文件不存在，將從空白開始")

    def _save(self):
        """保存已學習的錯誤"""
        # 確保目錄存在
        self.errors_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.errors_path, 'w', encoding='utf-8') as f:
            json.dump({
                "_meta": {
                    "description": "從 MCP 執行錯誤中學習的模式和規則",
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "total_errors": len(self.errors)
                },
                "errors": [asdict(e) for e in self.errors]
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"已保存 {len(self.errors)} 個錯誤模式")

    def learn_from_error(
        self,
        error_message: str,
        context: ErrorContext,
        analysis: Optional[str] = None
    ) -> Optional[LearnedError]:
        """
        從 MCP 錯誤中學習

        Args:
            error_message: MCP 返回的錯誤訊息
            context: 錯誤上下文
            analysis: 可選的人工分析

        Returns:
            已學習或更新的錯誤對象
        """
        # 嘗試匹配已知錯誤模式
        for error in self.errors:
            if re.search(error.error_pattern, error_message, re.IGNORECASE):
                # 更新已知錯誤
                error.occurrence_count += 1
                error.examples.append({
                    "message": error_message,
                    "context": asdict(context) if hasattr(context, '__dict__') else context.__dict__,
                    "timestamp": datetime.now().isoformat()
                })
                # 保留最近 10 個案例
                error.examples = error.examples[-10:]
                self._save()
                logger.info(f"已更新錯誤模式: {error.error_id} (次數: {error.occurrence_count})")
                return error

        # 分析新錯誤
        learned = self._analyze_error(error_message, context, analysis)
        if learned:
            self.errors.append(learned)
            self._save()
            logger.info(f"已學習新錯誤模式: {learned.error_id}")

        return learned

    def _analyze_error(
        self,
        error_message: str,
        context: ErrorContext,
        analysis: Optional[str] = None
    ) -> Optional[LearnedError]:
        """分析錯誤並生成學習結果"""

        # 嘗試匹配預定義模式
        for pattern_def in self.ERROR_PATTERNS:
            match = re.search(pattern_def["pattern"], error_message, re.IGNORECASE)
            if match:
                groups = match.groups()

                # 生成錯誤 ID
                if groups:
                    error_id = pattern_def["id_template"].format(*groups)
                    root_cause = pattern_def["root_cause_template"].format(*groups)
                    rule = pattern_def["rule_template"].format(*groups)
                else:
                    error_id = pattern_def["id_template"]
                    root_cause = pattern_def["root_cause_template"]
                    rule = pattern_def["rule_template"]

                return LearnedError(
                    error_id=error_id,
                    error_pattern=pattern_def["pattern"],
                    root_cause=root_cause,
                    prevention_rule=rule,
                    prevention_check=None,
                    examples=[{
                        "message": error_message,
                        "context": asdict(context) if hasattr(context, '__dict__') else {},
                        "timestamp": datetime.now().isoformat()
                    }],
                    learned_at=datetime.now().isoformat(),
                    tags=pattern_def.get("tags", [])
                )

        # 未知錯誤 - 需要人工分析
        error_id = f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return LearnedError(
            error_id=error_id,
            error_pattern=re.escape(error_message[:100]),
            root_cause=analysis or "待分析",
            prevention_rule="待定義",
            prevention_check=None,
            examples=[{
                "message": error_message,
                "context": asdict(context) if hasattr(context, '__dict__') else {},
                "timestamp": datetime.now().isoformat()
            }],
            learned_at=datetime.now().isoformat(),
            tags=["unknown"]
        )

    def check_known_errors(self, connection: Dict) -> List[Tuple[LearnedError, str]]:
        """
        檢查連接是否可能觸發已知錯誤

        Args:
            connection: 連接定義

        Returns:
            (已知錯誤, 警告訊息) 列表
        """
        warnings = []

        for error in self.errors:
            # 檢查標籤相關的規則
            if "wasp" in error.tags and "GEO" in str(connection):
                if error.error_id == "geo_mesh_type":
                    warnings.append((error, "WASP Connection.GEO 必須接收 Mesh 類型"))

            if "slider" in error.tags and "slider" in str(connection).lower():
                if error.error_id == "slider_range":
                    warnings.append((error, "設定 Slider 時注意先設 min/max 再設 value"))

            if "type" in error.tags:
                # 如果連接涉及類型轉換，檢查是否是已知的不兼容類型
                pass  # 由 ConnectionValidator 處理

        return warnings

    def get_prevention_rules(self, tags: Optional[List[str]] = None) -> List[str]:
        """
        獲取預防規則

        Args:
            tags: 可選的標籤過濾

        Returns:
            規則列表
        """
        rules = []
        for error in self.errors:
            if tags is None or any(t in error.tags for t in tags):
                rules.append(error.prevention_rule)
        return rules

    def get_error_by_id(self, error_id: str) -> Optional[LearnedError]:
        """根據 ID 獲取錯誤"""
        for error in self.errors:
            if error.error_id == error_id:
                return error
        return None

    def get_statistics(self) -> Dict:
        """獲取統計信息"""
        tag_counts = {}
        for error in self.errors:
            for tag in error.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_errors": len(self.errors),
            "total_occurrences": sum(e.occurrence_count for e in self.errors),
            "tag_distribution": tag_counts,
            "most_frequent": sorted(
                self.errors,
                key=lambda e: e.occurrence_count,
                reverse=True
            )[:5]
        }


def main():
    """測試錯誤學習器"""
    learner = ErrorLearner()

    print("=== 測試 ErrorLearner ===\n")

    # 測試 1: 學習類型轉換錯誤
    print("測試 1: 學習類型轉換錯誤")
    context = ErrorContext(
        command="connect",
        parameters={"from": "panel_1", "to": "point_1"},
        connection={"from": "panel_1", "to": "point_1", "toParam": "X"},
        component=None,
        timestamp=datetime.now().isoformat()
    )
    error = learner.learn_from_error(
        "Data conversion failed from String to Number",
        context
    )
    if error:
        print(f"  錯誤 ID: {error.error_id}")
        print(f"  根因: {error.root_cause}")
        print(f"  預防規則: {error.prevention_rule}")
        print(f"  標籤: {error.tags}")

    # 測試 2: 學習 WASP 錯誤
    print("\n測試 2: 學習 WASP GEO 錯誤")
    context2 = ErrorContext(
        command="connect",
        parameters={"from": "box_1", "to": "connection_1"},
        connection={"from": "box_1", "to": "connection_1", "toParam": "GEO"},
        component=None,
        timestamp=datetime.now().isoformat()
    )
    error2 = learner.learn_from_error(
        "GEO input expects Mesh data, got Brep",
        context2
    )
    if error2:
        print(f"  錯誤 ID: {error2.error_id}")
        print(f"  根因: {error2.root_cause}")
        print(f"  預防規則: {error2.prevention_rule}")

    # 測試 3: 獲取統計
    print("\n測試 3: 錯誤統計")
    stats = learner.get_statistics()
    print(f"  總錯誤數: {stats['total_errors']}")
    print(f"  標籤分布: {stats['tag_distribution']}")

    # 測試 4: 獲取特定標籤的規則
    print("\n測試 4: WASP 相關預防規則")
    wasp_rules = learner.get_prevention_rules(tags=["wasp"])
    for rule in wasp_rules:
        print(f"  - {rule}")

    print(f"\n已保存到: {learner.errors_path}")


if __name__ == "__main__":
    main()
