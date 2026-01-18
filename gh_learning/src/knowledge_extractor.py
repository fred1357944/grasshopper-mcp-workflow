#!/usr/bin/env python3
"""
Knowledge Extractor - 從解析的 GHX 文件中萃取知識

功能:
1. 統計組件使用頻率
2. 萃取參數映射 (nickname -> fullName)
3. 發現連線模式
4. 生成結構化知識庫
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field, asdict

from ghx_parser import GHXParser, GHXDocument, Component, Connection


@dataclass
class ComponentKnowledge:
    """組件知識"""
    guid: str
    names: Set[str] = field(default_factory=set)
    nicknames: Set[str] = field(default_factory=set)
    inputs: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    outputs: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    usage_count: int = 0
    connected_to: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    connected_from: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class KnowledgeExtractor:
    """知識萃取器"""

    def __init__(self):
        self.registry: Dict[str, ComponentKnowledge] = {}
        self.connection_patterns: Dict[str, int] = defaultdict(int)
        self.component_name_to_guid: Dict[str, str] = {}

    def extract(self, documents: List[GHXDocument]) -> Dict[str, Any]:
        """從多個解析結果中萃取知識"""

        for doc in documents:
            # 建立 instance_guid -> component 映射
            instance_map = {c.instance_guid: c for c in doc.components}

            # 處理組件
            for comp in doc.components:
                self._register_component(comp)

            # 處理連線
            for conn in doc.connections:
                self._record_connection(conn, instance_map)

        return self._export()

    def _register_component(self, comp: Component):
        """註冊組件知識"""
        guid = comp.component_guid
        if not guid:
            return

        if guid not in self.registry:
            self.registry[guid] = ComponentKnowledge(guid=guid)

        entry = self.registry[guid]
        entry.usage_count += 1

        # 記錄名稱
        if comp.name:
            entry.names.add(comp.name)
            self.component_name_to_guid[comp.name.lower()] = guid

        if comp.nickname:
            entry.nicknames.add(comp.nickname)

        # 記錄參數
        for inp in comp.inputs:
            if inp.nickname:
                entry.inputs[inp.nickname].add(inp.name or inp.nickname)

        for out in comp.outputs:
            if out.nickname:
                entry.outputs[out.nickname].add(out.name or out.nickname)

    def _record_connection(self, conn: Connection, instance_map: Dict[str, Component]):
        """記錄連線模式"""
        from_comp = instance_map.get(conn.from_component)
        to_comp = instance_map.get(conn.to_component)

        if from_comp and to_comp:
            from_guid = from_comp.component_guid
            to_guid = to_comp.component_guid

            # 記錄連線模式
            pattern = f"{from_comp.name}.{conn.from_param} -> {to_comp.name}.{conn.to_param}"
            self.connection_patterns[pattern] += 1

            # 更新組件連線統計
            if from_guid in self.registry:
                self.registry[from_guid].connected_to[to_guid] += 1
            if to_guid in self.registry:
                self.registry[to_guid].connected_from[from_guid] += 1

    def _export(self) -> Dict[str, Any]:
        """導出知識庫"""
        components = {}

        for guid, knowledge in self.registry.items():
            components[guid] = {
                "guid": guid,
                "names": list(knowledge.names),
                "nicknames": list(knowledge.nicknames),
                "inputs": {k: list(v) for k, v in knowledge.inputs.items()},
                "outputs": {k: list(v) for k, v in knowledge.outputs.items()},
                "usage_count": knowledge.usage_count,
                "commonly_connected_to": dict(
                    sorted(knowledge.connected_to.items(), key=lambda x: -x[1])[:10]
                ),
                "commonly_connected_from": dict(
                    sorted(knowledge.connected_from.items(), key=lambda x: -x[1])[:10]
                )
            }

        # 排序連線模式
        sorted_patterns = sorted(
            self.connection_patterns.items(),
            key=lambda x: -x[1]
        )[:100]  # 取 Top 100

        return {
            "components": components,
            "connection_patterns": dict(sorted_patterns),
            "name_to_guid": self.component_name_to_guid,
            "statistics": {
                "total_components": len(components),
                "total_patterns": len(self.connection_patterns)
            }
        }

    def merge_with_existing(self, existing_path: str) -> Dict[str, Any]:
        """與現有知識庫合併"""
        if not Path(existing_path).exists():
            return self._export()

        with open(existing_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

        new_data = self._export()

        # 合併組件
        for guid, comp_data in new_data['components'].items():
            if guid in existing.get('components', {}):
                old = existing['components'][guid]
                # 合併名稱
                comp_data['names'] = list(set(old.get('names', []) + comp_data['names']))
                comp_data['nicknames'] = list(set(old.get('nicknames', []) + comp_data['nicknames']))
                # 合併參數
                for nick, names in comp_data['inputs'].items():
                    old_names = old.get('inputs', {}).get(nick, [])
                    comp_data['inputs'][nick] = list(set(old_names + names))
                for nick, names in comp_data['outputs'].items():
                    old_names = old.get('outputs', {}).get(nick, [])
                    comp_data['outputs'][nick] = list(set(old_names + names))
                # 累加使用次數
                comp_data['usage_count'] += old.get('usage_count', 0)

            existing['components'][guid] = comp_data

        # 合併連線模式
        for pattern, count in new_data['connection_patterns'].items():
            existing['connection_patterns'][pattern] = \
                existing.get('connection_patterns', {}).get(pattern, 0) + count

        # 合併名稱映射
        existing['name_to_guid'] = {
            **existing.get('name_to_guid', {}),
            **new_data['name_to_guid']
        }

        return existing

    def to_component_params_format(self) -> Dict[str, Any]:
        """轉換為 component_params.json 格式"""
        result = {
            "_meta": {
                "version": "1.0.0",
                "description": "從 .ghx 文件自動萃取的組件參數",
                "source": "GHX Parser + Knowledge Extractor"
            },
            "components": {}
        }

        for guid, knowledge in self.registry.items():
            if not knowledge.names:
                continue

            name = list(knowledge.names)[0]  # 取第一個名稱

            inputs = []
            for nick, full_names in knowledge.inputs.items():
                inputs.append({
                    "nickname": nick,
                    "fullName": list(full_names)[0] if full_names else nick
                })

            outputs = []
            for nick, full_names in knowledge.outputs.items():
                outputs.append({
                    "nickname": nick,
                    "fullName": list(full_names)[0] if full_names else nick
                })

            result["components"][name] = {
                "guid": guid,
                "inputs": inputs,
                "outputs": outputs,
                "usage_count": knowledge.usage_count
            }

        return result


def generate_report(knowledge: Dict[str, Any]) -> str:
    """生成人類可讀的報告"""
    lines = [
        "# GHX Knowledge Report",
        "",
        f"## Statistics",
        f"- Total component types: {knowledge['statistics']['total_components']}",
        f"- Total connection patterns: {knowledge['statistics']['total_patterns']}",
        "",
        "## Top 20 Most Used Components",
        ""
    ]

    # 排序組件
    sorted_comps = sorted(
        knowledge['components'].items(),
        key=lambda x: -x[1].get('usage_count', 0)
    )[:20]

    for guid, data in sorted_comps:
        names = data.get('names', ['Unknown'])
        count = data.get('usage_count', 0)
        inputs = data.get('inputs', {})
        outputs = data.get('outputs', {})

        lines.append(f"### {names[0]} (used {count} times)")
        lines.append(f"- GUID: `{guid}`")

        if inputs:
            lines.append("- Inputs:")
            for nick, full_names in inputs.items():
                lines.append(f"  - `{nick}`: {full_names}")

        if outputs:
            lines.append("- Outputs:")
            for nick, full_names in outputs.items():
                lines.append(f"  - `{nick}`: {full_names}")

        lines.append("")

    lines.extend([
        "## Top 20 Connection Patterns",
        ""
    ])

    sorted_patterns = sorted(
        knowledge['connection_patterns'].items(),
        key=lambda x: -x[1]
    )[:20]

    for pattern, count in sorted_patterns:
        lines.append(f"- `{pattern}` ({count} times)")

    return "\n".join(lines)


# CLI 介面
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python knowledge_extractor.py <ghx_folder> [output.json] [--report]")
        print("\nExamples:")
        print("  python knowledge_extractor.py ./ghx_samples/")
        print("  python knowledge_extractor.py ./ghx_samples/ knowledge.json")
        print("  python knowledge_extractor.py ./ghx_samples/ knowledge.json --report")
        sys.exit(1)

    ghx_folder = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    generate_report_flag = '--report' in sys.argv

    # 解析
    parser = GHXParser()
    docs = parser.batch_parse(ghx_folder)

    if not docs:
        print("No documents parsed successfully.")
        sys.exit(1)

    # 萃取知識
    extractor = KnowledgeExtractor()
    knowledge = extractor.extract(docs)

    # 輸出
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)
        print(f"Knowledge saved to: {output_path}")

    if generate_report_flag:
        report = generate_report(knowledge)
        report_path = output_path.replace('.json', '_report.md') if output_path else 'knowledge_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {report_path}")

    # 顯示摘要
    print(f"\n=== Knowledge Summary ===")
    print(f"Component types: {knowledge['statistics']['total_components']}")
    print(f"Connection patterns: {knowledge['statistics']['total_patterns']}")
    print("\nTop 5 components:")
    sorted_comps = sorted(
        knowledge['components'].items(),
        key=lambda x: -x[1].get('usage_count', 0)
    )[:5]
    for guid, data in sorted_comps:
        names = data.get('names', ['Unknown'])
        print(f"  - {names[0]}: {data.get('usage_count', 0)} times")
