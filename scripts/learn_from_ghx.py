#!/usr/bin/env python3
"""
從 .ghx 範例學習 - Learn from GHX Examples

掃描 .ghx 檔案，收集：
1. 組件 GUID 和參數名
2. 設計模式 (組件組合)
3. 常用連接模式

使用方式：
    python scripts/learn_from_ghx.py gh_learning/ghx_samples/
    python scripts/learn_from_ghx.py gh_learning/ghx_samples/ --output learned_guids.json

2026-01-23
"""

import xml.etree.ElementTree as ET
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class LearnedComponent:
    """學習到的組件資訊"""
    guid: str
    name: str
    category: str
    subcategory: str
    inputs: List[str]
    outputs: List[str]
    seen_count: int
    source_files: List[str]


class GHXLearner:
    """從 .ghx 檔案學習組件資訊"""

    def __init__(self):
        self.components: Dict[str, LearnedComponent] = {}
        self.connections: List[Dict] = []
        self.patterns: Dict[str, int] = defaultdict(int)  # 組合模式計數
        self.param_mappings: Dict[str, Dict] = {}  # GUID → 參數名

    def scan_directory(self, directory: str) -> Dict:
        """掃描目錄中所有 .ghx 檔案"""
        dir_path = Path(directory)
        ghx_files = list(dir_path.rglob("*.ghx"))

        print(f"\n{'='*60}")
        print(f"GHX 學習器 - 掃描 {len(ghx_files)} 個檔案")
        print(f"{'='*60}\n")

        for i, ghx_file in enumerate(ghx_files, 1):
            print(f"[{i}/{len(ghx_files)}] {ghx_file.name}...")
            try:
                self._parse_ghx(str(ghx_file))
            except Exception as e:
                print(f"   ⚠️ 解析失敗: {e}")

        return self._generate_report()

    def _parse_ghx(self, filepath: str):
        """解析單個 .ghx 檔案"""
        tree = ET.parse(filepath)
        root = tree.getroot()

        # 找到 DefinitionObjects
        for chunk in root.iter('chunk'):
            if chunk.get('name') == 'DefinitionObjects':
                self._parse_objects(chunk, filepath)

    def _parse_objects(self, def_objects: ET.Element, source_file: str):
        """解析物件定義"""
        for obj in def_objects.iter('chunk'):
            if obj.get('name') == 'Object':
                self._parse_component(obj, source_file)

    def _parse_component(self, obj: ET.Element, source_file: str):
        """解析單個組件"""
        # 取得組件 GUID
        guid = None
        name = None
        category = ""
        subcategory = ""
        inputs = []
        outputs = []

        for item in obj.iter('item'):
            item_name = item.get('name', '')

            if item_name == 'GUID':
                guid = item.text
            elif item_name == 'Name':
                name = item.text
            elif item_name == 'NickName':
                if not name:
                    name = item.text
            elif item_name == 'Category':
                category = item.text or ""
            elif item_name == 'SubCategory':
                subcategory = item.text or ""

        # 解析參數
        for chunk in obj.iter('chunk'):
            chunk_name = chunk.get('name', '')
            if chunk_name == 'param_input':
                param_name = self._get_param_name(chunk)
                if param_name:
                    inputs.append(param_name)
            elif chunk_name == 'param_output':
                param_name = self._get_param_name(chunk)
                if param_name:
                    outputs.append(param_name)

        if guid and name:
            self._add_component(guid, name, category, subcategory,
                              inputs, outputs, source_file)

    def _get_param_name(self, param_chunk: ET.Element) -> Optional[str]:
        """取得參數名稱"""
        for item in param_chunk.iter('item'):
            if item.get('name') == 'Name':
                return item.text
            elif item.get('name') == 'NickName':
                return item.text
        return None

    def _add_component(self, guid: str, name: str, category: str,
                      subcategory: str, inputs: List[str],
                      outputs: List[str], source_file: str):
        """添加或更新組件資訊"""
        if guid in self.components:
            comp = self.components[guid]
            comp.seen_count += 1
            if source_file not in comp.source_files:
                comp.source_files.append(source_file)
            # 合併參數 (取最完整的)
            if len(inputs) > len(comp.inputs):
                comp.inputs = inputs
            if len(outputs) > len(comp.outputs):
                comp.outputs = outputs
        else:
            self.components[guid] = LearnedComponent(
                guid=guid,
                name=name,
                category=category,
                subcategory=subcategory,
                inputs=inputs,
                outputs=outputs,
                seen_count=1,
                source_files=[source_file]
            )

    def _generate_report(self) -> Dict:
        """生成學習報告"""
        # 按使用頻率排序
        sorted_comps = sorted(
            self.components.values(),
            key=lambda x: x.seen_count,
            reverse=True
        )

        # 生成 GUID Registry 格式
        verified_guids = {}
        param_names = {}

        for comp in sorted_comps:
            # 使用 (name, category) 作為 key
            key = f"{comp.name}|{comp.category}"
            verified_guids[key] = comp.guid

            # 參數名映射
            if comp.inputs or comp.outputs:
                param_names[comp.guid] = {
                    "inputs": comp.inputs,
                    "outputs": comp.outputs
                }

        report = {
            "summary": {
                "total_components": len(self.components),
                "unique_categories": len(set(c.category for c in self.components.values())),
            },
            "top_20_components": [
                {
                    "name": c.name,
                    "guid": c.guid,
                    "category": c.category,
                    "seen_count": c.seen_count,
                    "inputs": c.inputs,
                    "outputs": c.outputs
                }
                for c in sorted_comps[:20]
            ],
            "verified_guids": verified_guids,
            "param_names": param_names,
            "all_components": [asdict(c) for c in sorted_comps]
        }

        return report

    def print_summary(self, report: Dict):
        """印出摘要"""
        print(f"\n{'='*60}")
        print(f"學習完成！")
        print(f"{'='*60}")
        print(f"   組件總數: {report['summary']['total_components']}")
        print(f"   類別數: {report['summary']['unique_categories']}")
        print(f"\n最常用的 20 個組件:")
        print(f"{'-'*60}")

        for i, comp in enumerate(report['top_20_components'], 1):
            inputs = ', '.join(comp['inputs'][:3]) if comp['inputs'] else '-'
            outputs = ', '.join(comp['outputs'][:3]) if comp['outputs'] else '-'
            print(f"{i:2}. {comp['name']:<25} ({comp['seen_count']:2}x)")
            print(f"    GUID: {comp['guid'][:20]}...")
            print(f"    輸入: {inputs}")
            print(f"    輸出: {outputs}")
            print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='從 .ghx 檔案學習')
    parser.add_argument('directory', help='.ghx 檔案目錄')
    parser.add_argument('--output', '-o', default='learned_guids.json',
                       help='輸出檔案名')

    args = parser.parse_args()

    learner = GHXLearner()
    report = learner.scan_directory(args.directory)
    learner.print_summary(report)

    # 儲存結果
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已儲存到 {output_path}")

    # 生成可複製到 guid_registry.py 的格式
    print(f"\n{'='*60}")
    print("可複製到 guid_registry.py 的 VERIFIED_GUIDS:")
    print(f"{'='*60}")
    for comp in report['top_20_components']:
        name = comp['name']
        cat = comp['category']
        guid = comp['guid']
        print(f'        ("{name}", "{cat}"): "{guid}",')


if __name__ == '__main__':
    main()
