#!/usr/bin/env python3
"""
Knowledge Bridge - 連接萃取的知識到 MCP 腳本

讓 MCP 腳本可以查詢：
- 組件的正確參數名
- 常用連接模式
- 最佳實踐建議
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ComponentInfo:
    """組件資訊"""
    name: str
    guid: str
    inputs: List[Dict[str, str]]  # [{"nickname": "G", "fullName": "Geometry"}]
    outputs: List[Dict[str, str]]
    usage_count: int
    aliases: List[str] = None  # 別名


@dataclass
class ConnectionPattern:
    """連接模式"""
    from_component: str
    from_param: str
    to_component: str
    to_param: str
    frequency: int
    description: str = ""


class KnowledgeBridge:
    """
    知識橋接器 - 讓 MCP 腳本可以查詢學習到的知識

    使用方式:
        bridge = KnowledgeBridge()
        bridge.load()

        # 查詢組件參數
        params = bridge.get_component_params("Center Box")

        # 建議連接
        suggestion = bridge.suggest_connection("Division", "Construct Point")
    """

    def __init__(self, knowledge_dir: str = None):
        if knowledge_dir is None:
            # 預設路徑
            self.knowledge_dir = Path(__file__).parent.parent / "knowledge"
        else:
            self.knowledge_dir = Path(knowledge_dir)

        self.components: Dict[str, ComponentInfo] = {}
        self.patterns: List[ConnectionPattern] = []
        self.name_aliases: Dict[str, str] = {}  # 別名 -> 標準名
        self.embeddings: Dict[str, np.ndarray] = {}  # 組件嵌入向量
        self.embedding_level: str = "NOT_LOADED"  # 學習等級

        # 手動補充的組件參數（從經驗學習）
        self._manual_params = {
            "Center Box": {
                "inputs": [
                    {"nickname": "B", "fullName": "Base"},
                    {"nickname": "X", "fullName": "X"},
                    {"nickname": "Y", "fullName": "Y"},
                    {"nickname": "Z", "fullName": "Z"},
                ],
                "outputs": [{"nickname": "Box", "fullName": "Box"}]
            },
            "XY Plane": {
                "inputs": [{"nickname": "O", "fullName": "Origin"}],
                "outputs": [{"nickname": "Pl", "fullName": "Plane"}]
            },
            "Construct Point": {
                "inputs": [
                    {"nickname": "X", "fullName": "X coordinate"},
                    {"nickname": "Y", "fullName": "Y coordinate"},
                    {"nickname": "Z", "fullName": "Z coordinate"},
                ],
                "outputs": [{"nickname": "Pt", "fullName": "Point"}]
            },
            "Division": {
                "inputs": [
                    {"nickname": "A", "fullName": "A"},
                    {"nickname": "B", "fullName": "B"},
                ],
                "outputs": [{"nickname": "R", "fullName": "Result"}]
            },
            "Average": {
                "inputs": [{"nickname": "I", "fullName": "Input"}],
                "outputs": [{"nickname": "A", "fullName": "Arithmetic mean"}]
            },
            "Orient": {
                "inputs": [
                    {"nickname": "G", "fullName": "Geometry"},
                    {"nickname": "A", "fullName": "Source"},
                    {"nickname": "B", "fullName": "Target"},
                ],
                "outputs": [{"nickname": "G", "fullName": "Geometry"}]
            },
            "Solid Union": {
                "inputs": [{"nickname": "B", "fullName": "Breps"}],
                "outputs": [{"nickname": "R", "fullName": "Result"}]
            },
            "Extrude": {
                "inputs": [
                    {"nickname": "B", "fullName": "Base"},
                    {"nickname": "D", "fullName": "Direction"},
                ],
                "outputs": [{"nickname": "E", "fullName": "Extrusion"}]
            },
            "Circle": {
                "inputs": [
                    {"nickname": "P", "fullName": "Plane"},
                    {"nickname": "R", "fullName": "Radius"},
                ],
                "outputs": [{"nickname": "C", "fullName": "Circle"}]
            },
            "Boundary Surfaces": {
                "inputs": [{"nickname": "E", "fullName": "Edges"}],
                "outputs": [{"nickname": "S", "fullName": "Surfaces"}]
            },
            "Unit Z": {
                "inputs": [{"nickname": "F", "fullName": "Factor"}],
                "outputs": [{"nickname": "V", "fullName": "Unit vector"}]
            },
            "Amplitude": {
                "inputs": [
                    {"nickname": "V", "fullName": "Vector"},
                    {"nickname": "A", "fullName": "Amplitude"},
                ],
                "outputs": [{"nickname": "V", "fullName": "Vector"}]
            },
            "Mass Addition": {
                "inputs": [{"nickname": "I", "fullName": "Input"}],
                "outputs": [
                    {"nickname": "R", "fullName": "Result"},
                    {"nickname": "P", "fullName": "Partial Results"},
                ]
            },
            "Subtraction": {
                "inputs": [
                    {"nickname": "A", "fullName": "A"},
                    {"nickname": "B", "fullName": "B"},
                ],
                "outputs": [{"nickname": "R", "fullName": "Result"}]
            },
            "Multiplication": {
                "inputs": [
                    {"nickname": "A", "fullName": "A"},
                    {"nickname": "B", "fullName": "B"},
                ],
                "outputs": [{"nickname": "R", "fullName": "Result"}]
            },
            "Addition": {
                "inputs": [
                    {"nickname": "A", "fullName": "A"},
                    {"nickname": "B", "fullName": "B"},
                ],
                "outputs": [{"nickname": "R", "fullName": "Result"}]
            },
            "Negative": {
                "inputs": [{"nickname": "x", "fullName": "Value"}],
                "outputs": [{"nickname": "y", "fullName": "Result"}]
            },
            "Rectangle": {
                "inputs": [
                    {"nickname": "P", "fullName": "Plane"},
                    {"nickname": "X", "fullName": "X Size"},
                    {"nickname": "Y", "fullName": "Y Size"},
                    {"nickname": "R", "fullName": "Radius"},
                ],
                "outputs": [
                    {"nickname": "R", "fullName": "Rectangle"},
                    {"nickname": "L", "fullName": "Length"},
                ]
            },
            "Loft": {
                "inputs": [
                    {"nickname": "C", "fullName": "Curves"},
                    {"nickname": "O", "fullName": "Options"},
                ],
                "outputs": [{"nickname": "L", "fullName": "Loft"}]
            },
        }

        # OLD 組件警告列表
        self._old_components = {
            "Move": "使用 Orient 或 Transform 替代",
            "Multiplication": "使用 Division (A / (1/B)) 替代",
            "Subtraction": "使用 Addition + Negative 替代",
            "Addition": "使用 Mass Addition 替代",
        }

    def load(self) -> bool:
        """載入知識庫"""
        # 載入萃取的組件參數
        params_file = self.knowledge_dir / "component_params_extracted.json"
        if params_file.exists():
            with open(params_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name, info in data.get("components", {}).items():
                    self.components[name] = ComponentInfo(
                        name=name,
                        guid=info.get("guid", ""),
                        inputs=info.get("inputs", []),
                        outputs=info.get("outputs", []),
                        usage_count=info.get("usage_count", 0)
                    )

        # 載入連接模式
        knowledge_file = self.knowledge_dir / "extracted_knowledge.json"
        if knowledge_file.exists():
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for pattern, count in data.get("connection_patterns", {}).items():
                    # 解析模式: "Bounds.I -> Remap Numbers.S"
                    if " -> " in pattern:
                        parts = pattern.split(" -> ")
                        if len(parts) == 2:
                            from_part = parts[0].rsplit(".", 1)
                            to_part = parts[1].rsplit(".", 1)
                            if len(from_part) == 2 and len(to_part) == 2:
                                self.patterns.append(ConnectionPattern(
                                    from_component=from_part[0],
                                    from_param=from_part[1],
                                    to_component=to_part[0],
                                    to_param=to_part[1],
                                    frequency=count
                                ))

        # 補充手動參數
        for name, params in self._manual_params.items():
            if name not in self.components:
                self.components[name] = ComponentInfo(
                    name=name,
                    guid="",
                    inputs=params.get("inputs", []),
                    outputs=params.get("outputs", []),
                    usage_count=0
                )
            else:
                # 補充空的 inputs/outputs
                if not self.components[name].inputs:
                    self.components[name].inputs = params.get("inputs", [])
                if not self.components[name].outputs:
                    self.components[name].outputs = params.get("outputs", [])

        print(f"[KnowledgeBridge] 載入 {len(self.components)} 組件, {len(self.patterns)} 連接模式")
        return True

    def get_component_params(self, name: str) -> Optional[Dict]:
        """
        查詢組件的參數資訊

        Args:
            name: 組件名稱 (如 "Center Box", "Division")

        Returns:
            {
                "name": "Center Box",
                "inputs": [{"nickname": "B", "fullName": "Base"}, ...],
                "outputs": [{"nickname": "Box", "fullName": "Box"}],
                "warning": "此組件可能有 OLD 版本" (可選)
            }
        """
        # 先檢查手動補充的
        if name in self._manual_params:
            result = {
                "name": name,
                "inputs": self._manual_params[name].get("inputs", []),
                "outputs": self._manual_params[name].get("outputs", []),
            }
            if name in self._old_components:
                result["warning"] = f"OLD 組件警告: {self._old_components[name]}"
            return result

        # 再檢查萃取的知識
        if name in self.components:
            comp = self.components[name]
            return {
                "name": comp.name,
                "inputs": comp.inputs,
                "outputs": comp.outputs,
                "guid": comp.guid,
                "usage_count": comp.usage_count,
            }

        # 模糊匹配
        for comp_name, comp in self.components.items():
            if name.lower() in comp_name.lower():
                return {
                    "name": comp.name,
                    "inputs": comp.inputs,
                    "outputs": comp.outputs,
                    "guid": comp.guid,
                    "usage_count": comp.usage_count,
                    "matched_from": name,
                }

        return None

    def get_input_param(self, component_name: str, param_hint: str = None) -> Optional[str]:
        """
        獲取組件輸入參數的正確名稱

        Args:
            component_name: 組件名稱
            param_hint: 參數提示 (如 "X", "Base", "Geometry")

        Returns:
            正確的參數名 (nickname 或 fullName)
        """
        info = self.get_component_params(component_name)
        if not info or not info.get("inputs"):
            return None

        inputs = info["inputs"]

        if param_hint:
            # 先嘗試精確匹配 nickname
            for inp in inputs:
                if inp.get("nickname", "").lower() == param_hint.lower():
                    return inp["fullName"]  # 返回 fullName 用於 MCP
            # 再嘗試精確匹配 fullName
            for inp in inputs:
                if inp.get("fullName", "").lower() == param_hint.lower():
                    return inp["fullName"]
            # 模糊匹配
            for inp in inputs:
                if param_hint.lower() in inp.get("fullName", "").lower():
                    return inp["fullName"]

        # 沒有提示，返回第一個
        if inputs:
            return inputs[0].get("fullName")

        return None

    def get_output_param(self, component_name: str, param_hint: str = None) -> Optional[str]:
        """獲取組件輸出參數的正確名稱"""
        info = self.get_component_params(component_name)
        if not info or not info.get("outputs"):
            return None

        outputs = info["outputs"]

        if param_hint:
            for out in outputs:
                if out.get("nickname", "").lower() == param_hint.lower():
                    return out["fullName"]
            for out in outputs:
                if out.get("fullName", "").lower() == param_hint.lower():
                    return out["fullName"]

        if outputs:
            return outputs[0].get("fullName")

        return None

    def suggest_connection(self, from_component: str, to_component: str) -> Optional[Dict]:
        """
        建議兩個組件之間的最佳連接方式

        Args:
            from_component: 來源組件
            to_component: 目標組件

        Returns:
            {
                "from_param": "Result",
                "to_param": "X coordinate",
                "confidence": 0.9,
                "examples": 15
            }
        """
        # 從學習到的模式中查找
        best_match = None
        best_count = 0

        for pattern in self.patterns:
            if (from_component.lower() in pattern.from_component.lower() and
                to_component.lower() in pattern.to_component.lower()):
                if pattern.frequency > best_count:
                    best_count = pattern.frequency
                    best_match = pattern

        if best_match:
            # 轉換 nickname 到 fullName
            from_full = self.get_output_param(from_component, best_match.from_param)
            to_full = self.get_input_param(to_component, best_match.to_param)

            return {
                "from_param": from_full or best_match.from_param,
                "to_param": to_full or best_match.to_param,
                "confidence": min(best_count / 10, 1.0),
                "examples": best_count,
            }

        # 沒找到學習的模式，使用預設邏輯
        from_info = self.get_component_params(from_component)
        to_info = self.get_component_params(to_component)

        if from_info and to_info:
            from_out = from_info.get("outputs", [])
            to_in = to_info.get("inputs", [])

            if from_out and to_in:
                return {
                    "from_param": from_out[0].get("fullName"),
                    "to_param": to_in[0].get("fullName"),
                    "confidence": 0.5,
                    "examples": 0,
                    "note": "基於預設邏輯，非學習結果"
                }

        return None

    def check_old_component(self, name: str) -> Optional[str]:
        """檢查是否為 OLD 組件，返回替代建議"""
        return self._old_components.get(name)

    def get_common_patterns(self, category: str = None, limit: int = 10) -> List[ConnectionPattern]:
        """獲取最常用的連接模式"""
        sorted_patterns = sorted(self.patterns, key=lambda p: p.frequency, reverse=True)

        if category:
            sorted_patterns = [p for p in sorted_patterns
                              if category.lower() in p.from_component.lower()
                              or category.lower() in p.to_component.lower()]

        return sorted_patterns[:limit]

    def load_embeddings(self) -> bool:
        """載入組件嵌入向量"""
        embeddings_file = self.knowledge_dir / "component_embeddings.json"
        if not embeddings_file.exists():
            print(f"[KnowledgeBridge] 嵌入檔案不存在: {embeddings_file}")
            return False

        try:
            with open(embeddings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            emb_data = data.get('embeddings', {})
            for name, vec in emb_data.items():
                self.embeddings[name] = np.array(vec)

            self.embedding_level = data.get('metadata', {}).get('learning_level', 'UNKNOWN')
            print(f"[KnowledgeBridge] 載入 {len(self.embeddings)} 個嵌入向量 (Level: {self.embedding_level})")
            return True

        except Exception as e:
            print(f"[KnowledgeBridge] 載入嵌入失敗: {e}")
            return False

    def find_similar_components(self, name: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        使用嵌入向量找出相似組件

        Args:
            name: 組件名稱
            top_k: 返回前 k 個

        Returns:
            [(組件名, 相似度), ...]
        """
        if not self.embeddings:
            self.load_embeddings()

        if not self.embeddings:
            return []

        # 查找目標組件
        target_name = None
        if name in self.embeddings:
            target_name = name
        else:
            # 模糊匹配
            for comp_name in self.embeddings.keys():
                if name.lower() in comp_name.lower():
                    target_name = comp_name
                    break

        if not target_name:
            return []

        target_vec = self.embeddings[target_name]
        similarities = []

        for comp, vec in self.embeddings.items():
            if comp != target_name:
                norm_t = np.linalg.norm(target_vec)
                norm_v = np.linalg.norm(vec)
                if norm_t > 0 and norm_v > 0:
                    sim = float(np.dot(target_vec, vec) / (norm_t * norm_v))
                    similarities.append((comp, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def suggest_alternative(self, name: str) -> Optional[Dict]:
        """
        建議替代組件（當找不到組件時使用嵌入找相似的）

        Args:
            name: 找不到的組件名稱

        Returns:
            {"alternatives": [...], "reason": "基於嵌入相似度"}
        """
        similar = self.find_similar_components(name, top_k=3)
        if not similar:
            return None

        return {
            "query": name,
            "alternatives": [
                {"name": comp, "similarity": f"{sim:.1%}"}
                for comp, sim in similar
            ],
            "reason": f"基於 {self.embedding_level} 嵌入相似度"
        }


# CLI 測試
if __name__ == "__main__":
    bridge = KnowledgeBridge()
    bridge.load()

    print("\n=== 測試組件參數查詢 ===")
    for name in ["Center Box", "Division", "Orient", "Custom Preview"]:
        info = bridge.get_component_params(name)
        print(f"\n{name}:")
        if info:
            print(f"  Inputs: {info.get('inputs', [])}")
            print(f"  Outputs: {info.get('outputs', [])}")
            if info.get("warning"):
                print(f"  Warning: {info['warning']}")
        else:
            print("  Not found")

    print("\n=== 測試連接建議 ===")
    tests = [
        ("Division", "Construct Point"),
        ("Bounds", "Remap Numbers"),
        ("Gradient", "Custom Preview"),
    ]
    for from_comp, to_comp in tests:
        suggestion = bridge.suggest_connection(from_comp, to_comp)
        print(f"\n{from_comp} -> {to_comp}:")
        if suggestion:
            print(f"  建議: {suggestion['from_param']} -> {suggestion['to_param']}")
            print(f"  信心度: {suggestion['confidence']:.1%} (基於 {suggestion['examples']} 個範例)")
        else:
            print("  無建議")

    print("\n=== 最常用連接模式 ===")
    for pattern in bridge.get_common_patterns(limit=5):
        print(f"  {pattern.from_component}.{pattern.from_param} -> "
              f"{pattern.to_component}.{pattern.to_param} ({pattern.frequency}次)")
