#!/usr/bin/env python3
"""
Pattern Library - 可學習的設計模式庫

功能：
1. 搜索相關 Pattern
2. 記錄使用者回饋
3. 更新優雅分數
4. A/B 比對支援
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PatternMatch:
    """Pattern 搜索結果"""
    pattern_id: str
    name: str
    description: str
    score: float
    elegance_score: float
    usage_count: int
    keywords: List[str]
    mermaid_path: Optional[str] = None


class PatternLibrary:
    """Pattern Library 管理器"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            # 預設使用專案根目錄的 patterns/
            self.base_path = Path(__file__).parent.parent / "patterns"
        else:
            self.base_path = Path(base_path)

        self.index_path = self.base_path / "index.json"
        self.patterns: Dict = {}
        self._load_index()

    def _load_index(self):
        """載入索引"""
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self.patterns = json.load(f)
            print(f"[PatternLibrary] 載入 {len(self.patterns)} 個 Pattern")
        else:
            self.patterns = {}
            print(f"[PatternLibrary] 警告: index.json 不存在")

    def _save_index(self):
        """儲存索引"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.patterns, f, ensure_ascii=False, indent=2)

    def search(self, query: str, top_k: int = 3) -> List[PatternMatch]:
        """
        搜索相關 Pattern

        Args:
            query: 搜索關鍵字（支援中英文）
            top_k: 返回前 k 個結果

        Returns:
            PatternMatch 列表，按分數排序
        """
        query_lower = query.lower()
        query_terms = query_lower.split()

        results = []

        for pattern_id, info in self.patterns.items():
            score = 0

            # 名稱匹配 (權重最高)
            name = info.get('name', '').lower()
            for term in query_terms:
                if term in name:
                    score += 20

            # 關鍵字匹配
            keywords = info.get('keywords', [])
            for keyword in keywords:
                keyword_lower = keyword.lower()
                for term in query_terms:
                    if term in keyword_lower or keyword_lower in term:
                        score += 10

            # 描述匹配
            desc = info.get('description', '').lower()
            for term in query_terms:
                if term in desc:
                    score += 5

            # 優雅分數加成
            elegance = info.get('metadata', {}).get('elegance_score', 0)
            score += elegance * 2  # 每星加 2 分

            if score > 0:
                # 取得 Mermaid 檔案路徑
                mermaid_path = self.base_path / pattern_id / "flowchart.mmd"

                results.append(PatternMatch(
                    pattern_id=pattern_id,
                    name=info.get('name', pattern_id),
                    description=info.get('description', ''),
                    score=score,
                    elegance_score=elegance,
                    usage_count=info.get('metadata', {}).get('usage_count', 0),
                    keywords=keywords,
                    mermaid_path=str(mermaid_path) if mermaid_path.exists() else None
                ))

        # 排序並返回 top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """取得完整 Pattern 資料"""
        pattern_path = self.base_path / pattern_id / "pattern.json"
        if pattern_path.exists():
            with open(pattern_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_mermaid(self, pattern_id: str) -> Optional[str]:
        """取得 Mermaid flowchart"""
        mermaid_path = self.base_path / pattern_id / "flowchart.mmd"
        if mermaid_path.exists():
            with open(mermaid_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def record_feedback(
        self,
        pattern_id: str,
        feedback_type: str,  # 'positive', 'negative', 'modified', 'used'
        comment: str = "",
        before_after: Optional[Tuple[Dict, Dict]] = None
    ) -> bool:
        """
        記錄使用者回饋

        Args:
            pattern_id: Pattern ID
            feedback_type: 回饋類型
                - 'positive': 👍 優雅 → elegance_score += 0.5
                - 'negative': 👎 不好 → 記錄負面樣本
                - 'modified': ✏️ 修改 → 記錄 before/after
                - 'used': ➡️ 繼續 → usage_count += 1

        Returns:
            是否成功記錄
        """
        if pattern_id not in self.patterns:
            print(f"[PatternLibrary] 找不到 Pattern: {pattern_id}")
            return False

        info = self.patterns[pattern_id]
        metadata = info.get('metadata', {})

        # 更新分數
        if feedback_type == 'positive':
            current_score = metadata.get('elegance_score', 0)
            metadata['elegance_score'] = min(5.0, current_score + 0.5)
            print(f"   ⭐ {info['name']} elegance_score: {current_score} → {metadata['elegance_score']}")

        elif feedback_type == 'used':
            metadata['usage_count'] = metadata.get('usage_count', 0) + 1
            print(f"   📊 {info['name']} usage_count: {metadata['usage_count']}")

        elif feedback_type == 'negative':
            # 記錄到 pattern.json 的 feedback_history
            self._add_feedback_history(pattern_id, {
                'type': 'negative',
                'comment': comment,
                'timestamp': datetime.now().isoformat()
            })
            print(f"   👎 記錄負面回饋: {comment}")

        elif feedback_type == 'modified' and before_after:
            self._add_feedback_history(pattern_id, {
                'type': 'modified',
                'before': before_after[0],
                'after': before_after[1],
                'comment': comment,
                'timestamp': datetime.now().isoformat()
            })
            print(f"   ✏️ 記錄修改: {comment}")

        info['metadata'] = metadata
        self._save_index()
        return True

    def _add_feedback_history(self, pattern_id: str, feedback: Dict):
        """添加回饋歷史到 pattern.json"""
        pattern_path = self.base_path / pattern_id / "pattern.json"
        if pattern_path.exists():
            with open(pattern_path, 'r', encoding='utf-8') as f:
                pattern = json.load(f)

            if 'feedback_history' not in pattern:
                pattern['feedback_history'] = []

            pattern['feedback_history'].append(feedback)

            with open(pattern_path, 'w', encoding='utf-8') as f:
                json.dump(pattern, f, ensure_ascii=False, indent=2)

    def add_pattern(
        self,
        pattern_id: str,
        name: str,
        description: str,
        keywords: List[str],
        pattern_data: Dict,
        mermaid: str = None
    ) -> str:
        """
        添加新 Pattern

        Returns:
            Pattern ID
        """
        # 建立目錄
        pattern_dir = self.base_path / pattern_id
        pattern_dir.mkdir(parents=True, exist_ok=True)

        # 儲存 pattern.json
        pattern_path = pattern_dir / "pattern.json"
        with open(pattern_path, 'w', encoding='utf-8') as f:
            json.dump(pattern_data, f, ensure_ascii=False, indent=2)

        # 儲存 Mermaid
        if mermaid:
            mermaid_path = pattern_dir / "flowchart.mmd"
            with open(mermaid_path, 'w', encoding='utf-8') as f:
                f.write(mermaid)

        # 更新索引
        self.patterns[pattern_id] = {
            'name': name,
            'description': description,
            'keywords': keywords,
            'component_count': len(pattern_data.get('components', [])),
            'source_file': pattern_data.get('metadata', {}).get('script_path', ''),
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'elegance_score': 0,
                'usage_count': 0,
                'verified': False
            }
        }
        self._save_index()

        print(f"[PatternLibrary] 新增 Pattern: {pattern_id}")
        return pattern_id

    def print_search_results(self, results: List[PatternMatch]):
        """印出搜索結果"""
        if not results:
            print("\n❌ 沒有找到相關的 Pattern")
            return

        print("\n" + "=" * 60)
        print("Pattern Library 搜索結果")
        print("=" * 60)

        for i, r in enumerate(results, 1):
            stars = "⭐" * int(r.elegance_score)
            print(f"\n{i}. {r.name}")
            print(f"   分數: {r.score:.1f} | 優雅: {stars} ({r.elegance_score}/5)")
            print(f"   使用次數: {r.usage_count}")
            print(f"   描述: {r.description[:50]}...")
            print(f"   關鍵字: {', '.join(r.keywords[:5])}")


# 便捷函數
_library = None


def get_library() -> PatternLibrary:
    """取得全域 Pattern Library 實例"""
    global _library
    if _library is None:
        _library = PatternLibrary()
    return _library


def search_patterns(query: str, top_k: int = 3) -> List[PatternMatch]:
    """快速搜索 Pattern"""
    return get_library().search(query, top_k)


def record_feedback(pattern_id: str, feedback_type: str, **kwargs) -> bool:
    """快速記錄回饋"""
    return get_library().record_feedback(pattern_id, feedback_type, **kwargs)


if __name__ == "__main__":
    # 測試
    library = PatternLibrary()

    # 搜索測試
    print("\n測試搜索 '螺旋樓梯':")
    results = library.search("螺旋樓梯")
    library.print_search_results(results)

    print("\n測試搜索 'spiral stair':")
    results = library.search("spiral stair")
    library.print_search_results(results)

    print("\n測試搜索 'helix':")
    results = library.search("helix")
    library.print_search_results(results)
