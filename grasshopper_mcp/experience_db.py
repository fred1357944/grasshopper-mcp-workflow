#!/usr/bin/env python3
"""
Experience Database - 三層知識架構
==================================

Knowledge Hierarchy:
  🏆 Golden    - 官方審核、專家驗證、核心競爭力
  🌐 Community - 社群貢獻、投票驗證、生態系統
  📝 Personal  - 個人累積、即時學習、個人化

知識流動:
  Personal → (opt-in share) → Community Pending → (verified) → Community → (curated) → Golden
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class KnowledgeSource(Enum):
    """知識來源層級"""
    GOLDEN = "golden"          # 🏆 官方審核
    COMMUNITY = "community"    # 🌐 社群驗證
    PERSONAL = "personal"      # 📝 個人經驗
    NONE = "none"              # 無匹配


class KnowledgeStatus(Enum):
    """社群知識狀態"""
    PENDING = "pending"        # 等待驗證
    VERIFIED = "verified"      # 已驗證
    DEPRECATED = "deprecated"  # 已棄用


@dataclass
class DomainKnowledge:
    """領域知識片段"""
    key: str                          # 知識鍵 (e.g., "solar_height_formula")
    value: str                        # 知識值 (e.g., "H ≤ 3.6(Sw+D)")
    source: str = "user_provided"     # 來源 (user_provided, web_search, expert)
    context: str = ""                 # 適用情境
    confidence: float = 1.0           # 信心度


@dataclass
class LearnedPattern:
    """學習到的連接模式"""
    pattern: str                      # e.g., "MeshBox.M → FaceNormals.M"
    usage_count: int = 1
    success_count: int = 1
    last_used: str = ""


@dataclass
class Experience:
    """經驗記錄"""
    id: str
    timestamp: str

    # 問題描述
    request: str                      # 原始請求
    keywords: List[str] = field(default_factory=list)
    task_type: str = ""               # wasp, structural, solar, etc.

    # 解決方案
    solution: Dict = field(default_factory=dict)  # patterns_used, components, connections

    # 領域知識 (精華)
    domain_knowledge: List[Dict] = field(default_factory=list)

    # 學習到的模式
    learned_patterns: List[str] = field(default_factory=list)

    # 統計
    usage_count: int = 1
    success_count: int = 1

    # 社群狀態 (僅 Community 層)
    status: str = "active"            # pending, verified, deprecated
    votes_up: int = 0
    votes_down: int = 0

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.usage_count, 1)


@dataclass
class KnowledgeResult:
    """知識查詢結果"""
    source: KnowledgeSource
    content: Optional[Experience] = None
    domain_knowledge: List[DomainKnowledge] = field(default_factory=list)
    reliability: str = ""
    action: str = ""  # 當 source=NONE 時的建議動作


class ExperienceDB:
    """
    三層經驗知識庫

    結構:
      config/
        golden_knowledge/
          _index.json
          building_regulations/
          wasp_patterns/
          structural_systems/
        community_knowledge/
          _index.json
          pending/
          verified/
        personal_knowledge/
          {user_id}/
            experiences.json
            domain_knowledge.json
    """

    def __init__(
        self,
        storage_dir: Union[str, Path] = "config",
        user_id: str = "default"
    ):
        self.storage_dir = Path(storage_dir)
        self.user_id = user_id

        # 三層目錄
        self.golden_dir = self.storage_dir / "golden_knowledge"
        self.community_dir = self.storage_dir / "community_knowledge"
        self.personal_dir = self.storage_dir / "personal_knowledge" / user_id

        # 確保目錄存在
        self._ensure_directories()

        # 載入索引
        self.golden_index = self._load_index(self.golden_dir)
        self.community_index = self._load_index(self.community_dir)
        self.personal_experiences = self._load_personal_experiences()
        self.personal_knowledge = self._load_personal_knowledge()

    def _ensure_directories(self):
        """確保目錄結構存在"""
        dirs = [
            self.golden_dir,
            self.golden_dir / "building_regulations",
            self.golden_dir / "wasp_patterns",
            self.golden_dir / "structural_systems",
            self.community_dir / "pending",
            self.community_dir / "verified",
            self.personal_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_index(self, base_dir: Path) -> Dict:
        """載入索引"""
        index_path = base_dir / "_index.json"
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"version": "1.0", "entries": [], "last_updated": ""}

    def _save_index(self, base_dir: Path, index: Dict):
        """儲存索引"""
        index["last_updated"] = datetime.now().isoformat()
        index_path = base_dir / "_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _load_personal_experiences(self) -> List[Experience]:
        """載入個人經驗"""
        exp_path = self.personal_dir / "experiences.json"
        if exp_path.exists():
            with open(exp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Experience(**e) for e in data.get("experiences", [])]
        return []

    def _save_personal_experiences(self):
        """儲存個人經驗"""
        exp_path = self.personal_dir / "experiences.json"
        data = {
            "version": "1.0",
            "user_id": self.user_id,
            "last_updated": datetime.now().isoformat(),
            "experiences": [asdict(e) for e in self.personal_experiences]
        }
        with open(exp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_personal_knowledge(self) -> List[DomainKnowledge]:
        """載入個人領域知識"""
        know_path = self.personal_dir / "domain_knowledge.json"
        if know_path.exists():
            with open(know_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [DomainKnowledge(**k) for k in data.get("knowledge", [])]
        return []

    def _save_personal_knowledge(self):
        """儲存個人領域知識"""
        know_path = self.personal_dir / "domain_knowledge.json"
        data = {
            "version": "1.0",
            "user_id": self.user_id,
            "last_updated": datetime.now().isoformat(),
            "knowledge": [asdict(k) for k in self.personal_knowledge]
        }
        with open(know_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # =========================================================================
    # 搜尋 API
    # =========================================================================

    def search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        task_type: Optional[str] = None
    ) -> KnowledgeResult:
        """
        三層知識搜尋（按優先順序）

        1. Golden（官方保證品質）
        2. Community Verified（群眾驗證）
        3. Personal（自己用過）
        4. None → 需要 HITL 協作
        """
        keywords = keywords or self._extract_keywords(query)

        # 1. 搜尋 Golden
        golden = self._search_golden(keywords, task_type)
        if golden and golden.success_rate >= 0.8:
            return KnowledgeResult(
                source=KnowledgeSource.GOLDEN,
                content=golden,
                reliability="verified_by_experts",
            )

        # 2. 搜尋 Community (Verified)
        community = self._search_community(keywords, task_type, verified_only=True)
        if community and community.success_rate >= 0.7:
            return KnowledgeResult(
                source=KnowledgeSource.COMMUNITY,
                content=community,
                reliability=f"used_by_{community.usage_count}_users",
            )

        # 3. 搜尋 Personal
        personal = self._search_personal(keywords, task_type)
        if personal:
            return KnowledgeResult(
                source=KnowledgeSource.PERSONAL,
                content=personal,
                reliability="your_previous_solution",
            )

        # 4. 都沒有
        return KnowledgeResult(
            source=KnowledgeSource.NONE,
            action="collaborate_with_user"
        )

    def search_knowledge(
        self,
        topic: str
    ) -> Optional[DomainKnowledge]:
        """
        搜尋領域知識片段

        用於 HITL 協作時，查找相關的已知知識
        """
        topic_lower = topic.lower()

        # 搜尋個人知識
        for k in self.personal_knowledge:
            if topic_lower in k.key.lower() or topic_lower in k.value.lower():
                return k

        # TODO: 搜尋 Golden 和 Community 的知識片段

        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵字"""
        text_lower = text.lower()

        # 領域關鍵字
        domain_keywords = {
            'wasp': ['wasp', '離散', '聚集', 'aggregation', 'part', 'module'],
            'structural': ['結構', 'karamba', 'beam', 'column', '柱', '樑'],
            'solar': ['日照', 'ladybug', 'solar', 'shadow', '陰影'],
            'form_finding': ['kangaroo', '找形', '張力', 'tensile', 'membrane'],
            'regulation': ['法規', '建蔽率', '容積率', 'coverage', 'far'],
        }

        extracted = set()
        for category, kws in domain_keywords.items():
            for kw in kws:
                if kw.lower() in text_lower:
                    extracted.add(kw.lower())
                    extracted.add(category)

        return list(extracted)

    def _search_golden(
        self,
        keywords: List[str],
        task_type: Optional[str]
    ) -> Optional[Experience]:
        """搜尋 Golden 知識庫"""
        best_match = None
        best_score = 0.0

        for entry in self.golden_index.get("entries", []):
            # 計算匹配分數
            entry_keywords = set(k.lower() for k in entry.get("keywords", []))
            query_keywords = set(k.lower() for k in keywords)

            overlap = entry_keywords & query_keywords
            if not overlap:
                continue

            score = len(overlap) / max(len(query_keywords), 1)

            # task_type 加分
            if task_type and entry.get("task_type") == task_type:
                score *= 1.2

            if score > best_score:
                best_score = score
                # 載入完整經驗
                exp_path = self.golden_dir / entry.get("path", "")
                if exp_path.exists():
                    with open(exp_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        best_match = self._dict_to_experience(data)

        return best_match

    def _dict_to_experience(self, data: Dict) -> Experience:
        """將字典轉換為 Experience，過濾額外欄位"""
        # Experience 支援的欄位
        valid_fields = {
            'id', 'timestamp', 'request', 'keywords', 'task_type',
            'solution', 'domain_knowledge', 'learned_patterns',
            'usage_count', 'success_count', 'status', 'votes_up', 'votes_down'
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return Experience(**filtered)

    def _search_community(
        self,
        keywords: List[str],
        task_type: Optional[str],
        verified_only: bool = True
    ) -> Optional[Experience]:
        """搜尋 Community 知識庫"""
        search_dir = self.community_dir / ("verified" if verified_only else "pending")

        if not search_dir.exists():
            return None

        best_match = None
        best_score = 0.0

        for exp_file in search_dir.glob("*.json"):
            try:
                with open(exp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    exp = self._dict_to_experience(data)

                # 計算匹配分數
                exp_keywords = set(k.lower() for k in exp.keywords)
                query_keywords = set(k.lower() for k in keywords)

                overlap = exp_keywords & query_keywords
                if not overlap:
                    continue

                score = len(overlap) / max(len(query_keywords), 1)
                score *= exp.success_rate  # 成功率加權

                if score > best_score:
                    best_score = score
                    best_match = exp

            except Exception:
                continue

        return best_match

    def _search_personal(
        self,
        keywords: List[str],
        task_type: Optional[str]
    ) -> Optional[Experience]:
        """搜尋個人經驗"""
        best_match = None
        best_score = 0.0

        for exp in self.personal_experiences:
            exp_keywords = set(k.lower() for k in exp.keywords)
            query_keywords = set(k.lower() for k in keywords)

            overlap = exp_keywords & query_keywords
            if not overlap:
                continue

            score = len(overlap) / max(len(query_keywords), 1)

            if score > best_score:
                best_score = score
                best_match = exp

        return best_match

    # =========================================================================
    # 學習 API
    # =========================================================================

    def learn(
        self,
        request: str,
        solution: Dict,
        domain_knowledge: Optional[List[Dict]] = None,
        patterns_used: Optional[List[str]] = None
    ) -> Experience:
        """
        從成功案例學習

        自動儲存到 Personal 層
        """
        # 生成 ID
        exp_id = self._generate_id(request)

        # 提取關鍵字
        keywords = self._extract_keywords(request)

        # 推斷任務類型
        task_type = self._infer_task_type(keywords)

        # 創建經驗
        exp = Experience(
            id=exp_id,
            timestamp=datetime.now().isoformat(),
            request=request,
            keywords=keywords,
            task_type=task_type,
            solution=solution,
            domain_knowledge=domain_knowledge or [],
            learned_patterns=patterns_used or [],
        )

        # 檢查是否已存在類似經驗
        existing = self._find_similar_experience(exp)
        if existing:
            # 更新現有經驗
            existing.usage_count += 1
            existing.success_count += 1
            # 合併知識
            self._merge_knowledge(existing, exp)
        else:
            # 新增經驗
            self.personal_experiences.append(exp)

        # 學習領域知識
        if domain_knowledge:
            for dk in domain_knowledge:
                self._learn_domain_knowledge(DomainKnowledge(**dk))

        # 儲存
        self._save_personal_experiences()
        self._save_personal_knowledge()

        return exp

    def record_failure(
        self,
        request: str,
        error: str,
        diagnostic: Optional[Dict] = None
    ):
        """記錄失敗案例"""
        # 找到相關經驗
        keywords = self._extract_keywords(request)
        exp = self._search_personal(keywords, None)

        if exp:
            exp.usage_count += 1
            # 不增加 success_count
            self._save_personal_experiences()

    def _generate_id(self, text: str) -> str:
        """生成唯一 ID"""
        hash_input = f"{text}_{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _infer_task_type(self, keywords: List[str]) -> str:
        """推斷任務類型"""
        type_keywords = {
            'wasp': ['wasp', 'aggregation', '聚集', 'part'],
            'structural': ['structural', 'karamba', '結構', 'beam'],
            'solar': ['solar', 'ladybug', '日照', 'shadow'],
            'form_finding': ['kangaroo', 'tensile', '張力', 'membrane'],
            'regulation': ['regulation', '法規', '建蔽率', '容積率'],
        }

        keywords_lower = set(k.lower() for k in keywords)

        for task_type, type_kws in type_keywords.items():
            if any(kw in keywords_lower for kw in type_kws):
                return task_type

        return "general"

    def _find_similar_experience(self, new_exp: Experience) -> Optional[Experience]:
        """找相似經驗"""
        for exp in self.personal_experiences:
            # 關鍵字重疊度
            overlap = set(exp.keywords) & set(new_exp.keywords)
            if len(overlap) >= len(new_exp.keywords) * 0.7:
                return exp
        return None

    def _merge_knowledge(self, existing: Experience, new_exp: Experience):
        """合併知識"""
        # 合併領域知識
        existing_keys = {dk.get("key") for dk in existing.domain_knowledge}
        for dk in new_exp.domain_knowledge:
            if dk.get("key") not in existing_keys:
                existing.domain_knowledge.append(dk)

        # 合併模式
        existing_patterns = set(existing.learned_patterns)
        for p in new_exp.learned_patterns:
            if p not in existing_patterns:
                existing.learned_patterns.append(p)

    def _learn_domain_knowledge(self, knowledge: DomainKnowledge):
        """學習領域知識片段"""
        # 檢查是否已存在
        for k in self.personal_knowledge:
            if k.key == knowledge.key:
                # 更新信心度
                k.confidence = min(k.confidence + 0.1, 1.0)
                return

        # 新增
        self.personal_knowledge.append(knowledge)

    # =========================================================================
    # 知識晉升 API
    # =========================================================================

    def share_to_community(self, experience_id: str) -> bool:
        """
        分享經驗到社群 (opt-in)

        Personal → Community Pending
        """
        # 找到經驗
        exp = None
        for e in self.personal_experiences:
            if e.id == experience_id:
                exp = e
                break

        if not exp:
            return False

        # 匿名化處理
        shared_exp = Experience(
            id=self._generate_id(f"community_{exp.id}"),
            timestamp=datetime.now().isoformat(),
            request=exp.request,
            keywords=exp.keywords,
            task_type=exp.task_type,
            solution=exp.solution,
            domain_knowledge=exp.domain_knowledge,
            learned_patterns=exp.learned_patterns,
            status="pending",
        )

        # 儲存到 Community Pending
        pending_path = self.community_dir / "pending" / f"{shared_exp.id}.json"
        with open(pending_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(shared_exp), f, indent=2, ensure_ascii=False)

        return True

    def verify_community_experience(
        self,
        experience_id: str,
        approved: bool = True
    ) -> bool:
        """
        驗證社群經驗（管理員功能）

        Pending → Verified / Deprecated
        """
        pending_path = self.community_dir / "pending" / f"{experience_id}.json"

        if not pending_path.exists():
            return False

        with open(pending_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if approved:
            # 移動到 verified
            data["status"] = "verified"
            verified_path = self.community_dir / "verified" / f"{experience_id}.json"
            with open(verified_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        # 刪除 pending
        pending_path.unlink()

        return True


# =============================================================================
# Golden Knowledge Builder (開發工具)
# =============================================================================

class GoldenKnowledgeBuilder:
    """
    黃金知識構建器

    用於創建官方審核的黃金法則
    """

    def __init__(self, golden_dir: Path):
        self.golden_dir = golden_dir
        self.index_path = golden_dir / "_index.json"

    def add_golden_rule(
        self,
        category: str,          # building_regulations, wasp_patterns, etc.
        name: str,
        description: str,
        keywords: List[str],
        solution: Dict,
        domain_knowledge: List[Dict],
        expert_verified: bool = True
    ) -> str:
        """新增黃金法則"""

        # 生成 ID
        rule_id = f"golden_{category}_{name}".replace(" ", "_").lower()

        # 創建經驗
        exp = Experience(
            id=rule_id,
            timestamp=datetime.now().isoformat(),
            request=description,
            keywords=keywords,
            task_type=category,
            solution=solution,
            domain_knowledge=domain_knowledge,
            usage_count=100,  # 預設高使用量
            success_count=100,
            status="golden",
        )

        # 儲存
        category_dir = self.golden_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        exp_path = category_dir / f"{name}.json"
        with open(exp_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(exp), f, indent=2, ensure_ascii=False)

        # 更新索引
        self._update_index(
            category=category,
            name=name,
            path=str(exp_path.relative_to(self.golden_dir)),
            keywords=keywords,
            task_type=category,
            expert_verified=expert_verified
        )

        return rule_id

    def _update_index(self, **entry):
        """更新索引"""
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"version": "1.0", "entries": []}

        # 檢查是否已存在
        for i, e in enumerate(index["entries"]):
            if e.get("name") == entry["name"]:
                index["entries"][i] = entry
                break
        else:
            index["entries"].append(entry)

        index["last_updated"] = datetime.now().isoformat()

        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    print("Experience Database - 三層知識架構測試")
    print("=" * 60)

    # 初始化
    db = ExperienceDB(storage_dir="config", user_id="test_user")

    # 測試學習
    print("\n1. 測試學習功能...")
    exp = db.learn(
        request="做一個 WASP 立方體聚集",
        solution={
            "patterns_used": ["wasp_cube_aggregation"],
            "components": ["Mesh Box", "WASP Part", "WASP Aggregation"],
        },
        domain_knowledge=[
            {"key": "wasp_geo_type", "value": "GEO 必須是 Mesh 不能是 Brep", "source": "user_provided"}
        ],
        patterns_used=["MeshBox.M → WASPPart.GEO", "WASPPart.PART → WASPAggregation.PART"]
    )
    print(f"  學習成功: {exp.id}")

    # 測試搜尋
    print("\n2. 測試搜尋功能...")
    result = db.search("wasp 聚集設計")
    print(f"  來源: {result.source.value}")
    print(f"  可靠度: {result.reliability}")
    if result.content:
        print(f"  匹配: {result.content.request}")

    # 測試知識搜尋
    print("\n3. 測試知識搜尋...")
    knowledge = db.search_knowledge("wasp_geo")
    if knowledge:
        print(f"  找到: {knowledge.key} = {knowledge.value}")
    else:
        print("  未找到相關知識")

    print("\n" + "=" * 60)
    print("測試完成！")
