#!/usr/bin/env python3
"""
Reference Mode - Reference-First 架構的核心模組
===============================================

核心理念：不讓系統猜測，而是找到成功案例後複製和微調。

流程：
    用戶請求 → 搜索 Reference Library → 顯示匹配 → 確認使用 → 複製配置 → 微調參數

Usage:
    from grasshopper_mcp.reference_mode import ReferenceMode

    ref_mode = ReferenceMode()
    match = ref_mode.search("做一個 WASP 離散聚集")
    if match:
        config = ref_mode.use_reference(match.path, modifications={"Count": 20})
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MatchConfidence(Enum):
    """匹配信心度等級"""
    EXACT = 1.0      # 精確匹配
    HIGH = 0.85      # 高度匹配
    MEDIUM = 0.6     # 中度匹配
    LOW = 0.4        # 低度匹配
    NONE = 0.0       # 無匹配


@dataclass
class ReferenceMatch:
    """參考配置匹配結果"""
    id: str
    name: str
    path: str
    confidence: float
    keywords_matched: List[str]
    description: str
    is_golden: bool = False
    is_verified: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "confidence": self.confidence,
            "keywords_matched": self.keywords_matched,
            "description": self.description,
            "is_golden": self.is_golden,
            "is_verified": self.is_verified
        }


@dataclass
class ReferenceConfig:
    """參考配置"""
    meta: Dict
    components: List[Dict]
    connections: List[Dict]
    layout: Dict
    lessons_learned: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Path) -> "ReferenceConfig":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            meta=data.get("_meta", {}),
            components=data.get("components", []),
            connections=data.get("connections", []),
            layout=data.get("layout", {}),
            lessons_learned=data.get("_lessons_learned", [])
        )

    def to_placement_info(self, col_width: int = 150, row_height: int = 50) -> Dict:
        """轉換為 placement_info.json 格式"""
        # 計算實際座標
        components_with_positions = []
        for comp in self.components:
            col = comp.get("col", 0)
            row = comp.get("row", 0)
            x = 50 + col * col_width
            y = 50 + row * row_height

            component = {
                "nickname": comp.get("nickname"),
                "type": comp.get("type"),
                "x": x,
                "y": y
            }

            if comp.get("guid"):
                component["guid"] = comp["guid"]
            if comp.get("properties"):
                component["properties"] = comp["properties"]

            components_with_positions.append(component)

        return {
            "_meta": self.meta,
            "components": components_with_positions,
            "connections": self.connections,
            "layout": self.layout
        }


class ReferenceLibrary:
    """參考配置庫"""

    def __init__(self, library_path: str = "reference_library"):
        self.library_path = Path(library_path)
        self.index: Dict[str, List[str]] = {}  # keyword -> config_ids
        self.configs: Dict[str, Dict] = {}     # config_id -> metadata
        self._load_library()

    def _load_library(self):
        """載入所有 metadata.json"""
        if not self.library_path.exists():
            return

        for plugin_dir in self.library_path.iterdir():
            if not plugin_dir.is_dir():
                continue

            metadata_path = plugin_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # 載入 golden configs
            for config in metadata.get("golden_configs", []):
                config_id = f"{plugin_dir.name}/{config['id']}"
                config["full_path"] = str(plugin_dir / config["path"])
                config["plugin"] = plugin_dir.name
                config["is_golden"] = True
                self.configs[config_id] = config

                # 建立關鍵字索引
                for kw in config.get("keywords", []):
                    kw_lower = kw.lower()
                    if kw_lower not in self.index:
                        self.index[kw_lower] = []
                    self.index[kw_lower].append(config_id)

            # 載入 variations
            for config in metadata.get("variations", []):
                config_id = f"{plugin_dir.name}/{config['id']}"
                config["full_path"] = str(plugin_dir / config["path"])
                config["plugin"] = plugin_dir.name
                config["is_golden"] = False
                self.configs[config_id] = config

                for kw in config.get("keywords", []):
                    kw_lower = kw.lower()
                    if kw_lower not in self.index:
                        self.index[kw_lower] = []
                    self.index[kw_lower].append(config_id)

    def search(self, query: str, top_k: int = 3) -> List[ReferenceMatch]:
        """
        搜索匹配的參考配置

        Args:
            query: 用戶查詢
            top_k: 返回前 k 個結果

        Returns:
            匹配結果列表
        """
        # 提取關鍵字（支援中文）
        query_lower = query.lower()

        # 英文單詞
        english_words = set(re.findall(r'[a-z]+', query_lower))

        # 中文詞彙（直接匹配索引中的中文關鍵字）
        chinese_matches = set()
        for indexed_kw in self.index.keys():
            if indexed_kw in query_lower or indexed_kw in query:
                chinese_matches.add(indexed_kw)

        query_keywords = english_words | chinese_matches

        # 計算每個配置的匹配分數
        scores: Dict[str, Tuple[float, List[str]]] = {}

        for kw in query_keywords:
            if kw in self.index:
                for config_id in self.index[kw]:
                    if config_id not in scores:
                        scores[config_id] = (0.0, [])
                    current_score, matched_kws = scores[config_id]
                    matched_kws.append(kw)
                    scores[config_id] = (current_score + 1.0, matched_kws)

        # 排序並生成結果
        results = []
        for config_id, (score, matched_kws) in sorted(
            scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )[:top_k]:
            config = self.configs[config_id]

            # 計算信心度
            total_keywords = len(config.get("keywords", []))
            confidence = score / max(total_keywords, 1)

            # Golden 配置加成
            if config.get("is_golden"):
                confidence = min(confidence * 1.5, 1.0)

            results.append(ReferenceMatch(
                id=config_id,
                name=config.get("name", ""),
                path=config.get("full_path", ""),
                confidence=confidence,
                keywords_matched=matched_kws,
                description=config.get("description", ""),
                is_golden=config.get("is_golden", False),
                is_verified=config.get("confidence", 0) >= 1.0
            ))

        return results


class ReferenceMode:
    """
    Reference Mode - Reference-First 工作模式

    流程：
    1. search(): 搜索匹配的參考配置
    2. preview(): 顯示配置預覽
    3. use_reference(): 使用配置（可選修改）
    4. execute(): 執行部署
    """

    def __init__(self, library_path: str = "reference_library"):
        self.library = ReferenceLibrary(library_path)
        self.current_config: Optional[ReferenceConfig] = None
        self.current_match: Optional[ReferenceMatch] = None

    def search(self, query: str) -> List[ReferenceMatch]:
        """
        搜索參考配置

        Args:
            query: 用戶查詢（如 "做一個 WASP 離散聚集"）

        Returns:
            匹配結果列表
        """
        return self.library.search(query)

    def preview(self, match: ReferenceMatch) -> Dict:
        """
        預覽參考配置

        Returns:
            配置摘要
        """
        config = ReferenceConfig.from_json(Path(match.path))

        return {
            "name": match.name,
            "description": match.description,
            "is_golden": match.is_golden,
            "components": [
                {"nickname": c.get("nickname"), "type": c.get("type")}
                for c in config.components
            ],
            "connections_count": len(config.connections),
            "lessons_learned": config.lessons_learned
        }

    def use_reference(
        self,
        match: ReferenceMatch,
        modifications: Optional[Dict] = None
    ) -> Dict:
        """
        使用參考配置

        Args:
            match: 匹配結果
            modifications: 修改項目（如 {"Count": 20, "Seed": 123}）

        Returns:
            placement_info.json 格式
        """
        config = ReferenceConfig.from_json(Path(match.path))
        placement_info = config.to_placement_info()

        # 應用修改
        if modifications:
            for comp in placement_info["components"]:
                nickname = comp.get("nickname")
                if nickname in modifications:
                    if "properties" not in comp:
                        comp["properties"] = {}
                    comp["properties"]["value"] = modifications[nickname]

        self.current_config = config
        self.current_match = match

        return placement_info

    def get_execution_advice(self) -> List[str]:
        """
        獲取執行建議（從 lessons_learned）

        Returns:
            建議列表
        """
        if self.current_config:
            return self.current_config.lessons_learned
        return []


# ============================================================================
# 整合到 DualModeWorkflow
# ============================================================================

def integrate_reference_mode(workflow_class):
    """
    裝飾器：將 Reference Mode 整合到 DualModeWorkflow

    Usage:
        @integrate_reference_mode
        class DualModeWorkflow:
            ...
    """
    original_run = workflow_class.run

    async def enhanced_run(self, request: str, **kwargs):
        # 優先檢查 Reference Library
        ref_mode = ReferenceMode()
        matches = ref_mode.search(request)

        if matches and matches[0].confidence >= 0.7:
            best_match = matches[0]
            print(f"\n【Reference Mode】")
            print(f"  找到匹配配置: {best_match.name}")
            print(f"  信心度: {best_match.confidence:.2f}")
            print(f"  匹配關鍵字: {best_match.keywords_matched}")

            # 顯示預覽
            preview = ref_mode.preview(best_match)
            print(f"  組件數: {len(preview['components'])}")

            if best_match.is_golden:
                print(f"  ✅ Golden Config (已驗證)")

            # 使用參考配置
            placement_info = ref_mode.use_reference(best_match)

            # 直接進入執行階段
            self.state.placement_info = placement_info
            self.state.check_passed = True

            # 顯示執行建議
            advice = ref_mode.get_execution_advice()
            if advice:
                print(f"\n  📝 執行注意事項:")
                for a in advice:
                    print(f"    - {a}")

            return {"mode": "reference", "match": best_match.to_dict(), "placement_info": placement_info}

        # 否則使用原始流程
        return await original_run(self, request, **kwargs)

    workflow_class.run = enhanced_run
    return workflow_class


# ============================================================================
# CLI 測試
# ============================================================================

def main():
    """命令行測試"""
    import sys

    ref_mode = ReferenceMode()

    test_queries = [
        "做一個 WASP 離散聚集",
        "wasp cube aggregation",
        "立方體聚集設計",
    ]

    if len(sys.argv) > 1:
        test_queries = [" ".join(sys.argv[1:])]

    print("=" * 60)
    print("Reference Mode 測試")
    print("=" * 60)

    for query in test_queries:
        print(f"\n查詢: {query}")
        print("-" * 40)

        matches = ref_mode.search(query)

        if not matches:
            print("  無匹配結果")
            continue

        for i, match in enumerate(matches):
            print(f"\n  [{i+1}] {match.name}")
            print(f"      信心度: {match.confidence:.2f}")
            print(f"      關鍵字: {match.keywords_matched}")
            print(f"      路徑: {match.path}")
            print(f"      Golden: {'✅' if match.is_golden else '❌'}")

            # 預覽
            preview = ref_mode.preview(match)
            print(f"      組件: {[c['nickname'] for c in preview['components'][:5]]}...")

            if preview.get("lessons_learned"):
                print(f"      經驗: {preview['lessons_learned'][0][:50]}...")


if __name__ == "__main__":
    main()
