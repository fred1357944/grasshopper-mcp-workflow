#!/usr/bin/env python3
"""
連接三元組分析器 - 從 GHX 文件學習語義連接模式

分析所有 GHX 範例中的連接關係，建立：
1. 語義三元組資料庫: SourceComponent.Output → TargetComponent.Input
2. 連接頻率統計
3. 前驅/後繼推薦表
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from ghx_parser import GHXParser, GHXDocument, Component, Connection


@dataclass
class ConnectionTriplet:
    """語義三元組"""
    source_component: str  # 組件類型名稱
    source_param: str      # 輸出參數名
    target_component: str  # 組件類型名稱
    target_param: str      # 輸入參數名
    frequency: int = 1
    examples: List[str] = field(default_factory=list)  # 來源文件


@dataclass
class ComponentConnectionStats:
    """組件連接統計"""
    component_name: str
    predecessors: Dict[str, int] = field(default_factory=dict)  # 上游組件 -> 頻率
    successors: Dict[str, int] = field(default_factory=dict)    # 下游組件 -> 頻率
    input_sources: Dict[str, Dict[str, int]] = field(default_factory=dict)  # input_param -> {source_comp.out -> freq}
    output_targets: Dict[str, Dict[str, int]] = field(default_factory=dict) # output_param -> {target_comp.in -> freq}


class ConnectionAnalyzer:
    """連接模式分析器"""

    def __init__(self):
        self.parser = GHXParser()
        self.triplets: Dict[str, ConnectionTriplet] = {}  # key -> triplet
        self.component_stats: Dict[str, ComponentConnectionStats] = {}  # comp_name -> stats
        self.analyzed_files: List[str] = []

    def analyze_folder(self, folder: str, recursive: bool = True) -> None:
        """分析資料夾中所有 GHX 文件"""
        folder_path = Path(folder)
        pattern = "**/*.gh*" if recursive else "*.gh*"

        for file_path in folder_path.glob(pattern):
            if file_path.suffix.lower() in ['.ghx', '.gh']:
                self._analyze_file(str(file_path))

        print(f"\n分析完成: {len(self.analyzed_files)} 個文件")
        print(f"提取三元組: {len(self.triplets)}")
        print(f"分析組件: {len(self.component_stats)}")

    def _analyze_file(self, file_path: str) -> None:
        """分析單個文件"""
        doc = self.parser.parse_ghx(file_path)
        if not doc:
            return

        self.analyzed_files.append(file_path)
        file_name = Path(file_path).name

        # 建立 instance_guid -> component 映射
        guid_to_comp: Dict[str, Component] = {
            comp.instance_guid: comp for comp in doc.components
        }

        # 分析每個連接
        for conn in doc.connections:
            source_comp = guid_to_comp.get(conn.from_component)
            target_comp = guid_to_comp.get(conn.to_component)

            if not source_comp or not target_comp:
                continue

            # 跳過 Group 等非組件
            if source_comp.name == 'Group' or target_comp.name == 'Group':
                continue

            self._record_triplet(
                source_comp.name,
                conn.from_param,
                target_comp.name,
                conn.to_param,
                file_name
            )

            self._update_component_stats(
                source_comp.name,
                conn.from_param,
                target_comp.name,
                conn.to_param
            )

    def _record_triplet(self, src_comp: str, src_param: str,
                        tgt_comp: str, tgt_param: str, file_name: str) -> None:
        """記錄三元組"""
        key = f"{src_comp}.{src_param} -> {tgt_comp}.{tgt_param}"

        if key in self.triplets:
            self.triplets[key].frequency += 1
            if file_name not in self.triplets[key].examples:
                self.triplets[key].examples.append(file_name)
        else:
            self.triplets[key] = ConnectionTriplet(
                source_component=src_comp,
                source_param=src_param,
                target_component=tgt_comp,
                target_param=tgt_param,
                frequency=1,
                examples=[file_name]
            )

    def _update_component_stats(self, src_comp: str, src_param: str,
                                 tgt_comp: str, tgt_param: str) -> None:
        """更新組件統計"""
        # 更新來源組件的 successors
        if src_comp not in self.component_stats:
            self.component_stats[src_comp] = ComponentConnectionStats(component_name=src_comp)
        stats = self.component_stats[src_comp]
        stats.successors[tgt_comp] = stats.successors.get(tgt_comp, 0) + 1

        if src_param not in stats.output_targets:
            stats.output_targets[src_param] = {}
        target_key = f"{tgt_comp}.{tgt_param}"
        stats.output_targets[src_param][target_key] = stats.output_targets[src_param].get(target_key, 0) + 1

        # 更新目標組件的 predecessors
        if tgt_comp not in self.component_stats:
            self.component_stats[tgt_comp] = ComponentConnectionStats(component_name=tgt_comp)
        stats = self.component_stats[tgt_comp]
        stats.predecessors[src_comp] = stats.predecessors.get(src_comp, 0) + 1

        if tgt_param not in stats.input_sources:
            stats.input_sources[tgt_param] = {}
        source_key = f"{src_comp}.{src_param}"
        stats.input_sources[tgt_param][source_key] = stats.input_sources[tgt_param].get(source_key, 0) + 1

    def get_top_triplets(self, n: int = 20) -> List[ConnectionTriplet]:
        """獲取頻率最高的 n 個三元組"""
        sorted_triplets = sorted(
            self.triplets.values(),
            key=lambda t: t.frequency,
            reverse=True
        )
        return sorted_triplets[:n]

    def get_recommendations(self, component_name: str) -> Dict:
        """獲取組件的連接推薦"""
        stats = self.component_stats.get(component_name)
        if not stats:
            return {"error": f"Component '{component_name}' not found"}

        return {
            "component": component_name,
            "common_predecessors": dict(sorted(
                stats.predecessors.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "common_successors": dict(sorted(
                stats.successors.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "input_recommendations": {
                inp: dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3])
                for inp, sources in stats.input_sources.items()
            },
            "output_recommendations": {
                out: dict(sorted(targets.items(), key=lambda x: x[1], reverse=True)[:3])
                for out, targets in stats.output_targets.items()
            }
        }

    def filter_by_plugin(self, plugin_prefix: str) -> Dict[str, ConnectionTriplet]:
        """過濾特定插件的三元組"""
        return {
            key: triplet for key, triplet in self.triplets.items()
            if plugin_prefix.lower() in triplet.source_component.lower() or
               plugin_prefix.lower() in triplet.target_component.lower()
        }

    def to_json(self, output_path: str) -> None:
        """匯出分析結果為 JSON"""
        data = {
            "metadata": {
                "analyzed_files": len(self.analyzed_files),
                "total_triplets": len(self.triplets),
                "total_components": len(self.component_stats)
            },
            "triplets": [
                asdict(t) for t in sorted(
                    self.triplets.values(),
                    key=lambda t: t.frequency,
                    reverse=True
                )
            ],
            "component_stats": {
                name: {
                    "component_name": stats.component_name,
                    "predecessors": dict(sorted(stats.predecessors.items(), key=lambda x: x[1], reverse=True)),
                    "successors": dict(sorted(stats.successors.items(), key=lambda x: x[1], reverse=True)),
                    "input_sources": stats.input_sources,
                    "output_targets": stats.output_targets
                }
                for name, stats in self.component_stats.items()
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"已匯出至: {output_path}")


# CLI 介面
if __name__ == "__main__":
    import sys

    analyzer = ConnectionAnalyzer()

    # 分析 WASP 範例
    wasp_folder = "gh_learning/ghx_samples"
    if len(sys.argv) > 1:
        wasp_folder = sys.argv[1]

    print(f"分析資料夾: {wasp_folder}")
    analyzer.analyze_folder(wasp_folder)

    # 輸出結果
    print("\n=== 最常見的連接模式 (Top 20) ===")
    for triplet in analyzer.get_top_triplets(20):
        print(f"  [{triplet.frequency:3d}x] {triplet.source_component}.{triplet.source_param} -> "
              f"{triplet.target_component}.{triplet.target_param}")

    # WASP 專項分析
    print("\n=== WASP 連接模式 ===")
    wasp_triplets = analyzer.filter_by_plugin("Wasp")
    for key, triplet in sorted(wasp_triplets.items(), key=lambda x: x[1].frequency, reverse=True)[:15]:
        print(f"  [{triplet.frequency:3d}x] {triplet.source_component}.{triplet.source_param} -> "
              f"{triplet.target_component}.{triplet.target_param}")

    # 組件推薦示例
    print("\n=== WASP_Stochastic Aggregation 連接推薦 ===")
    recs = analyzer.get_recommendations("Wasp_Stochastic Aggregation")
    if "error" not in recs:
        print(f"  常見上游: {recs['common_predecessors']}")
        print(f"  常見下游: {recs['common_successors']}")

    # 匯出 JSON
    output_path = sys.argv[2] if len(sys.argv) > 2 else "config/connection_triplets.json"
    analyzer.to_json(output_path)
