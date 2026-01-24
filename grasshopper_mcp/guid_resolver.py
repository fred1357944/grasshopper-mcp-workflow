"""
GUID Resolver - 多層防護的組件 GUID 解析器

優先順序：
1. trusted_guids.json (100% 信心)
2. Pattern Library (80% 信心)
3. MCP get_component_candidates (需驗證)
"""

import json
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ResolvedComponent:
    """解析後的組件資訊"""
    name: str
    guid: str
    source: str  # 'trusted', 'pattern', 'mcp'
    confidence: float  # 0.0 - 1.0
    full_name: Optional[str] = None
    inputs: List[str] = None
    outputs: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.inputs is None:
            self.inputs = []
        if self.outputs is None:
            self.outputs = []
        if self.warnings is None:
            self.warnings = []


class GUIDResolver:
    """多層防護的 GUID 解析器"""

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # 預設使用專案根目錄的 config/
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        self.trusted_guids: Dict = {}
        self.pattern_guids: Dict = {}
        self.mcp_host = 'localhost'
        self.mcp_port = 8080

        self._load_trusted_guids()
        self._load_pattern_guids()

    def _load_trusted_guids(self):
        """載入可信 GUID 對照表"""
        trusted_path = self.config_dir / "trusted_guids.json"
        if trusted_path.exists():
            with open(trusted_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trusted_guids = data.get('components', {})
                self.known_conflicts = data.get('known_plugin_conflicts', {})
                print(f"[GUIDResolver] 載入 {len(self.trusted_guids)} 個可信組件")
        else:
            print(f"[GUIDResolver] 警告: trusted_guids.json 不存在")

    def _load_pattern_guids(self):
        """載入 Pattern Library 中的 GUID"""
        patterns_dir = self.config_dir.parent / "patterns"
        if patterns_dir.exists():
            for pattern_file in patterns_dir.glob("*.json"):
                try:
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        pattern = json.load(f)
                        for comp in pattern.get('components', []):
                            name = comp.get('type') or comp.get('name')
                            guid = comp.get('guid')
                            if name and guid and name not in self.pattern_guids:
                                self.pattern_guids[name] = guid
                except Exception as e:
                    pass
            if self.pattern_guids:
                print(f"[GUIDResolver] 載入 {len(self.pattern_guids)} 個 Pattern GUID")

    def _query_mcp(self, component_name: str) -> Optional[Dict]:
        """向 MCP 查詢組件"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.mcp_host, self.mcp_port))

            cmd = {
                'type': 'get_component_candidates',
                'parameters': {'name': component_name}
            }
            sock.sendall((json.dumps(cmd) + '\n').encode())

            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in chunk:
                    break

            sock.close()
            result = json.loads(response.decode('utf-8-sig').strip())

            if result.get('success') and result.get('data', {}).get('candidates'):
                return result['data']['candidates'][0]
            return None
        except Exception as e:
            return None

    def resolve(self, component_name: str) -> ResolvedComponent:
        """
        解析組件 GUID

        優先順序：
        1. trusted_guids.json (100% 信心)
        2. Pattern Library (80% 信心)
        3. MCP 查詢 (需驗證 Library)

        Returns:
            ResolvedComponent with guid, source, confidence, and warnings
        """
        warnings = []

        # 1. 先查 trusted_guids.json
        if component_name in self.trusted_guids:
            comp = self.trusted_guids[component_name]

            # 檢查已知衝突
            if 'known_conflicts' in comp:
                warnings.append(f"⚠️ 已知衝突: {', '.join(comp['known_conflicts'])}")

            return ResolvedComponent(
                name=component_name,
                guid=comp['guid'],
                source='trusted',
                confidence=1.0,
                full_name=comp.get('full_name'),
                inputs=comp.get('inputs', []),
                outputs=comp.get('outputs', []),
                warnings=warnings
            )

        # 2. 查 Pattern Library
        if component_name in self.pattern_guids:
            return ResolvedComponent(
                name=component_name,
                guid=self.pattern_guids[component_name],
                source='pattern',
                confidence=0.8,
                warnings=["來自 Pattern Library，建議驗證"]
            )

        # 3. 最後用 MCP 查詢
        mcp_result = self._query_mcp(component_name)
        if mcp_result:
            guid = mcp_result.get('guid')
            library = mcp_result.get('library', 'Unknown')
            actual_name = mcp_result.get('fullName') or mcp_result.get('name')

            # 檢查是否為原生 GH 組件
            if library != 'Grasshopper':
                warnings.append(f"⚠️ 非原生組件! Library: {library}")
                warnings.append(f"   實際組件: {actual_name}")
                confidence = 0.3
            else:
                confidence = 0.6

            # 檢查名稱是否匹配
            if actual_name and actual_name.lower() != component_name.lower():
                warnings.append(f"⚠️ 名稱不符! 查詢: {component_name}, 返回: {actual_name}")
                confidence *= 0.5

            return ResolvedComponent(
                name=component_name,
                guid=guid,
                source='mcp',
                confidence=confidence,
                full_name=actual_name,
                warnings=warnings
            )

        # 找不到
        return ResolvedComponent(
            name=component_name,
            guid=None,
            source='not_found',
            confidence=0.0,
            warnings=[f"❌ 找不到組件: {component_name}"]
        )

    def resolve_batch(self, component_names: List[str]) -> Dict[str, ResolvedComponent]:
        """批量解析組件"""
        results = {}
        for name in component_names:
            results[name] = self.resolve(name)
        return results

    def print_report(self, resolved: Dict[str, ResolvedComponent]):
        """印出解析報告"""
        print("\n" + "=" * 60)
        print("GUID 解析報告")
        print("=" * 60)

        for name, comp in resolved.items():
            status = "✅" if comp.confidence >= 0.8 else "⚠️" if comp.confidence >= 0.5 else "❌"
            print(f"\n{status} {name}")
            print(f"   GUID: {comp.guid or 'N/A'}")
            print(f"   來源: {comp.source} (信心: {comp.confidence*100:.0f}%)")
            if comp.full_name:
                print(f"   完整路徑: {comp.full_name}")
            for warn in comp.warnings:
                print(f"   {warn}")

        # 統計
        total = len(resolved)
        trusted = sum(1 for c in resolved.values() if c.source == 'trusted')
        pattern = sum(1 for c in resolved.values() if c.source == 'pattern')
        mcp = sum(1 for c in resolved.values() if c.source == 'mcp')
        not_found = sum(1 for c in resolved.values() if c.source == 'not_found')

        print("\n" + "-" * 60)
        print(f"統計: {total} 組件")
        print(f"  - trusted (100%): {trusted}")
        print(f"  - pattern (80%):  {pattern}")
        print(f"  - mcp (需驗證):   {mcp}")
        print(f"  - 找不到:         {not_found}")


# 便捷函數
_resolver = None

def get_resolver() -> GUIDResolver:
    """取得全域 Resolver 實例"""
    global _resolver
    if _resolver is None:
        _resolver = GUIDResolver()
    return _resolver

def resolve_guid(component_name: str) -> str:
    """快速解析單一組件 GUID"""
    result = get_resolver().resolve(component_name)
    if result.warnings:
        for warn in result.warnings:
            print(f"  {warn}")
    return result.guid


if __name__ == "__main__":
    # 測試
    resolver = GUIDResolver()

    test_components = [
        "Number Slider",
        "Series",
        "Multiplication",
        "Division",
        "Sine",
        "Cosine",
        "Construct Point",
        "Center Box",
        "Rotate",
        "Cylinder",
        "Interpolate",
        "Pipe",
        "Unknown Component"
    ]

    results = resolver.resolve_batch(test_components)
    resolver.print_report(results)
