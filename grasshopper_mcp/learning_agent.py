#!/usr/bin/env python3
"""
Learning Agent - 自動學習代理
==============================

從成功的 Grasshopper 執行中學習：
1. 提取連接三元組
2. 更新知識庫頻率
3. 自動保存學習結果

使用方式：
```python
from grasshopper_mcp.learning_agent import LearningAgent
from grasshopper_mcp.knowledge_base import ConnectionKnowledgeBase

kb = ConnectionKnowledgeBase(storage_dir=Path("config"))
agent = LearningAgent(kb, auto_save=True)

# 執行成功後調用
agent.learn_from_execution(workflow_json, {"status": "success"})
```
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
from .knowledge_base import ConnectionKnowledgeBase


class LearningAgent:
    """
    Agent responsible for learning from successful Grasshopper executions.
    Extracts connection patterns and updates the Knowledge Base.
    """

    def __init__(
        self,
        knowledge_base: ConnectionKnowledgeBase,
        storage_dir: Optional[Path] = None,
        auto_save: bool = True
    ):
        self.kb = knowledge_base
        self.storage_dir = storage_dir or Path("config")
        self.auto_save = auto_save
        self.learning_log: List[Dict] = []

    def learn_from_execution(
        self,
        workflow_json: Dict[str, Any],
        execution_report: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a successful execution report to learn patterns.

        Args:
            workflow_json: The workflow configuration that was executed.
            execution_report: The report returned by the GH/WASP execution.
            context: Optional context string (e.g., "WASP cube aggregation").

        Returns:
            Learning result summary.
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "skipped",
            "learned_count": 0,
            "new_patterns": [],
            "reinforced_patterns": []
        }

        # 1. Verify Success
        status = execution_report.get("status", "")
        if status not in ("success", "completed", True):
            # Also check for error count
            errors = execution_report.get("errors", [])
            if errors:
                result["status"] = "skipped_with_errors"
                return result

        print("🧠 Learning Agent: analyzing successful workflow...")

        # 2. Extract Connections
        connections = workflow_json.get("connections", [])
        components = workflow_json.get("components", [])

        if not connections:
            result["status"] = "no_connections"
            return result

        # Build ID lookup map
        comp_lookup = {c.get("id", c.get("nickname", "")): c for c in components}

        learned_count = 0
        new_patterns = []
        reinforced_patterns = []

        for conn in connections:
            source_id = conn.get("from") or conn.get("source", {}).get("id")
            target_id = conn.get("to") or conn.get("target", {}).get("id")

            # Handle different JSON formats
            source_port = conn.get("fromParam") or conn.get("source", {}).get("port", "")
            target_port = conn.get("toParam") or conn.get("target", {}).get("port", "")

            if not (source_id and target_id):
                continue

            source_comp = comp_lookup.get(source_id)
            target_comp = comp_lookup.get(target_id)

            if not source_comp or not target_comp:
                continue

            source_type = source_comp.get("type", "Unknown")
            target_type = target_comp.get("type", "Unknown")

            # Skip unknown types
            if source_type == "Unknown" or target_type == "Unknown":
                continue

            # Check if this is a new pattern
            key = f"{source_type}.{source_port}->{target_type}.{target_port}"
            was_new = key not in self.kb.connection_triplets or self.kb.connection_triplets.get(key, 0) == 0

            # 3. Update Knowledge Base
            self.kb.record_connection(source_type, source_port, target_type, target_port)
            learned_count += 1

            if was_new:
                new_patterns.append(key)
            else:
                reinforced_patterns.append(key)

        # 4. Auto-save if enabled
        if self.auto_save and learned_count > 0:
            self._save_triplets()

        # 5. Log learning event
        result.update({
            "status": "success",
            "learned_count": learned_count,
            "new_patterns": new_patterns,
            "reinforced_patterns": reinforced_patterns[:10],  # Limit for readability
            "context": context
        })
        self.learning_log.append(result)

        # Print summary
        print(f"✅ Learned {learned_count} patterns ({len(new_patterns)} new, {len(reinforced_patterns)} reinforced)")
        if new_patterns:
            print(f"   New: {new_patterns[:3]}{'...' if len(new_patterns) > 3 else ''}")

        return result

    def _save_triplets(self):
        """Save connection triplets to JSON file."""
        output_path = self.storage_dir / "connection_triplets.json"

        # Convert to structured format
        triplets_list = []
        for key, freq in sorted(self.kb.connection_triplets.items(), key=lambda x: x[1], reverse=True):
            # Parse key: "Source.Port->Target.Port"
            if "->" in key:
                source_part, target_part = key.split("->")
                if "." in source_part and "." in target_part:
                    src_comp, src_port = source_part.rsplit(".", 1)
                    tgt_comp, tgt_port = target_part.rsplit(".", 1)
                    triplets_list.append({
                        "source_component": src_comp,
                        "source_param": src_port,
                        "target_component": tgt_comp,
                        "target_param": tgt_port,
                        "frequency": freq
                    })

        data = {
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "total_triplets": len(triplets_list)
            },
            "triplets": triplets_list
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def learn_from_ghx(self, ghx_path: str) -> Dict[str, Any]:
        """
        Learn patterns from an existing GHX file.

        Args:
            ghx_path: Path to .ghx file.

        Returns:
            Learning result summary.
        """
        try:
            from gh_learning.src.ghx_parser import GHXParser
        except ImportError:
            return {"status": "error", "message": "ghx_parser not available"}

        parser = GHXParser()
        doc = parser.parse_ghx(ghx_path)

        if not doc:
            return {"status": "error", "message": f"Failed to parse {ghx_path}"}

        # Convert to workflow_json format
        guid_to_comp = {c.instance_guid: {"id": c.instance_guid, "type": c.name} for c in doc.components}

        workflow_json = {
            "components": list(guid_to_comp.values()),
            "connections": [
                {
                    "from": c.from_component,
                    "fromParam": c.from_param,
                    "to": c.to_component,
                    "toParam": c.to_param
                }
                for c in doc.connections
            ]
        }

        return self.learn_from_execution(
            workflow_json,
            {"status": "success"},
            context=f"GHX: {Path(ghx_path).name}"
        )

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learning events."""
        total_learned = sum(log.get("learned_count", 0) for log in self.learning_log)
        total_new = sum(len(log.get("new_patterns", [])) for log in self.learning_log)

        return {
            "total_events": len(self.learning_log),
            "total_patterns_learned": total_learned,
            "total_new_patterns": total_new,
            "kb_triplet_count": len(self.kb.connection_triplets)
        }

    # =========================================================================
    # 簡化學習 API (Phase 4 優化)
    # =========================================================================

    def learn_from_success(
        self,
        user_input: str,
        execution_result: Dict[str, Any],
        save_to_experience: bool = True
    ) -> Dict[str, Any]:
        """
        簡化學習 - 不用 Claude 總結

        流程:
        1. 直接記錄連接模式 (使用 learn_from_execution)
        2. 規則提取關鍵字
        3. 模板化儲存經驗

        Args:
            user_input: 用戶原始請求
            execution_result: 執行結果 (包含 placement_info)
            save_to_experience: 是否儲存到 Experience DB

        Returns:
            學習結果摘要
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "learned_count": 0,
            "keywords_extracted": [],
            "experience_saved": False
        }

        # 1. 從執行結果學習連接模式
        placement_info = execution_result.get("placement_info", {})
        if placement_info:
            learn_result = self.learn_from_execution(
                workflow_json=placement_info,
                execution_report={"status": "success"},
                context=f"learn_from_success: {user_input[:50]}"
            )
            result["learned_count"] = learn_result.get("learned_count", 0)
            result["new_patterns"] = learn_result.get("new_patterns", [])

        # 2. 規則提取關鍵字
        keywords = self._extract_keywords_rule_based(user_input)
        result["keywords_extracted"] = keywords

        # 3. 模板化儲存經驗 (可選)
        if save_to_experience and placement_info:
            experience_record = self._create_experience_record(
                user_input=user_input,
                placement_info=placement_info,
                keywords=keywords,
                execution_result=execution_result
            )
            result["experience_record"] = experience_record
            result["experience_saved"] = True

        return result

    def _extract_keywords_rule_based(self, text: str) -> List[str]:
        """
        規則提取關鍵字 (不用 Claude)

        基於預定義的領域關鍵字進行匹配
        """
        # 領域關鍵字映射
        domain_keywords = {
            # WASP
            'wasp': ['wasp', '聚集', '離散', 'aggregation', 'module', '模組', 'part', '連接器'],
            'cube': ['立方體', 'cube', 'box', '方塊'],
            'lshape': ['L形', 'lshape', 'l-shape', 'l shape'],

            # Karamba
            'karamba': ['karamba', '結構', 'structural', 'beam', 'shell', '樑', '殼'],
            'analysis': ['分析', 'analysis', 'analyze', 'fea'],

            # Kangaroo
            'kangaroo': ['kangaroo', '找形', '物理', 'form finding', 'physics', '張力', 'tensile'],
            'membrane': ['膜', 'membrane', 'fabric', 'tent', '帳篷'],

            # Ladybug
            'ladybug': ['ladybug', '日照', 'solar', 'radiation', '遮陽', 'shadow'],
            'honeybee': ['honeybee', '能源', 'energy', '建築能耗'],

            # Geometry
            'mesh': ['mesh', '網格', 'grid', '分割'],
            'surface': ['surface', '曲面', 'nurbs'],
            'curve': ['curve', '曲線', 'line', '線'],
            'point': ['point', '點', 'pts'],

            # Actions
            'create': ['做', '建立', '創建', 'create', 'make', 'generate'],
            'connect': ['連接', '連結', 'connect', 'link', 'wire'],
            'transform': ['移動', '旋轉', '縮放', 'move', 'rotate', 'scale', 'transform'],
        }

        text_lower = text.lower()
        extracted = set()

        for category, keywords in domain_keywords.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    extracted.add(category)
                    # 也加入匹配的原始關鍵字
                    extracted.add(kw.lower())
                    break  # 每個類別只需匹配一次

        return list(extracted)

    def _create_experience_record(
        self,
        user_input: str,
        placement_info: Dict,
        keywords: List[str],
        execution_result: Dict
    ) -> Dict:
        """
        模板化創建經驗記錄

        格式與 ExperienceDB 兼容
        """
        # 判斷 task_type
        task_type = "general"
        if any(kw in keywords for kw in ['wasp', 'aggregation']):
            task_type = "wasp"
        elif any(kw in keywords for kw in ['karamba', 'structural']):
            task_type = "structural"
        elif any(kw in keywords for kw in ['kangaroo', 'form finding']):
            task_type = "form_finding"
        elif any(kw in keywords for kw in ['ladybug', 'solar']):
            task_type = "environmental"

        return {
            "request": user_input,
            "solution": placement_info,
            "keywords": keywords,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            "success_count": 1,
            "usage_count": 1,
            "learned_patterns": list(set(
                execution_result.get("new_patterns", []) +
                execution_result.get("reinforced_patterns", [])
            ))[:10]  # 限制數量
        } 
