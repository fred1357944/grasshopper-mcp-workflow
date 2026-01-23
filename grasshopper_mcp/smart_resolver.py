#!/usr/bin/env python3
"""
GH_MCP Smart Resolver - 智能組件解析器

三層防護機制：
1. Registry 查詢 - 使用已驗證的可信 GUID
2. AI 判斷 - 根據上下文自動選擇最合適的組件
3. 人工確認 - 遇到不確定時詢問用戶

使用方式：
```python
resolver = SmartResolver(interactive=True)

# 解析組件 - 自動三層防護
guid = resolver.resolve("Line", context={"purpose": "connect two points"})

# 批量解析配置
fixed_config = resolver.resolve_placement_info(config)
```

2026-01-23
"""

import socket
import json
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

from .guid_registry import GUIDRegistry


class ResolutionMethod(Enum):
    """解析方法"""
    REGISTRY = "registry"      # 從已驗證 GUID 列表
    AI_INFERENCE = "ai"        # AI 根據上下文推斷
    USER_CONFIRM = "user"      # 用戶確認
    FALLBACK = "fallback"      # 降級到 GH_MCP 自動搜索


@dataclass
class ResolutionResult:
    """解析結果"""
    name: str
    guid: str
    category: str
    method: ResolutionMethod
    confidence: float  # 0.0 - 1.0
    alternatives: List[Dict]  # 其他候選


class SmartResolver:
    """
    智能組件解析器

    三層防護：
    1. Registry - 已驗證的 GUID，信心度 1.0
    2. AI 推斷 - 根據上下文選擇，信心度 0.7-0.9
    3. 人工確認 - 用戶選擇，信心度 1.0
    """

    # 組件用途關鍵字 → 類別映射
    PURPOSE_HINTS = {
        # Line 組件區分
        "connect two points": "Curve",
        "draw line": "Curve",
        "create line segment": "Curve",
        "line geometry": "Curve",
        "line parameter": "Params",
        "store line": "Params",
        "line input": "Params",

        # Point 組件區分
        "create point": "Vector",
        "construct point": "Vector",
        "point parameter": "Params",
        "point input": "Params",

        # Number 組件區分
        "slider": "Params",
        "input number": "Params",
        "parameter": "Params",
    }

    # 連接目標 → 推斷類別
    CONNECTION_HINTS = {
        # 如果 Line 的輸出連到 Pipe.Curve，那是 Curve 類別
        "Pipe.Curve": "Curve",
        "Pipe.C": "Curve",
        "Extrude.Base": "Surface",
        "Extrude.Direction": "Vector",
    }

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 8080,
        interactive: bool = True,
        ask_callback: Optional[Callable[[str, List[Dict]], str]] = None
    ):
        """
        Args:
            host: GH_MCP 主機
            port: GH_MCP 端口
            interactive: 是否啟用互動模式（詢問用戶）
            ask_callback: 自定義詢問函數，簽名: (question, options) -> selected_guid
        """
        self.host = host
        self.port = port
        self.interactive = interactive
        self.ask_callback = ask_callback or self._default_ask

        self.registry = GUIDRegistry(host=host, port=port)
        self._resolution_log: List[ResolutionResult] = []

    def _send_command(self, cmd_type: str, **params) -> dict:
        """發送命令到 GH_MCP"""
        command = {'type': cmd_type, 'parameters': params}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                s.shutdown(socket.SHUT_WR)
                response = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                return json.loads(response.decode('utf-8-sig'))
        except Exception as e:
            return {'error': str(e)}

    def _default_ask(self, question: str, options: List[Dict]) -> str:
        """默認的終端詢問函數"""
        print(f"\n⚠️ {question}\n")
        for i, opt in enumerate(options, 1):
            name = opt.get('name', 'Unknown')
            cat = opt.get('category', '')
            guid = opt.get('guid', '')[:16]
            inputs = opt.get('inputs', [])
            print(f"  [{i}] {name} ({cat})")
            print(f"      GUID: {guid}...")
            print(f"      輸入: {[p.get('name') for p in inputs]}")
            print()

        while True:
            try:
                choice = input("請選擇 (輸入數字): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return options[idx].get('guid')
            except (ValueError, KeyboardInterrupt):
                pass
            print("無效選擇，請重試")

    def resolve(
        self,
        name: str,
        context: Optional[Dict] = None,
        force_ask: bool = False
    ) -> ResolutionResult:
        """
        智能解析組件 GUID

        Args:
            name: 組件名稱 (e.g., "Line", "Division")
            context: 上下文信息
                - purpose: 用途描述 (e.g., "connect two points")
                - target_connection: 目標連接 (e.g., "Pipe.Curve")
            force_ask: 強制詢問用戶（即使有高信心度答案）

        Returns:
            ResolutionResult
        """
        context = context or {}
        alternatives = []

        # === 第一層：Registry 查詢 ===
        # 根據上下文推斷 category
        category = self._infer_category(name, context)

        if category:
            verified_guid = self.registry.VERIFIED_GUIDS.get((name, category))
            if verified_guid:
                result = ResolutionResult(
                    name=name,
                    guid=verified_guid,
                    category=category,
                    method=ResolutionMethod.REGISTRY,
                    confidence=1.0,
                    alternatives=[]
                )
                self._resolution_log.append(result)
                return result

        # === 第二層：AI 推斷 ===
        # 查詢所有候選
        search_result = self._send_command('get_component_candidates', name=name)
        if search_result.get('success'):
            candidates = search_result.get('data', {}).get('candidates', [])

            # 過濾掉 OBSOLETE
            valid_candidates = [c for c in candidates if not c.get('isObsolete')]

            if len(valid_candidates) == 1:
                # 只有一個候選，直接用
                c = valid_candidates[0]
                result = ResolutionResult(
                    name=c.get('name'),
                    guid=c.get('guid'),
                    category=c.get('category', ''),
                    method=ResolutionMethod.AI_INFERENCE,
                    confidence=0.95,
                    alternatives=[]
                )
                self._resolution_log.append(result)
                return result

            elif len(valid_candidates) > 1:
                # 多個候選，嘗試 AI 推斷
                alternatives = valid_candidates

                inferred = self._ai_select(name, valid_candidates, context)
                if inferred and not force_ask:
                    result = ResolutionResult(
                        name=inferred.get('name'),
                        guid=inferred.get('guid'),
                        category=inferred.get('category', ''),
                        method=ResolutionMethod.AI_INFERENCE,
                        confidence=0.8,
                        alternatives=alternatives
                    )
                    self._resolution_log.append(result)
                    return result

        # === 第三層：人工確認 ===
        if self.interactive and alternatives:
            question = f"組件 '{name}' 有多個版本，請選擇正確的："
            selected_guid = self.ask_callback(question, alternatives)

            selected = next((c for c in alternatives if c.get('guid') == selected_guid), None)
            if selected:
                result = ResolutionResult(
                    name=selected.get('name'),
                    guid=selected_guid,
                    category=selected.get('category', ''),
                    method=ResolutionMethod.USER_CONFIRM,
                    confidence=1.0,
                    alternatives=alternatives
                )
                self._resolution_log.append(result)

                # 記住用戶選擇，下次自動使用
                self._remember_choice(name, selected)

                return result

        # === 降級：讓 GH_MCP 自己處理 ===
        return ResolutionResult(
            name=name,
            guid="",
            category="",
            method=ResolutionMethod.FALLBACK,
            confidence=0.3,
            alternatives=alternatives
        )

    def _infer_category(self, name: str, context: Dict) -> Optional[str]:
        """根據上下文推斷組件類別"""
        # 1. 檢查 purpose
        purpose = context.get('purpose', '').lower()
        for hint, cat in self.PURPOSE_HINTS.items():
            if hint in purpose:
                return cat

        # 2. 檢查 target_connection
        target = context.get('target_connection', '')
        for hint, cat in self.CONNECTION_HINTS.items():
            if hint in target:
                return cat

        # 3. 使用 Registry 的 PREFERRED_CATEGORIES
        return self.registry.PREFERRED_CATEGORIES.get(name)

    def _ai_select(
        self,
        name: str,
        candidates: List[Dict],
        context: Dict
    ) -> Optional[Dict]:
        """AI 根據上下文選擇最合適的組件"""
        # 規則 1: 優先選擇 Curve 類別的 Line（用於幾何）
        if name == "Line":
            for c in candidates:
                if "Curve" in c.get('category', ''):
                    inputs = c.get('inputs', [])
                    input_names = [p.get('name', '') for p in inputs]
                    if 'Start Point' in input_names or 'End Point' in input_names:
                        return c

        # 規則 2: 優先選擇 Vector 類別的 Point
        if name == "Point" or name == "Construct Point":
            for c in candidates:
                if "Vector" in c.get('category', ''):
                    return c

        # 規則 3: 如果有 target_connection，匹配輸入類型
        target = context.get('target_connection', '')
        if target:
            # 例如 target = "Pipe.Curve"，我們需要輸出是 Line/Curve 的組件
            for c in candidates:
                outputs = c.get('outputs', [])
                for out in outputs:
                    out_name = out.get('name', '').lower()
                    if 'line' in out_name or 'curve' in out_name:
                        return c

        # 默認：返回第一個非 Params 類別的
        for c in candidates:
            if "Params" not in c.get('category', ''):
                return c

        return candidates[0] if candidates else None

    def _remember_choice(self, name: str, selected: Dict):
        """記住用戶選擇，更新 Registry"""
        category = selected.get('category', '')
        guid = selected.get('guid')

        if category and guid:
            # 動態添加到 VERIFIED_GUIDS
            key = (name, category)
            self.registry.VERIFIED_GUIDS[key] = guid
            print(f"   💾 已記住: {name} ({category}) → {guid[:16]}...")

    def resolve_placement_info(self, config: Dict) -> Dict:
        """
        智能解析整個 placement_info.json

        對每個缺少 GUID 的組件進行解析
        """
        import copy
        fixed = copy.deepcopy(config)

        print("\n=== 智能組件解析 ===\n")

        for comp in fixed.get('components', []):
            comp_type = comp.get('type')
            comp_id = comp.get('id')
            existing_guid = comp.get('guid')

            # 跳過 Slider（不需要 GUID）
            if comp_type == 'Number Slider':
                continue

            # 已有 GUID 的跳過
            if existing_guid:
                continue

            # 構建上下文
            context = self._build_context(comp, fixed)

            # 解析
            result = self.resolve(comp_type, context=context)

            if result.guid:
                comp['guid'] = result.guid
                method_icon = {
                    ResolutionMethod.REGISTRY: "📚",
                    ResolutionMethod.AI_INFERENCE: "🤖",
                    ResolutionMethod.USER_CONFIRM: "👤",
                    ResolutionMethod.FALLBACK: "⚠️",
                }[result.method]
                print(f"  {method_icon} {comp_id} ({comp_type}) → {result.guid[:16]}... [{result.method.value}]")

        return fixed

    def _build_context(self, comp: Dict, config: Dict) -> Dict:
        """從配置構建組件上下文"""
        comp_id = comp.get('id')
        connections = config.get('connections', [])

        # 找到這個組件的輸出連接
        target_connections = []
        for conn in connections:
            if conn.get('from') == comp_id:
                target = f"{conn.get('to')}.{conn.get('toParam')}"
                target_connections.append(target)

        return {
            'target_connection': target_connections[0] if target_connections else '',
            'all_targets': target_connections,
        }

    def get_resolution_log(self) -> List[ResolutionResult]:
        """獲取解析日誌"""
        return self._resolution_log.copy()

    def print_summary(self):
        """打印解析摘要"""
        if not self._resolution_log:
            print("沒有解析記錄")
            return

        print(f"\n=== 解析摘要 ({len(self._resolution_log)} 個組件) ===\n")

        by_method = {}
        for r in self._resolution_log:
            method = r.method.value
            by_method[method] = by_method.get(method, 0) + 1

        for method, count in sorted(by_method.items()):
            icon = {"registry": "📚", "ai": "🤖", "user": "👤", "fallback": "⚠️"}.get(method, "?")
            print(f"  {icon} {method}: {count} 個")


# 便捷函數
def smart_resolve(name: str, context: Optional[Dict] = None) -> str:
    """快速解析組件 GUID"""
    resolver = SmartResolver(interactive=False)
    result = resolver.resolve(name, context)
    return result.guid


if __name__ == '__main__':
    # 測試
    resolver = SmartResolver(interactive=True)

    print("=== 測試智能解析 ===\n")

    # 測試 Line 組件
    result = resolver.resolve("Line", context={"purpose": "connect two points"})
    print(f"Line (connect two points):")
    print(f"  GUID: {result.guid}")
    print(f"  Category: {result.category}")
    print(f"  Method: {result.method.value}")
    print(f"  Confidence: {result.confidence}")
    print()

    # 測試 Division 組件
    result = resolver.resolve("Division")
    print(f"Division:")
    print(f"  GUID: {result.guid}")
    print(f"  Method: {result.method.value}")
