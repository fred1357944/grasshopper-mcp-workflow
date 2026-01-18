#!/usr/bin/env python3
"""
Graph Learner - 自適應圖學習模組

根據資料量自動選擇最佳學習方法：

Level 1: 統計頻率 (< 30 樣本) - 共現矩陣 + SVD
Level 2: Node2Vec (30-500 樣本) - 隨機遊走 + Word2Vec
Level 3: GraphSAGE (500-10K 樣本) - 圖神經網絡
Level 4: Transformer (> 10K 樣本) - 預留

自動切換：系統偵測資料量，自動選擇最佳方法
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import warnings

# 嘗試導入可選依賴
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    warnings.warn("networkx not installed.")

try:
    from gensim.models import Word2Vec
    HAS_GENSIM = True
except ImportError:
    HAS_GENSIM = False

# Level 3: PyTorch Geometric
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# 資料量閾值
THRESHOLD_NODE2VEC = 30
THRESHOLD_GRAPHSAGE = 500
THRESHOLD_TRANSFORMER = 10000


@dataclass
class GraphNode:
    """圖中的節點"""
    instance_id: str
    component_type: str
    nickname: str
    position: Tuple[float, float] = (0.0, 0.0)


@dataclass
class GraphEdge:
    """圖中的邊"""
    source: str
    target: str
    source_param: str
    target_param: str
    weight: float = 1.0


@dataclass
class ComponentGraph:
    """GH 文件的圖表示"""
    file_name: str
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Subgraph:
    """子圖模式"""
    name: str
    nodes: List[str]
    edges: List[Tuple[int, int]]
    frequency: int = 0
    source_files: List[str] = field(default_factory=list)


class AdaptiveLearner:
    """
    自適應圖學習器

    使用方式:
        learner = AdaptiveLearner()
        learner.load_parsed_data("knowledge/extracted_knowledge.json")
        learner.train()
        learner.save("knowledge/component_embeddings.json")
    """

    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.graphs: List[ComponentGraph] = []
        self.combined_graph = None
        self.embeddings: Dict[str, np.ndarray] = {}
        self.current_level: str = "NOT_TRAINED"
        self.component_types: Set[str] = set()
        self.connection_patterns: Dict[str, int] = defaultdict(int)
        self.subgraphs: List[Subgraph] = []
        self.walk_length = 10
        self.num_walks = 80

    def get_sample_count(self) -> int:
        return len(self.graphs)

    def get_recommended_level(self) -> str:
        """根據資料量推薦學習等級"""
        count = self.get_sample_count()

        if count >= THRESHOLD_TRANSFORMER:
            return "TRANSFORMER"
        elif count >= THRESHOLD_GRAPHSAGE:
            return "GRAPHSAGE"
        elif count >= THRESHOLD_NODE2VEC:
            return "NODE2VEC"
        else:
            return "STATISTICAL"

    def load_parsed_data(self, parsed_json_path: str) -> int:
        """載入解析後的 JSON 資料（支援多種格式）"""
        path = Path(parsed_json_path)
        if not path.exists():
            print(f"[AdaptiveLearner] 找不到: {parsed_json_path}")
            return 0

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 格式 1: 聚合知識庫 (extracted_knowledge.json)
        if isinstance(data, dict) and 'connection_patterns' in data:
            return self._load_aggregated_knowledge(data)

        # 格式 2: 文件列表
        documents = []
        if isinstance(data, list):
            documents = data
        elif isinstance(data, dict):
            if 'documents' in data:
                documents = data['documents']
            elif 'components' in data and isinstance(data['components'], list):
                documents = [data]

        for doc in documents:
            graph = self._convert_to_graph(doc)
            if graph and (graph.nodes or graph.edges):
                self.graphs.append(graph)

        recommended = self.get_recommended_level()
        print(f"[AdaptiveLearner] 載入 {len(self.graphs)} 個圖")
        print(f"[AdaptiveLearner] 推薦等級: {recommended}")
        return len(self.graphs)

    def _load_aggregated_knowledge(self, data: Dict) -> int:
        """載入聚合知識庫格式（如 extracted_knowledge.json）"""
        # 提取組件類型
        components_dict = data.get('components', {})
        for guid, info in components_dict.items():
            names = info.get('names', [])
            for name in names:
                self.component_types.add(name)

        # 提取連接模式（格式: "CompA.param -> CompB.param": count）
        patterns = data.get('connection_patterns', {})
        for pattern, count in patterns.items():
            self.connection_patterns[pattern] = count

        # 根據連接模式建構虛擬圖
        # 每個模式代表一個 "樣本"
        sample_count = len(patterns)

        # 建構組件圖（基於連接模式）
        graph = ComponentGraph(file_name="aggregated_knowledge")
        node_ids = {}

        for pattern in patterns.keys():
            if " -> " in pattern:
                parts = pattern.split(" -> ")
                if len(parts) == 2:
                    src_full = parts[0]  # "CompA.param"
                    tgt_full = parts[1]  # "CompB.param"

                    src_parts = src_full.rsplit(".", 1)
                    tgt_parts = tgt_full.rsplit(".", 1)

                    if len(src_parts) >= 1 and len(tgt_parts) >= 1:
                        src_comp = src_parts[0]
                        tgt_comp = tgt_parts[0]
                        src_param = src_parts[1] if len(src_parts) > 1 else ""
                        tgt_param = tgt_parts[1] if len(tgt_parts) > 1 else ""

                        # 添加節點
                        if src_comp not in node_ids:
                            node_ids[src_comp] = src_comp
                            graph.nodes.append(GraphNode(
                                instance_id=src_comp,
                                component_type=src_comp,
                                nickname=src_comp
                            ))

                        if tgt_comp not in node_ids:
                            node_ids[tgt_comp] = tgt_comp
                            graph.nodes.append(GraphNode(
                                instance_id=tgt_comp,
                                component_type=tgt_comp,
                                nickname=tgt_comp
                            ))

                        # 添加邊
                        graph.edges.append(GraphEdge(
                            source=src_comp,
                            target=tgt_comp,
                            source_param=src_param,
                            target_param=tgt_param,
                            weight=float(patterns[pattern])
                        ))

        if graph.nodes:
            self.graphs.append(graph)

        stats = data.get('statistics', {})
        total_files = stats.get('total_files_parsed', sample_count)

        print(f"[AdaptiveLearner] 載入聚合知識:")
        print(f"  - 組件類型: {len(self.component_types)}")
        print(f"  - 連接模式: {len(self.connection_patterns)}")
        print(f"  - 樣本數估計: {total_files}")
        print(f"[AdaptiveLearner] 推薦等級: {self.get_recommended_level()}")

        return total_files

    def _convert_to_graph(self, doc: Dict) -> Optional[ComponentGraph]:
        """將 JSON 轉換為圖結構"""
        file_name = doc.get('file_path', doc.get('file_name', 'unknown'))
        graph = ComponentGraph(file_name=file_name, metadata=doc.get('metadata', {}))
        id_to_type = {}

        components = doc.get('components', [])
        for comp in components:
            instance_id = comp.get('instance_guid', comp.get('id', ''))
            comp_type = comp.get('name', comp.get('type', 'Unknown'))
            nickname = comp.get('nickname', comp_type)

            if instance_id:
                id_to_type[instance_id] = comp_type
                self.component_types.add(comp_type)
                node = GraphNode(
                    instance_id=instance_id,
                    component_type=comp_type,
                    nickname=nickname,
                    position=(comp.get('position_x', 0), comp.get('position_y', 0))
                )
                graph.nodes.append(node)

        connections = doc.get('connections', [])
        for conn in connections:
            source_id = conn.get('from_component', conn.get('source', ''))
            target_id = conn.get('to_component', conn.get('target', ''))
            source_param = conn.get('from_param', '')
            target_param = conn.get('to_param', '')

            if source_id and target_id:
                edge = GraphEdge(
                    source=source_id, target=target_id,
                    source_param=source_param, target_param=target_param
                )
                graph.edges.append(edge)

                if source_id in id_to_type and target_id in id_to_type:
                    pattern = f"{id_to_type[source_id]}.{source_param} -> {id_to_type[target_id]}.{target_param}"
                    self.connection_patterns[pattern] += 1

        return graph

    def train(self, level: Optional[str] = None) -> bool:
        """訓練嵌入向量（自動選擇或指定等級）"""
        if level is None:
            level = self.get_recommended_level()

        self.current_level = level
        print(f"\n[AdaptiveLearner] 使用等級: {level}")
        print(f"[AdaptiveLearner] 資料量: {self.get_sample_count()} 樣本")

        if level == "STATISTICAL":
            return self._train_statistical()
        elif level == "NODE2VEC":
            return self._train_node2vec()
        elif level == "GRAPHSAGE":
            return self._train_graphsage()
        elif level == "TRANSFORMER":
            return self._train_transformer()
        else:
            return self._train_statistical()

    def _train_statistical(self) -> bool:
        """Level 1: 統計頻率學習（共現矩陣 + SVD）"""
        print("[Level 1] 統計頻率學習...")

        types = sorted(self.component_types)
        if not types:
            return False

        type_to_idx = {t: i for i, t in enumerate(types)}
        n = len(types)
        cooccurrence = np.zeros((n, n))

        for graph in self.graphs:
            id_to_type = {node.instance_id: node.component_type for node in graph.nodes}
            for edge in graph.edges:
                src_type = id_to_type.get(edge.source)
                tgt_type = id_to_type.get(edge.target)
                if src_type and tgt_type and src_type in type_to_idx and tgt_type in type_to_idx:
                    i, j = type_to_idx[src_type], type_to_idx[tgt_type]
                    cooccurrence[i, j] += 1
                    cooccurrence[j, i] += 1

        try:
            U, S, _ = np.linalg.svd(cooccurrence, full_matrices=False)
            dim = min(self.embedding_dim, n, len(S))
            embeddings_matrix = U[:, :dim] * np.sqrt(S[:dim])

            for t, idx in type_to_idx.items():
                self.embeddings[t] = embeddings_matrix[idx]

            print(f"[Level 1] 完成: {len(self.embeddings)} 嵌入 (維度: {dim})")
            return True
        except Exception as e:
            print(f"[Level 1] 失敗: {e}")
            return False

    def _train_node2vec(self) -> bool:
        """Level 2: Node2Vec（隨機遊走 + Word2Vec）"""
        print("[Level 2] Node2Vec 學習...")

        if not HAS_NETWORKX:
            print("[Level 2] NetworkX 未安裝，降級到 Level 1")
            return self._train_statistical()

        if not self._build_combined_graph():
            return self._train_statistical()

        walks = self._generate_walks()
        if not walks:
            return self._train_statistical()

        print(f"[Level 2] 生成 {len(walks)} 條遊走序列")

        if HAS_GENSIM:
            model = Word2Vec(
                sentences=walks,
                vector_size=self.embedding_dim,
                window=5,
                min_count=1,
                sg=1,
                workers=4,
                epochs=10
            )
            for node in self.combined_graph.nodes():
                if node in model.wv:
                    self.embeddings[node] = np.array(model.wv[node])
            print(f"[Level 2] 完成: {len(self.embeddings)} 嵌入")
            return True
        else:
            print("[Level 2] Gensim 未安裝，降級到 Level 1")
            return self._train_statistical()

    def _build_combined_graph(self) -> bool:
        """建構合併圖"""
        if not HAS_NETWORKX:
            return False

        self.combined_graph = nx.DiGraph()

        for graph in self.graphs:
            id_to_type = {node.instance_id: node.component_type for node in graph.nodes}

            for node in graph.nodes:
                if not self.combined_graph.has_node(node.component_type):
                    self.combined_graph.add_node(node.component_type, count=1)
                else:
                    self.combined_graph.nodes[node.component_type]['count'] += 1

            for edge in graph.edges:
                src = id_to_type.get(edge.source)
                tgt = id_to_type.get(edge.target)
                if src and tgt:
                    if self.combined_graph.has_edge(src, tgt):
                        self.combined_graph.edges[src, tgt]['weight'] += 1
                    else:
                        self.combined_graph.add_edge(src, tgt, weight=1)

        print(f"[Level 2] 圖: {self.combined_graph.number_of_nodes()} 節點, "
              f"{self.combined_graph.number_of_edges()} 邊")
        return True

    def _generate_walks(self) -> List[List[str]]:
        """生成隨機遊走"""
        if not self.combined_graph:
            return []

        walks = []
        nodes = list(self.combined_graph.nodes())

        for _ in range(self.num_walks):
            for start in nodes:
                walk = [start]
                current = start
                for _ in range(self.walk_length - 1):
                    neighbors = list(self.combined_graph.successors(current))
                    if not neighbors:
                        neighbors = list(self.combined_graph.predecessors(current))
                    if not neighbors:
                        break

                    weights = []
                    for n in neighbors:
                        w = 1
                        if self.combined_graph.has_edge(current, n):
                            w = self.combined_graph.edges[current, n].get('weight', 1)
                        elif self.combined_graph.has_edge(n, current):
                            w = self.combined_graph.edges[n, current].get('weight', 1)
                        weights.append(w)

                    total = sum(weights)
                    if total > 0:
                        probs = [w / total for w in weights]
                        current = np.random.choice(neighbors, p=probs)
                    else:
                        current = np.random.choice(neighbors)
                    walk.append(current)
                walks.append(walk)
        return walks

    def _train_graphsage(self) -> bool:
        """Level 3: GraphSAGE（預留，目前降級）"""
        print("[Level 3] GraphSAGE（降級到 Level 2）")
        return self._train_node2vec()

    def _train_transformer(self) -> bool:
        """Level 4: Transformer（預留，目前降級）"""
        print("[Level 4] Transformer（降級到 Level 3）")
        return self._train_graphsage()

    def find_similar(self, component_type: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """找出最相似的組件"""
        if component_type not in self.embeddings:
            return []

        target = self.embeddings[component_type]
        results = []

        for comp, vec in self.embeddings.items():
            if comp != component_type:
                norm_t = np.linalg.norm(target)
                norm_v = np.linalg.norm(vec)
                if norm_t > 0 and norm_v > 0:
                    sim = float(np.dot(target, vec) / (norm_t * norm_v))
                    results.append((comp, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def extract_subgraphs(self, min_size: int = 3, max_size: int = 8) -> List[Subgraph]:
        """提取常見子圖"""
        if not HAS_NETWORKX:
            return []

        pattern_counts = defaultdict(list)

        for graph in self.graphs:
            G = nx.DiGraph()
            id_to_type = {}

            for node in graph.nodes:
                G.add_node(node.instance_id, comp_type=node.component_type)
                id_to_type[node.instance_id] = node.component_type

            for edge in graph.edges:
                G.add_edge(edge.source, edge.target)

            for component in nx.weakly_connected_components(G):
                if min_size <= len(component) <= max_size:
                    subG = G.subgraph(component)
                    pattern = self._hash_subgraph(subG, id_to_type)
                    pattern_counts[pattern].append(graph.file_name)

        self.subgraphs = []
        for pattern, files in pattern_counts.items():
            if len(files) >= 2:
                nodes, edges = self._decode_pattern(pattern)
                self.subgraphs.append(Subgraph(
                    name=f"Pattern_{len(self.subgraphs) + 1}",
                    nodes=nodes, edges=edges,
                    frequency=len(files), source_files=files
                ))

        self.subgraphs.sort(key=lambda x: x.frequency, reverse=True)
        return self.subgraphs

    def _hash_subgraph(self, G, id_to_type: Dict) -> str:
        types = sorted([id_to_type.get(n, 'Unknown') for n in G.nodes()])
        edges = []
        node_list = list(G.nodes())
        for u, v in G.edges():
            edges.append(f"{node_list.index(u)}-{node_list.index(v)}")
        edges.sort()
        return f"{','.join(types)}|{','.join(edges)}"

    def _decode_pattern(self, pattern: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        parts = pattern.split('|')
        nodes = parts[0].split(',') if parts[0] else []
        edges = []
        if len(parts) > 1 and parts[1]:
            for e in parts[1].split(','):
                pair = e.split('-')
                edges.append((int(pair[0]), int(pair[1])))
        return nodes, edges

    def save(self, output_path: str):
        """保存嵌入（JSON 格式）"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'metadata': {
                'learning_level': self.current_level,
                'sample_count': self.get_sample_count(),
                'embedding_dim': self.embedding_dim,
                'thresholds': {
                    'NODE2VEC': THRESHOLD_NODE2VEC,
                    'GRAPHSAGE': THRESHOLD_GRAPHSAGE,
                    'TRANSFORMER': THRESHOLD_TRANSFORMER,
                }
            },
            'embeddings': {k: v.tolist() for k, v in self.embeddings.items()},
            'component_types': sorted(list(self.component_types)),
            'top_patterns': dict(sorted(
                self.connection_patterns.items(),
                key=lambda x: x[1], reverse=True
            )[:100]),
            'subgraphs': [
                {'name': s.name, 'nodes': s.nodes, 'edges': s.edges,
                 'frequency': s.frequency, 'files': s.source_files[:5]}
                for s in self.subgraphs[:50]
            ]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[AdaptiveLearner] 已保存: {output_path}")

    def load(self, input_path: str) -> bool:
        """載入嵌入（JSON 格式）"""
        path = Path(input_path)
        if not path.exists():
            return False

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.embeddings = {k: np.array(v) for k, v in data.get('embeddings', {}).items()}
        meta = data.get('metadata', {})
        self.embedding_dim = meta.get('embedding_dim', 64)
        self.current_level = meta.get('learning_level', 'UNKNOWN')
        self.component_types = set(data.get('component_types', []))
        self.connection_patterns = defaultdict(int, data.get('top_patterns', {}))

        print(f"[AdaptiveLearner] 載入 {len(self.embeddings)} 嵌入 (Level: {self.current_level})")
        return True

    def get_statistics(self) -> Dict:
        """獲取統計資訊"""
        return {
            'sample_count': self.get_sample_count(),
            'recommended_level': self.get_recommended_level(),
            'current_level': self.current_level,
            'component_types': len(self.component_types),
            'embeddings': len(self.embeddings),
            'subgraphs': len(self.subgraphs),
            'dependencies': {
                'networkx': HAS_NETWORKX,
                'gensim': HAS_GENSIM,
                'torch': HAS_TORCH,
            }
        }


# 向後相容
GraphLearner = AdaptiveLearner


if __name__ == "__main__":
    print("=" * 60)
    print("Adaptive Graph Learner Test")
    print("=" * 60)

    learner = AdaptiveLearner(embedding_dim=32)

    print("\nDependencies:")
    print(f"  NetworkX: {HAS_NETWORKX}")
    print(f"  Gensim: {HAS_GENSIM}")
    print(f"  PyTorch: {HAS_TORCH}")

    knowledge_dir = Path(__file__).parent.parent / "knowledge"
    extracted_file = knowledge_dir / "extracted_knowledge.json"

    if extracted_file.exists():
        learner.load_parsed_data(str(extracted_file))
        learner.train()
        learner.extract_subgraphs()
        learner.save(str(knowledge_dir / "component_embeddings.json"))

        stats = learner.get_statistics()
        print("\nStatistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

        if learner.embeddings:
            test_comp = list(learner.embeddings.keys())[0]
            print(f"\nSimilar to '{test_comp}':")
            for comp, sim in learner.find_similar(test_comp, 5):
                print(f"  {comp}: {sim:.3f}")
    else:
        print(f"\nFile not found: {extracted_file}")
