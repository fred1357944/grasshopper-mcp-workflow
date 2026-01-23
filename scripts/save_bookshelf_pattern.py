#!/usr/bin/env python3
"""
保存工業風書架到 Pattern Library

將 GH_WIP/placement_info.json 和 component_info.mmd 儲存為可重用模式

2026-01-23
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.pattern_library import PatternLibrary


def save_bookshelf_pattern():
    """保存工業風書架到 Pattern Library"""

    # 載入配置
    config_path = Path(__file__).parent.parent / 'GH_WIP' / 'placement_info.json'
    mermaid_path = Path(__file__).parent.parent / 'GH_WIP' / 'component_info.mmd'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    mermaid = ""
    if mermaid_path.exists():
        with open(mermaid_path, 'r', encoding='utf-8') as f:
            mermaid = f.read()

    # 準備 Pattern 資料
    pattern_id = "industrial-bookshelf"
    name = "工業風書架 (Industrial Bookshelf)"
    description = """
可調整的工業風開放式書架設計。
- 尺寸: 可調整寬度、高度、深度
- 層數: 2-10 層可調
- 結構: 金屬圓管支架 + 木質層板 + 金屬托架
- 風格: 工業風、極簡現代

特點:
- 所有參數化：一個 Slider 控制一個維度
- 對稱設計：左右支架/托架自動鏡像
- 結構合理：托架支撐層板，支架承重
    """.strip()

    keywords = [
        # 中文
        "書架", "工業風", "金屬", "層板", "儲物架",
        "開放式", "展示架", "收納", "極簡",
        # 英文
        "bookshelf", "industrial", "metal", "shelf", "storage",
        "open", "display", "modern", "minimalist",
        # 技術
        "parametric", "adjustable", "modular"
    ]

    # 添加元資料
    config['metadata'] = {
        'pattern_id': pattern_id,
        'name': name,
        'version': '1.0.0',
        'created_at': '2026-01-23',
        'author': 'GH_MCP Workflow',
        'script_path': 'scripts/deploy_bookshelf.py',
        'default_values': {
            'width': 80,
            'height': 180,
            'depth': 30,
            'shelf_count': 5,
            'shelf_thickness': 2,
            'support_radius': 1.5,
            'bracket_radius': 0.8,
            'inset': 5
        },
        'lessons_learned': [
            "Line 組件需用 Curve 類別 GUID (31957fba-b08b-45f9-9ec0-5f9e52d3236b)",
            "XY Plane 正確 GUID: 5df6a8c1-de5e-4841-8089-41a95c741c5a",
            "參數名使用全名 (Result, Point, Series) 而非縮寫 (R, Pt, S)"
        ]
    }

    # 初始化 Pattern Library
    library = PatternLibrary()

    # 添加 Pattern
    library.add_pattern(
        pattern_id=pattern_id,
        name=name,
        description=description,
        keywords=keywords,
        pattern_data=config,
        mermaid=mermaid
    )

    print(f"\n{'='*60}")
    print(f"✅ 已保存 Pattern: {name}")
    print(f"{'='*60}")
    print(f"   ID: {pattern_id}")
    print(f"   組件數: {len(config.get('components', []))}")
    print(f"   連接數: {len(config.get('connections', []))}")
    print(f"   關鍵字: {len(keywords)}")
    print(f"   路徑: patterns/{pattern_id}/")
    print(f"{'='*60}\n")

    # 測試搜索
    print("測試搜索...")
    results = library.search("書架")
    library.print_search_results(results)

    return pattern_id


if __name__ == '__main__':
    save_bookshelf_pattern()
