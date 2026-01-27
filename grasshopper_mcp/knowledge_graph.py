"""
Grasshopper Knowledge Graph
基於 NetworkX 的輕量級知識圖譜

節點類型:
- ComponentType: Grasshopper 組件類型 (e.g., "Series", "Multiplication")
- Parameter: 組件參數 (e.g., "Series.S", "Multiplication.A")
- DesignIntent: 設計意圖標籤 (e.g., "螺旋", "結構分析")
- Pattern: 已知連接模式 (e.g., "WASP_Stochastic")

邊類型:
- CONNECTS_TO: 組件間連接 (帶頻率權重)
- HAS_PARAM: 組件擁有參數
- USED_FOR: 組件/模式用於某設計意圖
- PART_OF: 組件屬於某模式
"""

import networkx as nx
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGraph:
    """Grasshopper 知識圖譜"""

    graph: nx.MultiDiGraph = field(default_factory=nx.MultiDiGraph)

    # === 節點操作 ===

    def add_component_type(self, name: str, guid: str = None, category: str = None):
        """添加組件類型節點"""
        node_id = f"comp:{name}"
        self.graph.add_node(
            node_id,
            type="ComponentType",
            name=name,
            guid=guid,
            category=category
        )

    def add_design_intent(self, intent: str, keywords: List[str] = None):
        """添加設計意圖節點"""
        node_id = f"intent:{intent}"
        self.graph.add_node(
            node_id,
            type="DesignIntent",
            name=intent,
            keywords=keywords or []
        )

    def add_pattern(self, name: str, description: str = None):
        """添加模式節點"""
        node_id = f"pattern:{name}"
        self.graph.add_node(
            node_id,
            type="Pattern",
            name=name,
            description=description
        )

    # === 邊操作 ===

    def add_connection(
        self,
        from_comp: str,
        from_param: str,
        to_comp: str,
        to_param: str,
        frequency: int = 1,
        from_param_index: int = -1,
        to_param_index: int = -1,
        from_param_type: str = "unknown",
        to_param_type: str = "unknown"
    ):
        """
        添加帶完整語義的組件連接邊

        Args:
            from_comp: 來源組件名稱
            from_param: 來源參數名稱
            to_comp: 目標組件名稱
            to_param: 目標參數名稱
            frequency: 頻率（用於統計）
            from_param_index: 來源參數索引 (-1 表示未知)
            to_param_index: 目標參數索引 (-1 表示未知)
            from_param_type: 來源參數類型
            to_param_type: 目標參數類型
        """
        source_node = f"comp:{from_comp}"
        target_node = f"comp:{to_comp}"

        # 確保節點存在
        if source_node not in self.graph:
            self.add_component_type(from_comp)
        if target_node not in self.graph:
            self.add_component_type(to_comp)

        # 邊的唯一鍵：包含參數名和索引
        if from_param_index >= 0 and to_param_index >= 0:
            edge_key = f"{from_param}[{from_param_index}]->{to_param}[{to_param_index}]"
        else:
            edge_key = f"{from_param}->{to_param}"

        existing_edges = self.graph.get_edge_data(source_node, target_node)

        if existing_edges:
            for key, data in existing_edges.items():
                if (data.get("type") == "CONNECTS_TO" and
                    data.get("from_param") == from_param and
                    data.get("to_param") == to_param and
                    data.get("from_param_index", -1) == from_param_index and
                    data.get("to_param_index", -1) == to_param_index):
                    # 增加頻率
                    self.graph[source_node][target_node][key]["frequency"] += frequency
                    return

        # 新增連接（帶完整語義）
        self.graph.add_edge(
            source_node,
            target_node,
            key=edge_key,
            type="CONNECTS_TO",
            from_param=from_param,
            from_param_index=from_param_index,
            from_param_type=from_param_type,
            to_param=to_param,
            to_param_index=to_param_index,
            to_param_type=to_param_type,
            frequency=frequency
        )

    def add_intent_relation(self, component: str, intent: str):
        """標記組件用於某設計意圖"""
        comp_node = f"comp:{component}"
        intent_node = f"intent:{intent}"

        if comp_node not in self.graph:
            self.add_component_type(component)
        if intent_node not in self.graph:
            self.add_design_intent(intent)

        self.graph.add_edge(
            comp_node,
            intent_node,
            type="USED_FOR"
        )

    def add_pattern_component(self, pattern: str, component: str):
        """標記組件屬於某模式"""
        comp_node = f"comp:{component}"
        pattern_node = f"pattern:{pattern}"

        if comp_node not in self.graph:
            self.add_component_type(component)
        if pattern_node not in self.graph:
            self.add_pattern(pattern)

        self.graph.add_edge(
            comp_node,
            pattern_node,
            type="PART_OF"
        )

    # === 查詢操作 ===

    def find_next_components(self, component: str, top_k: int = 5) -> List[Tuple[str, int]]:
        """查詢某組件的下游連接（按頻率排序）"""
        node = f"comp:{component}"
        if node not in self.graph:
            return []

        connections = defaultdict(int)
        for _, target, data in self.graph.out_edges(node, data=True):
            if data.get("type") == "CONNECTS_TO":
                comp_name = target.replace("comp:", "")
                freq = data.get("frequency", 1)
                connections[comp_name] += freq

        return sorted(connections.items(), key=lambda x: -x[1])[:top_k]

    def find_previous_components(self, component: str, top_k: int = 5) -> List[Tuple[str, int]]:
        """查詢某組件的上游連接（按頻率排序）"""
        node = f"comp:{component}"
        if node not in self.graph:
            return []

        connections = defaultdict(int)
        for source, _, data in self.graph.in_edges(node, data=True):
            if data.get("type") == "CONNECTS_TO":
                comp_name = source.replace("comp:", "")
                freq = data.get("frequency", 1)
                connections[comp_name] += freq

        return sorted(connections.items(), key=lambda x: -x[1])[:top_k]

    def find_components_for_intent(self, intent: str) -> List[str]:
        """查詢某設計意圖相關的組件"""
        intent_node = f"intent:{intent}"
        if intent_node not in self.graph:
            return []

        components = []
        for source, _, data in self.graph.in_edges(intent_node, data=True):
            if data.get("type") == "USED_FOR" and source.startswith("comp:"):
                components.append(source.replace("comp:", ""))

        return components

    def find_patterns_for_intent(self, intent: str) -> List[str]:
        """查詢某設計意圖相關的模式"""
        intent_node = f"intent:{intent}"
        if intent_node not in self.graph:
            return []

        patterns = []
        for source, _, data in self.graph.in_edges(intent_node, data=True):
            if data.get("type") == "USED_FOR" and source.startswith("pattern:"):
                patterns.append(source.replace("pattern:", ""))

        return patterns

    def find_subgraph_for_intent(self, intent: str, max_depth: int = 3) -> nx.DiGraph:
        """找出某設計意圖相關的子圖"""
        components = self.find_components_for_intent(intent)
        if not components:
            return nx.DiGraph()

        # BFS 擴展子圖
        subgraph_nodes = set(f"comp:{c}" for c in components)
        frontier = list(subgraph_nodes)

        for _ in range(max_depth):
            next_frontier = []
            for node in frontier:
                for _, target, data in self.graph.out_edges(node, data=True):
                    if data.get("type") == "CONNECTS_TO" and target not in subgraph_nodes:
                        subgraph_nodes.add(target)
                        next_frontier.append(target)
            frontier = next_frontier

        return self.graph.subgraph(subgraph_nodes).copy()

    def get_connection_details(self, from_comp: str, to_comp: str) -> List[Dict]:
        """獲取兩個組件間的所有連接詳情（包含完整語義）"""
        source_node = f"comp:{from_comp}"
        target_node = f"comp:{to_comp}"

        if source_node not in self.graph or target_node not in self.graph:
            return []

        edges = self.graph.get_edge_data(source_node, target_node)
        if not edges:
            return []

        return [
            {
                "from_param": data.get("from_param"),
                "from_param_index": data.get("from_param_index", -1),
                "from_param_type": data.get("from_param_type", "unknown"),
                "to_param": data.get("to_param"),
                "to_param_index": data.get("to_param_index", -1),
                "to_param_type": data.get("to_param_type", "unknown"),
                "frequency": data.get("frequency", 1)
            }
            for data in edges.values()
            if data.get("type") == "CONNECTS_TO"
        ]

    def suggest_connection(self, from_comp: str, from_param_index: int = None) -> List[Dict]:
        """
        根據知識圖譜建議連接

        Args:
            from_comp: 來源組件名稱
            from_param_index: 可選的來源參數索引

        Returns:
            建議的連接列表，按頻率排序
        """
        source_node = f"comp:{from_comp}"
        if source_node not in self.graph:
            return []

        suggestions = []
        for _, target, data in self.graph.out_edges(source_node, data=True):
            if data.get("type") != "CONNECTS_TO":
                continue

            # 如果指定了參數索引，只返回匹配的
            if from_param_index is not None:
                if data.get("from_param_index", -1) != from_param_index:
                    continue

            suggestions.append({
                "target_component": target.replace("comp:", ""),
                "from_param": data.get("from_param"),
                "from_param_index": data.get("from_param_index", -1),
                "from_param_type": data.get("from_param_type", "unknown"),
                "to_param": data.get("to_param"),
                "to_param_index": data.get("to_param_index", -1),
                "to_param_type": data.get("to_param_type", "unknown"),
                "frequency": data.get("frequency", 1)
            })

        return sorted(suggestions, key=lambda x: -x["frequency"])

    # === 統計 ===

    def stats(self) -> Dict:
        """返回圖譜統計"""
        component_nodes = [n for n in self.graph.nodes if n.startswith("comp:")]
        intent_nodes = [n for n in self.graph.nodes if n.startswith("intent:")]
        pattern_nodes = [n for n in self.graph.nodes if n.startswith("pattern:")]

        connection_edges = sum(
            1 for _, _, d in self.graph.edges(data=True)
            if d.get("type") == "CONNECTS_TO"
        )

        return {
            "component_types": len(component_nodes),
            "design_intents": len(intent_nodes),
            "patterns": len(pattern_nodes),
            "connections": connection_edges,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

    # === 持久化 ===

    def save(self, path: Path):
        """保存為 JSON"""
        data = nx.node_link_data(self.graph)
        path = Path(path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Knowledge graph saved to {path}")

    @classmethod
    def load(cls, path: Path) -> "KnowledgeGraph":
        """從 JSON 載入"""
        path = Path(path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        kg = cls()
        kg.graph = nx.node_link_graph(data, directed=True, multigraph=True)
        logger.info(f"Knowledge graph loaded from {path}: {kg.stats()}")
        return kg

    # === 從現有數據導入 ===

    @classmethod
    def from_triplets(cls, triplets_path: Path) -> "KnowledgeGraph":
        """從 connection_triplets.json 導入"""
        kg = cls()
        triplets_path = Path(triplets_path)

        with open(triplets_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        triplets = data.get("triplets", data) if isinstance(data, dict) else data

        for triplet in triplets:
            source = triplet.get("source_component") or triplet.get("from")
            target = triplet.get("target_component") or triplet.get("to")
            source_param = triplet.get("source_param") or triplet.get("fromParam", "")
            target_param = triplet.get("target_param") or triplet.get("toParam", "")
            freq = triplet.get("frequency") or triplet.get("count", 1)

            if source and target:
                kg.add_connection(source, source_param, target, target_param, freq)

        logger.info(f"Imported from triplets: {kg.stats()}")
        return kg

    @classmethod
    def from_patterns(cls, patterns_path: Path, existing_kg: "KnowledgeGraph" = None) -> "KnowledgeGraph":
        """從 connection_patterns.json 導入，合併到現有圖譜"""
        kg = existing_kg or cls()
        patterns_path = Path(patterns_path)

        with open(patterns_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        patterns = data.get("patterns", data)

        for pattern_name, pattern_data in patterns.items():
            if pattern_name.startswith("_"):
                continue  # 跳過 _meta 等

            # 添加模式節點
            description = pattern_data.get("description", "")
            kg.add_pattern(pattern_name, description)

            # 添加設計意圖和關聯
            for keyword in pattern_data.get("keywords", []):
                kg.add_design_intent(keyword)
                kg.graph.add_edge(
                    f"pattern:{pattern_name}",
                    f"intent:{keyword}",
                    type="USED_FOR"
                )

            # 添加組件和連接
            for wiring in pattern_data.get("wiring", []):
                if len(wiring) >= 2:
                    source, target = wiring[0], wiring[1]
                    from_param = wiring[2] if len(wiring) > 2 else ""
                    to_param = wiring[3] if len(wiring) > 3 else ""

                    kg.add_component_type(source)
                    kg.add_component_type(target)

                    # 標記組件屬於模式
                    kg.add_pattern_component(pattern_name, source)
                    kg.add_pattern_component(pattern_name, target)

                    # 添加連接
                    kg.add_connection(source, from_param, target, to_param)

        logger.info(f"Imported from patterns: {kg.stats()}")
        return kg

    @classmethod
    def from_ghx_document(cls, doc, design_intent: str = None,
                         existing_kg: "KnowledgeGraph" = None) -> "KnowledgeGraph":
        """
        從 GHXParser 解析結果導入（帶完整參數語義）

        Args:
            doc: GHXParser.parse_file() 的返回結果
            design_intent: 可選的設計意圖標籤
            existing_kg: 現有圖譜（合併模式）
        """
        kg = existing_kg or cls()

        components_seen = set()

        # 處理連接
        for conn in doc.connections:
            source_comp = doc.components.get(conn.source_component_id)
            target_comp = doc.components.get(conn.target_component_id)

            if source_comp and target_comp:
                source_name = source_comp.name
                target_name = target_comp.name

                components_seen.add(source_name)
                components_seen.add(target_name)

                # 獲取參數類型
                from_type = "unknown"
                to_type = "unknown"

                if conn.source_output_index < len(source_comp.outputs):
                    from_type = source_comp.outputs[conn.source_output_index].data_type.value

                if conn.target_input_index < len(target_comp.inputs):
                    to_type = target_comp.inputs[conn.target_input_index].data_type.value

                # 帶完整語義的連接
                kg.add_connection(
                    from_comp=source_name,
                    from_param=conn.source_output_name or "",
                    to_comp=target_name,
                    to_param=conn.target_input_name or "",
                    frequency=1,
                    from_param_index=conn.source_output_index,
                    to_param_index=conn.target_input_index,
                    from_param_type=from_type,
                    to_param_type=to_type
                )

        # 如果有設計意圖，標記所有組件
        if design_intent:
            kg.add_design_intent(design_intent)
            for comp_name in components_seen:
                kg.add_intent_relation(comp_name, design_intent)

        return kg


def build_knowledge_graph(config_dir: Path = None) -> KnowledgeGraph:
    """
    從配置目錄構建完整知識圖譜

    優先順序：
    1. 載入已有的 knowledge_graph.json
    2. 從 connection_triplets.json 構建
    3. 合併 connection_patterns.json
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"
    else:
        config_dir = Path(config_dir)

    kg_path = config_dir / "knowledge_graph.json"

    # 嘗試載入現有圖譜
    if kg_path.exists():
        logger.info(f"Loading existing knowledge graph from {kg_path}")
        return KnowledgeGraph.load(kg_path)

    # 從頭構建
    kg = KnowledgeGraph()

    # 1. 導入 triplets
    triplets_path = config_dir / "connection_triplets.json"
    if triplets_path.exists():
        kg = KnowledgeGraph.from_triplets(triplets_path)

    # 2. 合併 patterns
    patterns_path = config_dir / "connection_patterns.json"
    if patterns_path.exists():
        kg = KnowledgeGraph.from_patterns(patterns_path, kg)

    # 保存構建結果
    kg.save(kg_path)

    return kg


if __name__ == "__main__":
    # 測試構建
    logging.basicConfig(level=logging.INFO)

    kg = build_knowledge_graph()
    print(f"\nKnowledge Graph Stats: {kg.stats()}")

    # 測試查詢
    print("\n=== 測試查詢 ===")

    # 下游組件
    next_comps = kg.find_next_components("Number Slider")
    print(f"Number Slider 下游: {next_comps[:5]}")

    # 上游組件
    prev_comps = kg.find_previous_components("Construct Point")
    print(f"Construct Point 上游: {prev_comps[:5]}")
