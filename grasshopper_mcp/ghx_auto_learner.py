"""
GHX Auto-Learner - 自動從 GHX 文件學習設計模式
================================================================

Pipeline:
1. GHX Parser → 結構化數據
2. Pattern Extractor → 連接模式提取
3. LLM Annotator → 語義標註 (設計意圖)
4. Knowledge Integration → 更新知識庫

Usage:
    learner = GHXAutoLearner()
    results = await learner.learn_from_directory("gh_learning/ghx_samples")
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from .ghx_parser import GHXParser
from .models import GHDocument

# 可選依賴：sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 資料結構
# ============================================================

@dataclass
class ExtractedPattern:
    """從 GHX 提取的連接模式"""
    pattern_id: str
    source_file: str

    # 結構資訊
    components: List[Dict[str, Any]]  # [{"name": ..., "type": ..., "guid": ...}]
    connections: List[Dict[str, Any]]  # [{"from": ..., "to": ..., "params": ...}]

    # 統計
    component_count: int = 0
    connection_count: int = 0
    plugin_components: List[str] = field(default_factory=list)

    # LLM 標註 (後填充)
    design_intent: str = ""
    semantic_tags: List[str] = field(default_factory=list)
    difficulty_level: str = "medium"  # easy/medium/advanced
    confidence: float = 0.0


@dataclass
class LearningResult:
    """學習結果"""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    patterns_extracted: int = 0
    new_knowledge: int = 0

    errors: List[Dict[str, str]] = field(default_factory=list)
    patterns: List[ExtractedPattern] = field(default_factory=list)


@dataclass
class SearchResult:
    """語義搜索結果"""
    pattern: ExtractedPattern
    score: float
    source_file: str = ""

    def __post_init__(self):
        if not self.source_file and self.pattern:
            self.source_file = self.pattern.source_file


# ============================================================
# Embedding Index (語義搜索)
# ============================================================

class EmbeddingIndex:
    """
    設計意圖語義索引

    使用 sentence-transformers 將設計意圖轉為向量，
    支援語義搜索（如「螺旋結構」找到相關 pattern）

    Usage:
        index = EmbeddingIndex()
        index.add_pattern(pattern)
        results = index.search("螺旋樓梯", top_k=5)
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = None, cache_dir: str = "config"):
        """
        初始化 Embedding Index

        Args:
            model_name: sentence-transformers 模型名稱
            cache_dir: 索引快取目錄
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_dir = Path(cache_dir)
        self.index_path = self.cache_dir / "pattern_embeddings.json"

        self.model = None
        self.patterns: List[ExtractedPattern] = []
        self.embeddings: Optional[np.ndarray] = None
        self.texts: List[str] = []  # 用於搜索的文本

        self._initialized = False

    def _ensure_model(self):
        """確保模型已載入"""
        if self.model is not None:
            return

        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self._initialized = True

    def _pattern_to_text(self, pattern: ExtractedPattern) -> str:
        """將 pattern 轉為可搜索的文本"""
        parts = [
            pattern.design_intent,
            " ".join(pattern.semantic_tags),
            pattern.pattern_id.replace("_", " "),
        ]

        # 加入組件名稱
        component_names = [c["name"] for c in pattern.components[:10]]
        parts.append(" ".join(component_names))

        return " ".join(parts)

    def add_pattern(self, pattern: ExtractedPattern):
        """
        添加 pattern 到索引

        Args:
            pattern: 提取的模式
        """
        self._ensure_model()

        text = self._pattern_to_text(pattern)
        embedding = self.model.encode([text])[0]

        self.patterns.append(pattern)
        self.texts.append(text)

        if self.embeddings is None:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])

    def add_patterns(self, patterns: List[ExtractedPattern]):
        """批量添加 patterns"""
        self._ensure_model()

        texts = [self._pattern_to_text(p) for p in patterns]
        embeddings = self.model.encode(texts)

        self.patterns.extend(patterns)
        self.texts.extend(texts)

        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        語義搜索

        Args:
            query: 搜索查詢（自然語言）
            top_k: 返回前 k 個結果
            min_score: 最低相似度閾值

        Returns:
            SearchResult 列表，按相似度降序排列
        """
        if self.embeddings is None or len(self.patterns) == 0:
            return []

        self._ensure_model()

        query_emb = self.model.encode([query])[0]

        # 計算餘弦相似度
        similarities = np.dot(self.embeddings, query_emb) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_emb)
        )

        # 排序並過濾
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for i in top_indices:
            score = float(similarities[i])
            if score >= min_score:
                results.append(SearchResult(
                    pattern=self.patterns[i],
                    score=score,
                ))

        return results

    def save(self, path: str = None):
        """保存索引到 JSON 文件（安全格式，不使用 pickle）"""
        save_path = Path(path) if path else self.index_path

        if self.embeddings is None:
            logger.warning("No embeddings to save")
            return

        # 保存為 JSON 格式
        data = {
            "_meta": {
                "model": self.model_name,
                "total_patterns": len(self.patterns),
                "embedding_dim": self.embeddings.shape[1] if self.embeddings is not None else 0,
                "updated_at": datetime.now().isoformat(),
            },
            "patterns": [],
        }

        for i, p in enumerate(self.patterns):
            data["patterns"].append({
                "pattern_id": p.pattern_id,
                "source_file": p.source_file,
                "design_intent": p.design_intent,
                "semantic_tags": p.semantic_tags,
                "difficulty_level": p.difficulty_level,
                "confidence": p.confidence,
                "component_count": p.component_count,
                "connection_count": p.connection_count,
                "text": self.texts[i],
                "embedding": self.embeddings[i].tolist(),
            })

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved index with {len(self.patterns)} patterns to {save_path}")

    def load(self, path: str = None) -> bool:
        """
        從 JSON 文件載入索引

        Returns:
            是否成功載入
        """
        load_path = Path(path) if path else self.index_path

        if not load_path.exists():
            logger.info(f"Index file not found: {load_path}")
            return False

        try:
            with open(load_path, encoding="utf-8") as f:
                data = json.load(f)

            self.patterns = []
            self.texts = []
            embeddings_list = []

            for p_dict in data["patterns"]:
                pattern = ExtractedPattern(
                    pattern_id=p_dict["pattern_id"],
                    source_file=p_dict["source_file"],
                    components=[],
                    connections=[],
                    component_count=p_dict["component_count"],
                    connection_count=p_dict["connection_count"],
                    design_intent=p_dict["design_intent"],
                    semantic_tags=p_dict["semantic_tags"],
                    difficulty_level=p_dict["difficulty_level"],
                    confidence=p_dict["confidence"],
                )
                self.patterns.append(pattern)
                self.texts.append(p_dict["text"])
                embeddings_list.append(p_dict["embedding"])

            self.embeddings = np.array(embeddings_list)

            logger.info(f"Loaded index with {len(self.patterns)} patterns from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def __len__(self) -> int:
        return len(self.patterns)


# ============================================================
# Pattern Extractor
# ============================================================

class PatternExtractor:
    """從 GHDocument 提取連接模式"""

    # 已知插件組件前綴
    PLUGIN_PREFIXES = ["Wasp_", "Karamba", "Kangaroo", "Ladybug", "Honeybee"]

    def extract(self, doc: GHDocument, source_file: str) -> ExtractedPattern:
        """
        提取連接模式

        Args:
            doc: 解析後的 GHDocument
            source_file: 原始文件路徑

        Returns:
            ExtractedPattern
        """
        pattern_id = Path(source_file).stem

        # 提取組件資訊
        components = []
        plugin_components = []

        for guid, comp in doc.components.items():
            comp_info = {
                "instance_guid": guid,
                "component_guid": comp.component_guid,
                "name": comp.name,
                "nickname": comp.nickname,
                "category": comp.category.value,
                "inputs": [{"name": p.name, "nickname": p.nickname} for p in comp.inputs],
                "outputs": [{"name": p.name, "nickname": p.nickname} for p in comp.outputs],
            }
            components.append(comp_info)

            # 檢查是否為插件組件
            for prefix in self.PLUGIN_PREFIXES:
                if comp.name.startswith(prefix):
                    plugin_components.append(comp.name)
                    break

        # 提取連接資訊
        connections = []
        for conn in doc.connections:
            src_comp = doc.components.get(conn.source_component_id)
            tgt_comp = doc.components.get(conn.target_component_id)

            conn_info = {
                "from_component": src_comp.name if src_comp else "Unknown",
                "from_nickname": src_comp.nickname if src_comp else "?",
                "from_param": conn.source_output_name,
                "from_param_index": conn.source_output_index,
                "to_component": tgt_comp.name if tgt_comp else "Unknown",
                "to_nickname": tgt_comp.nickname if tgt_comp else "?",
                "to_param": conn.target_input_name,
                "to_param_index": conn.target_input_index,
            }
            connections.append(conn_info)

        return ExtractedPattern(
            pattern_id=pattern_id,
            source_file=source_file,
            components=components,
            connections=connections,
            component_count=len(components),
            connection_count=len(connections),
            plugin_components=plugin_components,
        )

    def to_mermaid(self, pattern: ExtractedPattern) -> str:
        """將模式轉換為 Mermaid 流程圖"""
        lines = [
            "flowchart LR",
            f"    %% Source: {pattern.source_file}",
            f"    %% Components: {pattern.component_count}, Connections: {pattern.connection_count}",
            "",
        ]

        # 組件節點 (使用 nickname 作為 ID)
        nickname_map = {}
        for comp in pattern.components:
            safe_id = comp["nickname"].replace(" ", "_").replace("-", "_")
            nickname_map[comp["instance_guid"]] = safe_id
            lines.append(f'    {safe_id}["{comp["name"]}<br/>{comp["nickname"]}"]')

        lines.append("")

        # 連接
        for conn in pattern.connections:
            src_nick = conn["from_nickname"].replace(" ", "_").replace("-", "_")
            tgt_nick = conn["to_nickname"].replace(" ", "_").replace("-", "_")
            label = f"{conn['from_param']} → {conn['to_param']}"
            lines.append(f'    {src_nick} -->|"{label}"| {tgt_nick}')

        return "\n".join(lines)


# ============================================================
# LLM Annotator (模擬/整合)
# ============================================================

class LLMAnnotator:
    """使用 LLM 進行語義標註"""

    # 設計意圖關鍵字映射
    INTENT_KEYWORDS = {
        "aggregation": ["wasp", "aggregate", "stochastic", "rule", "part"],
        "structural": ["karamba", "beam", "shell", "load", "support", "analyze"],
        "form_finding": ["kangaroo", "solver", "anchor", "spring", "pressure"],
        "environmental": ["ladybug", "honeybee", "solar", "energy", "radiation"],
        "panelization": ["panel", "divide", "grid", "pattern"],
        "mesh_processing": ["mesh", "weld", "smooth", "subdivision"],
    }

    # 難度評估
    DIFFICULTY_THRESHOLDS = {
        "easy": (0, 10),      # 0-10 組件
        "medium": (10, 30),   # 10-30 組件
        "advanced": (30, float("inf")),  # 30+ 組件
    }

    async def annotate(self, pattern: ExtractedPattern) -> ExtractedPattern:
        """
        標註模式的設計意圖

        目前使用規則推斷，未來可接入真正的 LLM API
        """
        # 1. 推斷設計意圖
        intent = self._infer_intent(pattern)
        pattern.design_intent = intent

        # 2. 生成語義標籤
        tags = self._generate_tags(pattern)
        pattern.semantic_tags = tags

        # 3. 評估難度
        difficulty = self._assess_difficulty(pattern)
        pattern.difficulty_level = difficulty

        # 4. 計算置信度
        pattern.confidence = self._calculate_confidence(pattern)

        return pattern

    def _infer_intent(self, pattern: ExtractedPattern) -> str:
        """推斷設計意圖"""
        # 從組件名稱和插件判斷
        all_names = " ".join(
            [c["name"].lower() for c in pattern.components]
        )

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in all_names:
                    return intent

        # 從文件名推斷
        file_lower = pattern.source_file.lower()
        if "aggregation" in file_lower:
            return "aggregation"
        elif "field" in file_lower:
            return "field_driven"
        elif "constraint" in file_lower:
            return "constrained_aggregation"
        elif "rule" in file_lower:
            return "rule_based"

        return "general"

    def _generate_tags(self, pattern: ExtractedPattern) -> List[str]:
        """生成語義標籤"""
        tags = []

        # 插件標籤
        for plugin in pattern.plugin_components:
            if plugin.startswith("Wasp_"):
                tags.append("wasp")
            elif "Karamba" in plugin:
                tags.append("karamba")
            elif "Kangaroo" in plugin:
                tags.append("kangaroo")

        # 功能標籤
        comp_names = [c["name"].lower() for c in pattern.components]

        if any("slider" in n for n in comp_names):
            tags.append("parametric")
        if any("mesh" in n for n in comp_names):
            tags.append("mesh")
        if any("curve" in n for n in comp_names):
            tags.append("curve")
        if any("brep" in n for n in comp_names):
            tags.append("solid")

        # 難度標籤
        tags.append(f"level:{pattern.difficulty_level}")

        return list(set(tags))

    def _assess_difficulty(self, pattern: ExtractedPattern) -> str:
        """評估難度"""
        count = pattern.component_count

        for level, (low, high) in self.DIFFICULTY_THRESHOLDS.items():
            if low <= count < high:
                return level

        return "medium"

    def _calculate_confidence(self, pattern: ExtractedPattern) -> float:
        """計算標註置信度"""
        score = 0.5  # 基礎分

        # 有連接資訊加分
        if pattern.connection_count > 0:
            score += 0.2

        # 有插件組件加分 (更容易判斷意圖)
        if pattern.plugin_components:
            score += 0.2

        # 組件數量適中加分
        if 5 <= pattern.component_count <= 30:
            score += 0.1

        return min(score, 1.0)

    async def annotate_with_llm(
        self,
        pattern: ExtractedPattern,
        llm_client: Any = None
    ) -> ExtractedPattern:
        """
        使用真正的 LLM 進行標註 (未來擴展)

        Prompt 範本:
        ```
        你是一個 Grasshopper 專家。分析以下組件連接模式，提供：
        1. 設計意圖 (一句話描述)
        2. 語義標籤 (3-5 個關鍵字)
        3. 難度等級 (easy/medium/advanced)

        組件列表:
        {components}

        連接關係:
        {connections}
        ```
        """
        if llm_client is None:
            # 降級到規則推斷
            return await self.annotate(pattern)

        # TODO: 整合 Claude/OpenAI API
        # prompt = self._build_prompt(pattern)
        # response = await llm_client.complete(prompt)
        # pattern = self._parse_llm_response(pattern, response)

        return pattern


# ============================================================
# Knowledge Integrator
# ============================================================

class KnowledgeIntegrator:
    """將學習結果整合到知識庫"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.learned_patterns_path = self.config_dir / "learned_patterns.json"
        self.connection_triplets_path = self.config_dir / "connection_triplets.json"

    def integrate(self, patterns: List[ExtractedPattern]) -> int:
        """
        整合模式到知識庫

        Returns:
            新增的知識數量
        """
        new_count = 0

        # 載入現有知識
        existing = self._load_existing()

        for pattern in patterns:
            # 跳過低置信度
            if pattern.confidence < 0.5:
                continue

            # 提取連接三元組
            triplets = self._extract_triplets(pattern)
            new_count += self._merge_triplets(triplets, existing)

            # 提取設計意圖映射
            if pattern.design_intent:
                self._add_intent_mapping(pattern, existing)

        # 儲存更新
        self._save(existing)

        return new_count

    def _load_existing(self) -> Dict[str, Any]:
        """載入現有知識"""
        result = {
            "triplets": {},  # key → {count, sources}
            "intents": {},
        }

        if self.connection_triplets_path.exists():
            with open(self.connection_triplets_path) as f:
                data = json.load(f)
                triplets_data = data.get("triplets", [])
                # 轉換 list 格式為 dict 格式
                if isinstance(triplets_data, list):
                    for t in triplets_data:
                        key = f"{t['source_component']}.{t['source_param']}→{t['target_component']}.{t['target_param']}"
                        result["triplets"][key] = {
                            "count": t.get("frequency", 1),
                            "sources": t.get("sources", []),
                        }
                else:
                    result["triplets"] = triplets_data

        if self.learned_patterns_path.exists():
            with open(self.learned_patterns_path) as f:
                data = json.load(f)
                result["intents"] = data.get("intent_patterns", {})

        return result

    def _extract_triplets(self, pattern: ExtractedPattern) -> List[Dict[str, Any]]:
        """提取連接三元組"""
        triplets = []

        for conn in pattern.connections:
            triplet = {
                "from_type": conn["from_component"],
                "from_param": conn["from_param"],
                "to_type": conn["to_component"],
                "to_param": conn["to_param"],
                "source_file": pattern.source_file,
            }
            triplets.append(triplet)

        return triplets

    def _merge_triplets(
        self,
        triplets: List[Dict[str, Any]],
        existing: Dict[str, Any]
    ) -> int:
        """合併三元組"""
        new_count = 0

        for t in triplets:
            key = f"{t['from_type']}.{t['from_param']}→{t['to_type']}.{t['to_param']}"

            if key not in existing["triplets"]:
                existing["triplets"][key] = {
                    "count": 0,
                    "sources": [],
                }
                new_count += 1

            existing["triplets"][key]["count"] += 1

            # 記錄來源 (避免重複)
            if t["source_file"] not in existing["triplets"][key]["sources"]:
                existing["triplets"][key]["sources"].append(t["source_file"])

        return new_count

    def _add_intent_mapping(
        self,
        pattern: ExtractedPattern,
        existing: Dict[str, Any]
    ):
        """添加設計意圖映射"""
        intent = pattern.design_intent

        if intent not in existing["intents"]:
            existing["intents"][intent] = {
                "patterns": [],
                "keywords": [],
            }

        # 添加模式引用
        if pattern.pattern_id not in existing["intents"][intent]["patterns"]:
            existing["intents"][intent]["patterns"].append(pattern.pattern_id)

        # 合併標籤
        for tag in pattern.semantic_tags:
            if tag not in existing["intents"][intent]["keywords"]:
                existing["intents"][intent]["keywords"].append(tag)

    def _save(self, data: Dict[str, Any]):
        """儲存更新的知識"""
        # 儲存三元組
        triplets_data = {
            "_meta": {
                "description": "從 GHX 文件自動學習的連接三元組",
                "updated_at": datetime.now().isoformat(),
                "total": len(data["triplets"]),
            },
            "triplets": data["triplets"],
        }

        with open(self.connection_triplets_path, "w", encoding="utf-8") as f:
            json.dump(triplets_data, f, indent=2, ensure_ascii=False)

        # 更新 learned_patterns.json 中的 intent_patterns
        if self.learned_patterns_path.exists():
            with open(self.learned_patterns_path) as f:
                patterns_data = json.load(f)
        else:
            patterns_data = {"_meta": {}, "patterns": []}

        patterns_data["intent_patterns"] = data["intents"]
        patterns_data["_meta"]["updated_at"] = datetime.now().isoformat()

        with open(self.learned_patterns_path, "w", encoding="utf-8") as f:
            json.dump(patterns_data, f, indent=2, ensure_ascii=False)


# ============================================================
# 主類別: GHXAutoLearner
# ============================================================

class GHXAutoLearner:
    """
    GHX 自動學習器

    完整 Pipeline:
    1. 掃描 GHX 文件
    2. 解析結構
    3. 提取模式
    4. LLM 標註
    5. 整合知識庫
    6. 建立語義索引（可選）
    """

    def __init__(self, config_dir: str = "config", enable_embedding: bool = True):
        self.config_dir = config_dir
        self.parser = GHXParser()
        self.extractor = PatternExtractor()
        self.annotator = LLMAnnotator()
        self.integrator = KnowledgeIntegrator(config_dir)

        # Embedding 索引（可選）
        self.enable_embedding = enable_embedding and HAS_SENTENCE_TRANSFORMERS
        self.embedding_index: Optional[EmbeddingIndex] = None

        if self.enable_embedding:
            self.embedding_index = EmbeddingIndex(cache_dir=config_dir)

    async def learn_from_file(self, filepath: str) -> Optional[ExtractedPattern]:
        """
        從單個 GHX 文件學習

        Args:
            filepath: GHX 文件路徑

        Returns:
            提取的模式 (帶標註)，失敗返回 None
        """
        try:
            # 1. 解析
            doc = self.parser.parse_file(filepath)

            # 2. 提取
            pattern = self.extractor.extract(doc, filepath)

            # 3. 標註
            pattern = await self.annotator.annotate(pattern)

            return pattern

        except Exception as e:
            logger.error(f"Error learning from {filepath}: {e}")
            return None

    async def learn_from_directory(
        self,
        directory: str,
        recursive: bool = True,
        integrate: bool = True
    ) -> LearningResult:
        """
        從目錄批量學習

        Args:
            directory: 目錄路徑
            recursive: 是否遞迴子目錄
            integrate: 是否整合到知識庫

        Returns:
            LearningResult
        """
        result = LearningResult()

        # 收集 GHX 文件
        dir_path = Path(directory)
        pattern = "**/*.ghx" if recursive else "*.ghx"
        ghx_files = list(dir_path.glob(pattern))

        result.total_files = len(ghx_files)
        logger.info(f"Found {len(ghx_files)} GHX files in {directory}")

        # 逐一處理
        for filepath in ghx_files:
            logger.info(f"Processing: {filepath.name}")

            pattern = await self.learn_from_file(str(filepath))

            if pattern:
                result.successful += 1
                result.patterns.append(pattern)
                result.patterns_extracted += 1
            else:
                result.failed += 1
                result.errors.append({
                    "file": str(filepath),
                    "error": "Failed to parse or extract",
                })

        # 整合到知識庫
        if integrate and result.patterns:
            result.new_knowledge = self.integrator.integrate(result.patterns)

        # 建立語義索引
        if self.enable_embedding and self.embedding_index is not None and result.patterns:
            logger.info("Building embedding index...")
            self.embedding_index.add_patterns(result.patterns)
            self.embedding_index.save()

        logger.info(
            f"Learning complete: {result.successful}/{result.total_files} files, "
            f"{result.patterns_extracted} patterns, {result.new_knowledge} new knowledge items"
        )

        return result

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        語義搜索已學習的 patterns

        Args:
            query: 自然語言查詢（如「螺旋結構」「聚集」）
            top_k: 返回前 k 個結果

        Returns:
            SearchResult 列表
        """
        if not self.enable_embedding or not self.embedding_index:
            logger.warning("Embedding index not enabled")
            return []

        # 嘗試載入已保存的索引
        if len(self.embedding_index) == 0:
            self.embedding_index.load()

        return self.embedding_index.search(query, top_k=top_k)

    def load_index(self) -> bool:
        """載入已保存的語義索引"""
        if not self.enable_embedding or not self.embedding_index:
            return False
        return self.embedding_index.load()

    def export_patterns_as_mermaid(
        self,
        patterns: List[ExtractedPattern],
        output_dir: str = "GH_WIP/learned_patterns"
    ):
        """將學習到的模式匯出為 Mermaid 圖"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for pattern in patterns:
            mermaid = self.extractor.to_mermaid(pattern)

            # 加入標註資訊
            header = [
                f"---",
                f"title: {pattern.pattern_id}",
                f"intent: {pattern.design_intent}",
                f"tags: {', '.join(pattern.semantic_tags)}",
                f"difficulty: {pattern.difficulty_level}",
                f"confidence: {pattern.confidence:.2f}",
                f"---",
                "",
            ]

            content = "\n".join(header) + mermaid

            filepath = output_path / f"{pattern.pattern_id}.mmd"
            filepath.write_text(content, encoding="utf-8")

            logger.info(f"Exported: {filepath}")

    def generate_summary_report(self, result: LearningResult) -> str:
        """生成學習報告"""
        lines = [
            "# GHX Auto-Learning Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            f"- Total files: {result.total_files}",
            f"- Successful: {result.successful}",
            f"- Failed: {result.failed}",
            f"- Patterns extracted: {result.patterns_extracted}",
            f"- New knowledge items: {result.new_knowledge}",
            "",
            "## Patterns by Intent",
        ]

        # 按意圖分組
        intent_groups: Dict[str, List[ExtractedPattern]] = {}
        for p in result.patterns:
            intent = p.design_intent or "unknown"
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(p)

        for intent, patterns in sorted(intent_groups.items()):
            lines.append(f"\n### {intent.replace('_', ' ').title()}")
            for p in patterns:
                lines.append(
                    f"- **{p.pattern_id}**: {p.component_count} components, "
                    f"{p.connection_count} connections "
                    f"(confidence: {p.confidence:.0%})"
                )

        # 錯誤列表
        if result.errors:
            lines.append("\n## Errors")
            for err in result.errors:
                lines.append(f"- `{err['file']}`: {err['error']}")

        return "\n".join(lines)


# ============================================================
# CLI 介面
# ============================================================

async def main():
    """CLI 入口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m grasshopper_mcp.ghx_auto_learner <directory> [--no-integrate]")
        print("       python -m grasshopper_mcp.ghx_auto_learner <file.ghx>")
        sys.exit(1)

    path = sys.argv[1]
    integrate = "--no-integrate" not in sys.argv

    learner = GHXAutoLearner()

    if Path(path).is_dir():
        result = await learner.learn_from_directory(path, integrate=integrate)

        # 生成報告
        report = learner.generate_summary_report(result)
        print(report)

        # 匯出 Mermaid
        if result.patterns:
            learner.export_patterns_as_mermaid(result.patterns)
    else:
        pattern = await learner.learn_from_file(path)
        if pattern:
            print(f"Pattern: {pattern.pattern_id}")
            print(f"Intent: {pattern.design_intent}")
            print(f"Tags: {pattern.semantic_tags}")
            print(f"Components: {pattern.component_count}")
            print(f"Connections: {pattern.connection_count}")
            print(f"Confidence: {pattern.confidence:.0%}")
            print()
            print("--- Mermaid ---")
            print(learner.extractor.to_mermaid(pattern))


if __name__ == "__main__":
    asyncio.run(main())
