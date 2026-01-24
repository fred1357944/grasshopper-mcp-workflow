"""
GH_MCP Semantic Search - 語義搜索模組

使用 sentence-transformers 和 FAISS 進行向量化語義搜索，
支持自然語言查詢連接模式和組件。

這是 Claude 長文記憶增強計劃的進階組件 (Phase 3 - P2)。

依賴安裝：
```bash
pip install sentence-transformers faiss-cpu
```

使用方式：
```python
from grasshopper_mcp.semantic_search import GHSemanticSearch

search = GHSemanticSearch()
search.build_index()  # 構建索引（首次使用）

# 語義搜索
results = search.search("做一個結構分析")
for r in results:
    print(f"{r['name']}: {r['score']:.2f}")
```

2026-01-24
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 嘗試導入可選依賴
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    logger.warning(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers"
    )

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning(
        "faiss not installed. "
        "Install with: pip install faiss-cpu"
    )


class GHSemanticSearch:
    """
    Grasshopper 語義搜索引擎

    使用 sentence-transformers 將連接模式和組件描述向量化，
    然後使用 FAISS 進行高效的相似度搜索。

    Features:
    - 支持中英文混合查詢
    - 自動構建和更新索引
    - 返回相似度分數
    - 支持過濾和排序
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # 快速、高效的多語言模型

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        config_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        初始化語義搜索引擎

        Args:
            model_name: sentence-transformers 模型名稱
            config_dir: 配置目錄路徑
            cache_dir: 索引緩存目錄
        """
        self.model_name = model_name
        self._model = None
        self._index = None
        self._documents: List[Dict] = []
        self._embeddings = None

        # 設置路徑
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

        if cache_dir is None:
            cache_dir = Path(__file__).parent / ".cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self._index_path = self.cache_dir / "semantic_index.faiss"
        self._docs_path = self.cache_dir / "semantic_docs.json"

    @property
    def model(self):
        """延遲加載模型"""
        if self._model is None:
            if not HAS_SENTENCE_TRANSFORMERS:
                raise ImportError(
                    "sentence-transformers is required for semantic search. "
                    "Install with: pip install sentence-transformers"
                )
            logger.info(f"Loading model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _load_patterns(self) -> List[Dict]:
        """從 connection_patterns.json 載入連接模式"""
        patterns_path = self.config_dir / "connection_patterns.json"
        if not patterns_path.exists():
            logger.warning(f"Patterns file not found: {patterns_path}")
            return []

        with open(patterns_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        for name, pattern in data.get("patterns", {}).items():
            # 構建搜索文本
            keywords = pattern.get("keywords", [])
            description = pattern.get("description", "")
            category = pattern.get("category", "")

            search_text = f"{name} {description} {category} {' '.join(keywords)}"

            documents.append({
                "id": f"pattern:{name}",
                "type": "pattern",
                "name": name,
                "description": description,
                "category": category,
                "keywords": keywords,
                "search_text": search_text,
                "data": pattern
            })

        return documents

    def _load_components(self) -> List[Dict]:
        """從 trusted_guids.json 載入組件"""
        guids_path = self.config_dir / "trusted_guids.json"
        if not guids_path.exists():
            logger.warning(f"GUIDs file not found: {guids_path}")
            return []

        with open(guids_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        for name, info in data.get("components", {}).items():
            # 構建搜索文本
            category = info.get("category", "")
            subcategory = info.get("subcategory", "")
            note = info.get("note", "")
            inputs = info.get("inputs", [])
            outputs = info.get("outputs", [])

            search_text = (
                f"{name} {category} {subcategory} {note} "
                f"inputs: {' '.join(inputs)} outputs: {' '.join(outputs)}"
            )

            documents.append({
                "id": f"component:{name}",
                "type": "component",
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "search_text": search_text,
                "data": info
            })

        return documents

    def build_index(self, force_rebuild: bool = False) -> bool:
        """
        構建語義搜索索引

        Args:
            force_rebuild: 是否強制重建索引

        Returns:
            是否成功構建索引
        """
        if not HAS_FAISS:
            raise ImportError(
                "faiss is required for semantic search. "
                "Install with: pip install faiss-cpu"
            )

        # 檢查緩存
        if not force_rebuild and self._index_path.exists() and self._docs_path.exists():
            logger.info("Loading cached index...")
            return self._load_cached_index()

        # 載入文檔
        logger.info("Loading documents...")
        patterns = self._load_patterns()
        components = self._load_components()
        self._documents = patterns + components

        if not self._documents:
            logger.warning("No documents to index")
            return False

        # 構建嵌入向量
        logger.info(f"Building embeddings for {len(self._documents)} documents...")
        texts = [doc["search_text"] for doc in self._documents]
        self._embeddings = self.model.encode(texts, show_progress_bar=True)

        # 構建 FAISS 索引
        logger.info("Building FAISS index...")
        dimension = self._embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)  # 內積相似度
        faiss.normalize_L2(self._embeddings)  # 歸一化
        self._index.add(self._embeddings)

        # 保存緩存
        self._save_cached_index()

        logger.info("Index built successfully")
        return True

    def _load_cached_index(self) -> bool:
        """載入緩存的索引"""
        try:
            self._index = faiss.read_index(str(self._index_path))
            with open(self._docs_path, 'r', encoding='utf-8') as f:
                self._documents = json.load(f)
            logger.info(f"Loaded {len(self._documents)} documents from cache")
            return True
        except Exception as e:
            logger.error(f"Failed to load cached index: {e}")
            return False

    def _save_cached_index(self):
        """保存索引到緩存"""
        try:
            faiss.write_index(self._index, str(self._index_path))
            with open(self._docs_path, 'w', encoding='utf-8') as f:
                json.dump(self._documents, f, ensure_ascii=False, indent=2)
            logger.info("Index cached successfully")
        except Exception as e:
            logger.error(f"Failed to save index cache: {e}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        語義搜索

        Args:
            query: 搜索查詢（支持中英文）
            top_k: 返回結果數量
            doc_type: 過濾文檔類型 ("pattern" 或 "component")
            min_score: 最低相似度閾值

        Returns:
            搜索結果列表，每個結果包含：
            - name: 文檔名稱
            - type: 文檔類型
            - score: 相似度分數 (0-1)
            - data: 原始數據
        """
        if self._index is None:
            self.build_index()

        if self._index is None:
            return []

        # 編碼查詢
        query_vec = self.model.encode([query])
        faiss.normalize_L2(query_vec)

        # 搜索
        scores, indices = self._index.search(query_vec, top_k * 2)  # 多取一些以便過濾

        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0 or idx >= len(self._documents):
                continue

            doc = self._documents[idx]

            # 過濾類型
            if doc_type and doc.get("type") != doc_type:
                continue

            # 過濾分數
            if score < min_score:
                continue

            results.append({
                "name": doc["name"],
                "type": doc["type"],
                "score": float(score),
                "category": doc.get("category"),
                "description": doc.get("description"),
                "data": doc.get("data", {})
            })

            if len(results) >= top_k:
                break

        return results

    def search_patterns(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索連接模式"""
        return self.search(query, top_k=top_k, doc_type="pattern")

    def search_components(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索組件"""
        return self.search(query, top_k=top_k, doc_type="component")

    def get_similar_patterns(self, pattern_name: str, top_k: int = 3) -> List[Dict]:
        """獲取相似的連接模式"""
        # 找到指定模式
        target_doc = None
        for doc in self._documents:
            if doc["type"] == "pattern" and doc["name"] == pattern_name:
                target_doc = doc
                break

        if not target_doc:
            return []

        # 使用模式描述進行搜索
        return self.search_patterns(target_doc["search_text"], top_k=top_k + 1)[1:]


# 單例實例
_search_instance: Optional[GHSemanticSearch] = None


def get_semantic_search() -> GHSemanticSearch:
    """獲取全局語義搜索實例"""
    global _search_instance
    if _search_instance is None:
        _search_instance = GHSemanticSearch()
    return _search_instance


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """便捷搜索函數"""
    return get_semantic_search().search(query, top_k=top_k)


# CLI 入口
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python semantic_search.py <query>")
        print("\nExamples:")
        print("  python semantic_search.py '結構分析'")
        print("  python semantic_search.py 'wasp aggregation'")
        print("  python semantic_search.py 'form finding physics'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    print(f"\n=== 語義搜索: '{query}' ===\n")

    search = GHSemanticSearch()
    search.build_index()

    results = search.search(query, top_k=10)

    if not results:
        print("未找到匹配結果")
    else:
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['type']}] {r['name']}")
            print(f"   Score: {r['score']:.3f}")
            if r.get('description'):
                print(f"   {r['description']}")
            print()
