"""
Pattern Extractor - 模式提取器
==============================
從 GHX 文件中提取設計模式，建立模式庫
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
import hashlib

from .models import (
    GHDocument, GHComponent, GHConnection,
    ComponentVocabulary, ConnectionPattern, IntentPattern,
    ComponentCategory
)
from .ghx_parser import parse_ghx


@dataclass
class SubGraph:
    """子圖結構 - 用於模式識別"""
    components: List[str]  # component instance guids
    connections: List[Tuple[str, str]]  # (source_guid, target_guid)
    entry_points: List[str]  # 入口元件
    exit_points: List[str]   # 出口元件
    
    def signature(self) -> str:
        """產生子圖的簽名（用於比較）"""
        # 使用元件類型和連接結構產生唯一簽名
        sorted_conns = sorted(self.connections)
        return hashlib.md5(str(sorted_conns).encode()).hexdigest()[:8]


class PatternExtractor:
    """
    模式提取器
    
    從 GHX 文件中識別和提取常見的設計模式
    """
    
    def __init__(self):
        self.vocabulary: Dict[str, ComponentVocabulary] = {}
        self.connection_patterns: Dict[str, ConnectionPattern] = {}
        self.intent_patterns: Dict[str, IntentPattern] = {}
        
        # 統計資訊
        self.component_cooccurrence: Dict[Tuple[str, str], int] = {}
        self.analyzed_documents: int = 0
    
    def analyze_document(self, doc: GHDocument) -> Dict:
        """
        分析單個 GHX 文件，提取模式資訊
        
        Returns:
            分析結果字典
        """
        self.analyzed_documents += 1
        
        result = {
            "document": doc.filepath,
            "components_found": [],
            "patterns_found": [],
            "new_vocabulary": [],
            "statistics": {}
        }
        
        # 1. 更新元件詞彙表
        for comp in doc.components.values():
            vocab_entry = self._extract_vocabulary(comp)
            if vocab_entry:
                if vocab_entry.component_guid not in self.vocabulary:
                    self.vocabulary[vocab_entry.component_guid] = vocab_entry
                    result["new_vocabulary"].append(vocab_entry.name)
                result["components_found"].append(comp.name)
        
        # 2. 更新元件共現統計
        self._update_cooccurrence(doc)
        
        # 3. 識別連接模式
        patterns = self._identify_patterns(doc)
        result["patterns_found"] = [p.pattern_id for p in patterns]
        
        # 4. 統計資訊
        result["statistics"] = {
            "component_count": doc.component_count,
            "connection_count": doc.connection_count,
            "slider_count": sum(1 for c in doc.components.values() 
                              if "slider" in c.name.lower()),
            "unique_component_types": len(set(c.name for c in doc.components.values()))
        }
        
        return result
    
    def analyze_directory(self, directory: str) -> List[Dict]:
        """
        分析目錄下所有 GHX 文件
        
        Args:
            directory: 目錄路徑
            
        Returns:
            所有文件的分析結果列表
        """
        results = []
        path = Path(directory)
        
        for ghx_file in path.glob("**/*.ghx"):
            try:
                doc = parse_ghx(str(ghx_file))
                result = self.analyze_document(doc)
                results.append(result)
            except Exception as e:
                results.append({
                    "document": str(ghx_file),
                    "error": str(e)
                })
        
        return results
    
    def _extract_vocabulary(self, comp: GHComponent) -> Optional[ComponentVocabulary]:
        """從元件提取詞彙表條目"""
        if not comp.component_guid:
            return None
        
        return ComponentVocabulary(
            component_guid=comp.component_guid,
            name=comp.name,
            nickname=comp.nickname,
            category=comp.category,
            subcategory=comp.subcategory,
            input_specs=[
                {"name": inp.name, "type": inp.data_type.value}
                for inp in comp.inputs
            ],
            output_specs=[
                {"name": out.name, "type": out.data_type.value}
                for out in comp.outputs
            ],
            pattern_tags=self._infer_pattern_tags(comp),
            elegance_score=self._estimate_elegance_score(comp)
        )
    
    def _infer_pattern_tags(self, comp: GHComponent) -> List[str]:
        """推斷元件的模式標籤"""
        tags = []
        name_lower = comp.name.lower()
        
        # 基於元件名稱推斷標籤
        tag_rules = {
            "transformation": ["move", "rotate", "scale", "mirror", "orient"],
            "generation": ["construct", "create", "line", "circle", "point"],
            "distribution": ["divide", "series", "range", "remap", "graph"],
            "analysis": ["evaluate", "length", "area", "closest"],
            "topology": ["join", "split", "trim", "offset"],
            "data_manipulation": ["list", "tree", "flatten", "graft", "partition"],
            "trigonometry": ["sin", "cos", "tan"],
            "visualization": ["preview", "color", "display"],
        }
        
        for tag, keywords in tag_rules.items():
            if any(kw in name_lower for kw in keywords):
                tags.append(tag)
        
        # 基於分類添加標籤
        if comp.category != ComponentCategory.UNKNOWN:
            tags.append(comp.category.value.lower())
        
        return tags
    
    def _estimate_elegance_score(self, comp: GHComponent) -> float:
        """估計元件的優雅度分數"""
        name_lower = comp.name.lower()
        
        # 優雅元件得分較高
        elegant_keywords = ["graph mapper", "remap", "evaluate", "expression"]
        if any(kw in name_lower for kw in elegant_keywords):
            return 5.0
        
        # 基礎元件得分中等
        basic_keywords = ["slider", "panel", "number"]
        if any(kw in name_lower for kw in basic_keywords):
            return 2.0
        
        # 其他元件默認分數
        return 3.0
    
    def _update_cooccurrence(self, doc: GHDocument):
        """更新元件共現統計"""
        component_names = [c.name for c in doc.components.values()]
        
        # 計算所有配對的共現次數
        for i, name1 in enumerate(component_names):
            for name2 in component_names[i+1:]:
                pair = tuple(sorted([name1, name2]))
                self.component_cooccurrence[pair] = \
                    self.component_cooccurrence.get(pair, 0) + 1
    
    def _identify_patterns(self, doc: GHDocument) -> List[ConnectionPattern]:
        """識別文件中的連接模式"""
        patterns = []
        
        # 識別已知模式
        known_patterns = [
            self._detect_parametric_curve_pattern(doc),
            self._detect_array_pattern(doc),
            self._detect_gradient_distribution_pattern(doc),
            self._detect_trigonometric_spiral_pattern(doc),
        ]
        
        for pattern in known_patterns:
            if pattern:
                patterns.append(pattern)
        
        return patterns
    
    def _detect_parametric_curve_pattern(self, doc: GHDocument) -> Optional[ConnectionPattern]:
        """檢測參數化曲線生成模式"""
        # 模式: Series/Range -> 數學運算 -> Construct Point -> Interpolate
        
        has_series = any("series" in c.name.lower() or "range" in c.name.lower() 
                        for c in doc.components.values())
        has_point_construct = any("construct point" in c.name.lower() or "pt" in c.nickname.lower()
                                 for c in doc.components.values())
        has_interpolate = any("interpolate" in c.name.lower() 
                             for c in doc.components.values())
        
        if has_series and has_point_construct and has_interpolate:
            return ConnectionPattern(
                pattern_id="parametric_curve_generation",
                description="參數化曲線生成：使用序列產生參數，建構點後插值成曲線",
                elegance_level=4,
                component_sequence=["Series/Range", "Math Operations", "Construct Point", "Interpolate"],
                keywords=["parametric", "curve", "generation", "interpolate"]
            )
        
        return None
    
    def _detect_array_pattern(self, doc: GHDocument) -> Optional[ConnectionPattern]:
        """檢測陣列模式"""
        has_array = any("array" in c.name.lower() for c in doc.components.values())
        has_geometry = any(c.category in [ComponentCategory.CURVE, ComponentCategory.SURFACE]
                          for c in doc.components.values())
        
        if has_array and has_geometry:
            return ConnectionPattern(
                pattern_id="geometric_array",
                description="幾何陣列：複製幾何物件",
                elegance_level=3,
                component_sequence=["Geometry", "Array"],
                keywords=["array", "copy", "repeat"]
            )
        
        return None
    
    def _detect_gradient_distribution_pattern(self, doc: GHDocument) -> Optional[ConnectionPattern]:
        """檢測漸變分布模式"""
        has_divide = any("divide" in c.name.lower() for c in doc.components.values())
        has_remap = any("remap" in c.name.lower() or "graph" in c.name.lower()
                       for c in doc.components.values())
        
        if has_divide and has_remap:
            return ConnectionPattern(
                pattern_id="gradient_distribution",
                description="沿曲線漸變分布：分割曲線並重映射參數",
                elegance_level=5,
                component_sequence=["Curve", "Divide", "Remap/Graph Mapper", "Transform"],
                keywords=["gradient", "distribution", "remap", "along curve"],
                optimization_tips=["使用 Graph Mapper 可以實現非線性漸變"]
            )
        
        return None
    
    def _detect_trigonometric_spiral_pattern(self, doc: GHDocument) -> Optional[ConnectionPattern]:
        """檢測三角函數螺旋模式"""
        has_sin = any("sin" in c.name.lower() for c in doc.components.values())
        has_cos = any("cos" in c.name.lower() for c in doc.components.values())
        has_series = any("series" in c.name.lower() for c in doc.components.values())
        
        if has_sin and has_cos and has_series:
            return ConnectionPattern(
                pattern_id="trigonometric_spiral",
                description="三角函數螺旋：使用 Sin/Cos 生成螺旋或圓形運動",
                elegance_level=4,
                component_sequence=["Series", "Sin", "Cos", "Construct Point"],
                keywords=["spiral", "helix", "circular", "trigonometric"],
                alternatives=[
                    ConnectionPattern(
                        pattern_id="helix_component",
                        description="使用內建 Helix 元件",
                        elegance_level=5,
                        component_sequence=["Helix"],
                        keywords=["helix", "spiral"],
                        optimization_tips=["更簡潔，但參數化程度較低"]
                    )
                ]
            )
        
        return None
    
    def get_common_successors(self, component_name: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        取得某元件最常見的後續元件
        
        Args:
            component_name: 元件名稱
            top_n: 返回前 N 個
            
        Returns:
            [(元件名稱, 共現次數), ...]
        """
        successors = []
        
        for (c1, c2), count in self.component_cooccurrence.items():
            if c1 == component_name:
                successors.append((c2, count))
            elif c2 == component_name:
                successors.append((c1, count))
        
        return sorted(successors, key=lambda x: -x[1])[:top_n]
    
    def export_vocabulary(self, filepath: str):
        """匯出元件詞彙表為 JSON"""
        data = {
            name: {
                "component_guid": v.component_guid,
                "name": v.name,
                "nickname": v.nickname,
                "category": v.category.value,
                "input_specs": v.input_specs,
                "output_specs": v.output_specs,
                "pattern_tags": v.pattern_tags,
                "elegance_score": v.elegance_score,
                "common_predecessors": v.common_predecessors,
                "common_successors": v.common_successors,
            }
            for name, v in self.vocabulary.items()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_patterns(self, filepath: str):
        """匯出連接模式為 JSON"""
        data = {
            pid: {
                "pattern_id": p.pattern_id,
                "description": p.description,
                "elegance_level": p.elegance_level,
                "component_sequence": p.component_sequence,
                "keywords": p.keywords,
                "optimization_tips": p.optimization_tips,
            }
            for pid, p in self.connection_patterns.items()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def summary(self) -> str:
        """產生分析摘要"""
        lines = [
            "=== Pattern Extractor Summary ===",
            f"Analyzed documents: {self.analyzed_documents}",
            f"Vocabulary entries: {len(self.vocabulary)}",
            f"Connection patterns: {len(self.connection_patterns)}",
            f"Intent patterns: {len(self.intent_patterns)}",
            "",
            "--- Top Component Co-occurrences ---"
        ]
        
        # 顯示最常見的元件配對
        top_pairs = sorted(
            self.component_cooccurrence.items(),
            key=lambda x: -x[1]
        )[:10]
        
        for (c1, c2), count in top_pairs:
            lines.append(f"  {c1} + {c2}: {count}")
        
        return "\n".join(lines)


# ============================================================
# 便利函數
# ============================================================

def extract_patterns_from_file(filepath: str) -> Dict:
    """從單個文件提取模式"""
    extractor = PatternExtractor()
    doc = parse_ghx(filepath)
    return extractor.analyze_document(doc)


def extract_patterns_from_directory(directory: str) -> PatternExtractor:
    """從目錄提取模式並返回提取器實例"""
    extractor = PatternExtractor()
    extractor.analyze_directory(directory)
    return extractor


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pattern_extractor.py <file.ghx|directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    
    if path.is_file():
        result = extract_patterns_from_file(str(path))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif path.is_dir():
        extractor = extract_patterns_from_directory(str(path))
        print(extractor.summary())
    else:
        print(f"Path not found: {path}")
        sys.exit(1)
