#!/usr/bin/env python3
"""
GH_MCP Knowledge Base - 知識查詢層

整合 trusted_guids.json、mcp_commands.json、connection_patterns.json
提供統一的知識查詢介面，讓 Claude 在需要時即時查詢正確信息。

核心設計理念：
- 不讓 Claude 記住 GUID/連接方式
- 讓系統記住並在需要時快速提供

使用方式：
```python
from grasshopper_mcp.knowledge_base import GHKnowledgeBase
kb = GHKnowledgeBase()

# 查組件 GUID
kb.get_component_guid("Face Normals")
# → {"guid": "f4370b82...", "inputs": ["M"], "outputs": ["C", "N"]}

# 查模式
kb.get_pattern("WASP_Stochastic")
# → {"description": "...", "wiring": [...]}

# 檢查命令
kb.is_command_available("clear_canvas")
# → False
kb.get_workaround("clear_canvas")
# → "用戶手動 Ctrl+A → Delete"
```

2026-01-24
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class ComponentInfo:
    """組件資訊"""
    guid: str
    name: str
    category: str
    inputs: List[str]
    outputs: List[str]
    notes: Optional[str] = None
    known_conflicts: Optional[List[str]] = None


@dataclass
class PatternInfo:
    """連接模式資訊"""
    name: str
    description: str
    category: str
    wiring: List[List[Any]]  # [from, to, from_idx, to_idx]
    keywords: List[str]
    notes: Optional[List[str]] = None


@dataclass
class CommandInfo:
    """MCP 命令資訊"""
    name: str
    description: str
    required: List[str]
    optional: List[str]
    notes: Optional[List[str]] = None


class GHKnowledgeBase:
    """
    Grasshopper 知識庫 - 提供組件、連接模式、MCP 命令的即時查詢

    三層知識結構：
    1. 組件層 (trusted_guids.json) - GUID、輸入輸出參數
    2. 模式層 (connection_patterns.json) - 17 種連接模式
    3. 命令層 (mcp_commands.json) - 可用/不可用命令
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化知識庫

        Args:
            config_dir: 配置目錄路徑，預設為 project_root/config
        """
        if config_dir is None:
            # 嘗試多個可能的路徑
            possible_paths = [
                Path(__file__).parent.parent / "config",  # 相對於此檔案
                Path.cwd() / "config",  # 當前工作目錄
                Path("/Users/laihongyi/Downloads/grasshopper-mcp-workflow/config"),  # 絕對路徑
            ]
            for p in possible_paths:
                if p.exists():
                    config_dir = p
                    break
            else:
                config_dir = possible_paths[0]  # 使用第一個作為預設

        self.config_dir = Path(config_dir)
        self._guids: Dict = {}
        self._commands: Dict = {}
        self._patterns: Dict = {}
        self._loaded = False

    def _ensure_loaded(self):
        """確保知識已載入"""
        if not self._loaded:
            self._load_knowledge()
            self._loaded = True

    def _load_json(self, filename: str) -> Dict:
        """載入 JSON 配置檔"""
        filepath = self.config_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_knowledge(self):
        """載入所有配置文件"""
        self._guids = self._load_json("trusted_guids.json")
        self._commands = self._load_json("mcp_commands.json")
        self._patterns = self._load_json("connection_patterns.json")

    # ==================== 組件查詢 ====================

    def get_component_guid(self, name: str) -> Optional[Dict]:
        """
        查詢組件 GUID 和參數信息

        Args:
            name: 組件名稱 (e.g., "Face Normals", "Number Slider")

        Returns:
            組件資訊字典，包含 guid, inputs, outputs 等

        Example:
            >>> kb.get_component_guid("Face Normals")
            {'guid': 'f4370b82-...', 'inputs': ['M'], 'outputs': ['C', 'N']}
        """
        self._ensure_loaded()
        return self._guids.get("components", {}).get(name)

    def get_component_by_guid(self, guid: str) -> Optional[Tuple[str, Dict]]:
        """
        根據 GUID 反查組件名稱和資訊

        Args:
            guid: 組件 GUID

        Returns:
            (name, info) 元組，或 None
        """
        self._ensure_loaded()
        components = self._guids.get("components", {})
        for name, info in components.items():
            if info.get("guid") == guid:
                return (name, info)
        return None

    def list_components(self, category: Optional[str] = None) -> List[str]:
        """
        列出所有已知組件

        Args:
            category: 可選，過濾特定類別

        Returns:
            組件名稱列表
        """
        self._ensure_loaded()
        components = self._guids.get("components", {})
        if category:
            return [
                name for name, info in components.items()
                if info.get("category", "").lower() == category.lower()
            ]
        return list(components.keys())

    def get_known_conflicts(self, component_name: str) -> Optional[List[str]]:
        """
        獲取組件的已知衝突列表

        Args:
            component_name: 組件名稱

        Returns:
            衝突的插件/組件列表
        """
        self._ensure_loaded()
        info = self._guids.get("components", {}).get(component_name, {})
        return info.get("known_conflicts")

    # ==================== 模式查詢 ====================

    def get_pattern(self, name: str) -> Optional[Dict]:
        """
        查詢連接模式

        Args:
            name: 模式名稱 (e.g., "WASP_Stochastic", "Karamba_Structural")

        Returns:
            模式資訊字典，包含 description, wiring, keywords 等

        Example:
            >>> kb.get_pattern("WASP_Stochastic")
            {'description': 'WASP 隨機聚集', 'wiring': [...], 'keywords': [...]}
        """
        self._ensure_loaded()
        return self._patterns.get("patterns", {}).get(name)

    def search_patterns(self, keyword: str) -> List[Dict]:
        """
        根據關鍵字搜索模式

        Args:
            keyword: 搜索關鍵字 (支援中英文)

        Returns:
            匹配的模式列表

        Example:
            >>> kb.search_patterns("wasp")
            [{'name': 'WASP_Stochastic', ...}, {'name': 'WASP_Aggregation', ...}]
        """
        self._ensure_loaded()
        results = []
        patterns = self._patterns.get("patterns", {})
        keyword_lower = keyword.lower()

        for name, pattern in patterns.items():
            # 搜索關鍵字列表
            keywords = pattern.get("keywords", [])
            if any(keyword_lower in kw.lower() for kw in keywords):
                results.append({"name": name, **pattern})
                continue

            # 搜索描述
            description = pattern.get("description", "")
            if keyword_lower in description.lower():
                results.append({"name": name, **pattern})
                continue

            # 搜索模式名稱
            if keyword_lower in name.lower():
                results.append({"name": name, **pattern})

        return results

    def list_patterns(self, category: Optional[str] = None) -> List[str]:
        """
        列出所有連接模式

        Args:
            category: 可選，過濾特定類別

        Returns:
            模式名稱列表
        """
        self._ensure_loaded()
        patterns = self._patterns.get("patterns", {})
        if category:
            return [
                name for name, info in patterns.items()
                if info.get("category", "").lower() == category.lower()
            ]
        return list(patterns.keys())

    def get_pattern_categories(self) -> Dict[str, str]:
        """
        獲取所有模式類別及其描述

        Returns:
            {category_name: description}
        """
        self._ensure_loaded()
        return self._patterns.get("categories", {})

    # ==================== 命令查詢 ====================

    def is_command_available(self, cmd: str) -> bool:
        """
        檢查 MCP 命令是否可用

        Args:
            cmd: 命令名稱 (e.g., "add_component", "clear_canvas")

        Returns:
            True 如果命令可用

        Example:
            >>> kb.is_command_available("add_component")
            True
            >>> kb.is_command_available("clear_canvas")
            False
        """
        self._ensure_loaded()
        return cmd in self._commands.get("available", {})

    def get_command_info(self, cmd: str) -> Optional[Dict]:
        """
        獲取命令的詳細資訊

        Args:
            cmd: 命令名稱

        Returns:
            命令資訊字典，包含 description, required, optional 等
        """
        self._ensure_loaded()
        return self._commands.get("available", {}).get(cmd)

    def get_workaround(self, cmd: str) -> Optional[str]:
        """
        獲取不可用命令的替代方案

        Args:
            cmd: 不可用的命令名稱

        Returns:
            替代方案說明

        Example:
            >>> kb.get_workaround("clear_canvas")
            "用戶手動操作：Ctrl+A (全選) → Delete"
        """
        self._ensure_loaded()
        return self._commands.get("workarounds", {}).get(cmd)

    def list_available_commands(self) -> List[str]:
        """
        列出所有可用命令

        Returns:
            命令名稱列表
        """
        self._ensure_loaded()
        return list(self._commands.get("available", {}).keys())

    def list_unavailable_commands(self) -> List[str]:
        """
        列出所有不可用命令

        Returns:
            不可用命令名稱列表
        """
        self._ensure_loaded()
        return self._commands.get("unavailable", [])

    def get_common_mistakes(self) -> Dict[str, Dict]:
        """
        獲取常見錯誤及正確做法

        Returns:
            {mistake_id: {wrong, correct, reason}}
        """
        self._ensure_loaded()
        return self._commands.get("common_mistakes", {})

    # ==================== 綜合查詢 ====================

    def quick_lookup(self, query: str) -> Dict[str, Any]:
        """
        快速查詢 - 自動判斷查詢類型

        Args:
            query: 查詢字串

        Returns:
            查詢結果

        Example:
            >>> kb.quick_lookup("Face Normals")
            {'type': 'component', 'result': {...}}
            >>> kb.quick_lookup("wasp")
            {'type': 'patterns', 'result': [...]}
        """
        self._ensure_loaded()

        # 1. 嘗試精確匹配組件
        comp = self.get_component_guid(query)
        if comp:
            return {"type": "component", "name": query, "result": comp}

        # 2. 嘗試精確匹配模式
        pattern = self.get_pattern(query)
        if pattern:
            return {"type": "pattern", "name": query, "result": pattern}

        # 3. 嘗試匹配命令
        if self.is_command_available(query):
            return {"type": "command", "name": query, "result": self.get_command_info(query)}

        # 4. 模糊搜索模式
        patterns = self.search_patterns(query)
        if patterns:
            return {"type": "patterns", "query": query, "result": patterns}

        # 5. 搜索組件（部分匹配）
        components = self._guids.get("components", {})
        matching_comps = [
            {"name": name, **info}
            for name, info in components.items()
            if query.lower() in name.lower()
        ]
        if matching_comps:
            return {"type": "components", "query": query, "result": matching_comps}

        return {"type": "not_found", "query": query, "result": None}

    def get_summary(self) -> Dict[str, int]:
        """
        獲取知識庫摘要

        Returns:
            統計資訊
        """
        self._ensure_loaded()
        return {
            "total_components": len(self._guids.get("components", {})),
            "total_patterns": len(self._patterns.get("patterns", {})),
            "available_commands": len(self._commands.get("available", {})),
            "unavailable_commands": len(self._commands.get("unavailable", [])),
        }

    def print_quick_reference(self):
        """打印快速參考"""
        self._ensure_loaded()
        print("=== GH_MCP 知識庫快速參考 ===\n")

        print("【可用 MCP 命令】")
        for cmd in self.list_available_commands():
            print(f"  • {cmd}")

        print("\n【不可用命令】")
        for cmd in self.list_unavailable_commands():
            workaround = self.get_workaround(cmd)
            print(f"  ✗ {cmd}" + (f" → {workaround}" if workaround else ""))

        print("\n【連接模式類別】")
        for cat, desc in self.get_pattern_categories().items():
            print(f"  • {cat}: {desc}")

        print("\n【統計】")
        summary = self.get_summary()
        print(f"  組件: {summary['total_components']} 個")
        print(f"  模式: {summary['total_patterns']} 種")


# ==================== 便捷函數 ====================

_kb_instance: Optional[GHKnowledgeBase] = None


def get_knowledge_base() -> GHKnowledgeBase:
    """獲取全局知識庫實例（單例模式）"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = GHKnowledgeBase()
    return _kb_instance


def lookup(query: str) -> Dict[str, Any]:
    """便捷查詢函數"""
    return get_knowledge_base().quick_lookup(query)


def is_cmd_ok(cmd: str) -> bool:
    """檢查命令是否可用"""
    return get_knowledge_base().is_command_available(cmd)


def get_guid(component: str) -> Optional[str]:
    """快速獲取組件 GUID"""
    info = get_knowledge_base().get_component_guid(component)
    return info.get("guid") if info else None


if __name__ == "__main__":
    # 測試
    kb = GHKnowledgeBase()
    kb.print_quick_reference()

    print("\n=== 測試查詢 ===\n")

    # 測試組件查詢
    print("查詢 'Face Normals':")
    result = kb.get_component_guid("Face Normals")
    print(f"  {result}\n")

    # 測試模式搜索
    print("搜索 'wasp':")
    results = kb.search_patterns("wasp")
    for r in results:
        print(f"  • {r['name']}: {r['description']}")

    # 測試命令檢查
    print("\n命令檢查:")
    print(f"  add_component: {kb.is_command_available('add_component')}")
    print(f"  clear_canvas: {kb.is_command_available('clear_canvas')}")
    print(f"  → 替代方案: {kb.get_workaround('clear_canvas')}")
