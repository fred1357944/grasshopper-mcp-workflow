#!/usr/bin/env python3
"""
GH_MCP 自動排錯系統 (Auto Debugger)

設計理念：
1. 自動偵測 → 2. 智能診斷 → 3. 建議修正 → 4. 人機協作精緻化

錯誤類型：
- Type A: 組件 GUID 錯誤 (選到錯誤版本)
- Type B: 參數名錯誤 (A vs Start Point)
- Type C: 資料類型不匹配 (Point → Line)
- Type D: 連接邏輯錯誤 (缺少必要輸入)

2026-01-23
"""

import socket
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """錯誤類型"""
    GUID_MISMATCH = "guid_mismatch"          # 組件 GUID 選錯版本
    PARAM_NAME = "param_name"                # 參數名不匹配
    DATA_TYPE = "data_type"                  # 資料類型轉換失敗
    MISSING_INPUT = "missing_input"          # 缺少必要輸入
    COMPONENT_NOT_FOUND = "component_not_found"  # 組件找不到
    UNKNOWN = "unknown"


@dataclass
class DiagnosticResult:
    """診斷結果"""
    error_type: ErrorType
    component_id: str
    component_type: str
    description: str
    suggested_fix: str
    confidence: float  # 0.0 - 1.0
    fix_params: Optional[Dict] = None


class GHAutoDebugger:
    """
    Grasshopper 自動排錯系統

    使用方式：
    ```python
    debugger = GHAutoDebugger()

    # 執行部署後，分析畫布狀態
    errors = debugger.scan_canvas()

    # 顯示診斷報告
    debugger.print_report(errors)

    # 自動修正（需用戶確認）
    for err in errors:
        if err.confidence > 0.8:
            debugger.apply_fix(err)
    ```
    """

    # 常見組件 GUID 映射表 (正確版本)
    TRUSTED_GUIDS = {
        # 兩點線段組件 (不是曲線版本)
        "Line": "31957fba-b08b-45f9-9ec0-5f9e52d3236b",
        # SDL 線段 (起點、方向、長度)
        "Line SDL": "834dbb21-1c30-4be5-8e38-b7330e2c9d37",
        # 基礎數學
        "Division": "b16a2ec0-f873-4ef7-8e0c-a068e7571cb4",
        "Subtraction": "0ff0bb57-8207-48a0-a732-6fd4d4931193",
        "Multiplication": "ba265c5c-ea9a-43f0-a35d-0d93e9ea5041",
        "Addition": "13975a0f-0f14-4b3d-a2a8-7f40bf7b0637",
        "Series": "651c4fa5-dff4-4be6-ba31-6dc267d3ab47",
        "Negative": "5ef3b98f-0d72-414d-b58f-a9fe3c7dd8cf",
        # 幾何基礎
        "Construct Point": "3581f42a-9592-4549-bd6b-1c0fc39d067b",
        "XY Plane": "a396a2e3-4a7a-4b4d-8e0f-5a6f7c8d9e0b",
        "Center Box": "d1296e28-f64c-4c2a-9a9e-49e7839460de",
        "Cylinder": "4edaf2ed-7b3a-42ed-bce0-3119ed106792",
        "Pipe": "1ee25749-2e2d-4fc6-9209-0ea0515081f9",
        "Circle": "55c7e69f-2c48-4c32-91d0-2d46e9f98a4d",
    }

    # 參數名映射表 (組件類型 → {舊名: 新名})
    PARAM_MAPPINGS = {
        "Line": {
            "A": "Start Point",
            "B": "End Point",
            "L": "Line",
        },
        "Division": {
            "R": "Result",
        },
        "Subtraction": {
            "R": "Result",
        },
        "Multiplication": {
            "R": "Result",
        },
        "Negative": {
            "x": "Result",
        },
        "Series": {
            "S": "Series",
        },
        "Construct Point": {
            "Pt": "Point",
        },
    }

    # 錯誤訊息模式 → 錯誤類型
    ERROR_PATTERNS = {
        "Data conversion failed": ErrorType.DATA_TYPE,
        "Parameter not found": ErrorType.PARAM_NAME,
        "Component not found": ErrorType.COMPONENT_NOT_FOUND,
        "GUID": ErrorType.GUID_MISMATCH,
    }

    def __init__(self, host: str = '127.0.0.1', port: int = 8080):
        self.host = host
        self.port = port
        self._diagnostics: List[DiagnosticResult] = []

    def send_command(self, cmd_type: str, **params) -> dict:
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

    def scan_canvas(self) -> List[DiagnosticResult]:
        """
        掃描畫布上的錯誤組件

        Returns:
            診斷結果列表
        """
        self._diagnostics.clear()

        # 獲取文檔資訊
        doc_info = self.send_command('get_document_info')
        if not doc_info.get('success'):
            return []

        components = doc_info.get('data', {}).get('components', [])

        for comp in components:
            # 檢查是否有錯誤
            has_error = comp.get('hasError', False) or comp.get('runtimeMessageLevel') == 'Error'

            if has_error:
                diagnostic = self._diagnose_component(comp)
                if diagnostic:
                    self._diagnostics.append(diagnostic)

        return self._diagnostics

    def _diagnose_component(self, comp: Dict) -> Optional[DiagnosticResult]:
        """
        診斷單個組件的問題
        """
        comp_id = comp.get('instanceGuid', comp.get('id', 'unknown'))
        comp_type = comp.get('type', comp.get('name', 'unknown'))
        error_msg = comp.get('runtimeMessage', '')

        # 1. 檢查錯誤訊息模式
        error_type = ErrorType.UNKNOWN
        for pattern, etype in self.ERROR_PATTERNS.items():
            if pattern.lower() in error_msg.lower():
                error_type = etype
                break

        # 2. 根據錯誤類型生成診斷
        if error_type == ErrorType.DATA_TYPE:
            return self._diagnose_data_type_error(comp_id, comp_type, error_msg)
        elif error_type == ErrorType.PARAM_NAME:
            return self._diagnose_param_error(comp_id, comp_type, error_msg)
        elif error_type == ErrorType.GUID_MISMATCH:
            return self._diagnose_guid_error(comp_id, comp_type, error_msg)
        else:
            return DiagnosticResult(
                error_type=error_type,
                component_id=comp_id,
                component_type=comp_type,
                description=error_msg,
                suggested_fix="請手動檢查此組件",
                confidence=0.3
            )

    def _diagnose_data_type_error(
        self, comp_id: str, comp_type: str, error_msg: str
    ) -> DiagnosticResult:
        """
        診斷資料類型轉換錯誤

        常見原因：
        1. Line 組件選錯版本 (Curve vs Point)
        2. 輸入參數連接錯誤
        """
        # 解析錯誤訊息 "Data conversion failed from X to Y"
        parts = error_msg.split("from")
        if len(parts) > 1:
            conversion = parts[1].strip()  # "Point to Line"
        else:
            conversion = "unknown"

        # Line 組件特殊處理
        if "Line" in comp_type and "Point to Line" in error_msg:
            correct_guid = self.TRUSTED_GUIDS.get("Line")
            return DiagnosticResult(
                error_type=ErrorType.GUID_MISMATCH,
                component_id=comp_id,
                component_type=comp_type,
                description=f"Line 組件版本錯誤 ({conversion})",
                suggested_fix=f"替換為正確的 Line 組件 (GUID: {correct_guid})",
                confidence=0.95,
                fix_params={
                    "action": "replace_component",
                    "new_guid": correct_guid,
                    "param_mapping": self.PARAM_MAPPINGS.get("Line", {})
                }
            )

        return DiagnosticResult(
            error_type=ErrorType.DATA_TYPE,
            component_id=comp_id,
            component_type=comp_type,
            description=f"資料類型轉換失敗: {conversion}",
            suggested_fix="檢查輸入連接的資料類型",
            confidence=0.6
        )

    def _diagnose_param_error(
        self, comp_id: str, comp_type: str, error_msg: str
    ) -> DiagnosticResult:
        """
        診斷參數名錯誤
        """
        # 查找可能的正確參數名
        mappings = self.PARAM_MAPPINGS.get(comp_type, {})

        return DiagnosticResult(
            error_type=ErrorType.PARAM_NAME,
            component_id=comp_id,
            component_type=comp_type,
            description=f"參數名不匹配",
            suggested_fix=f"嘗試參數映射: {mappings}",
            confidence=0.7,
            fix_params={
                "action": "remap_params",
                "mappings": mappings
            }
        )

    def _diagnose_guid_error(
        self, comp_id: str, comp_type: str, error_msg: str
    ) -> DiagnosticResult:
        """
        診斷 GUID 錯誤
        """
        correct_guid = self.TRUSTED_GUIDS.get(comp_type)

        return DiagnosticResult(
            error_type=ErrorType.GUID_MISMATCH,
            component_id=comp_id,
            component_type=comp_type,
            description=f"組件 GUID 可能有誤",
            suggested_fix=f"使用 trusted GUID: {correct_guid}" if correct_guid else "手動查詢正確 GUID",
            confidence=0.8 if correct_guid else 0.4,
            fix_params={
                "action": "replace_guid",
                "new_guid": correct_guid
            } if correct_guid else None
        )

    def print_report(self, diagnostics: Optional[List[DiagnosticResult]] = None):
        """
        打印診斷報告
        """
        diags = diagnostics or self._diagnostics

        if not diags:
            print("\n✅ 沒有偵測到錯誤")
            return

        print(f"\n{'='*60}")
        print(f"GH_MCP 自動診斷報告")
        print(f"{'='*60}")
        print(f"偵測到 {len(diags)} 個問題\n")

        for i, d in enumerate(diags, 1):
            confidence_bar = "█" * int(d.confidence * 10) + "░" * (10 - int(d.confidence * 10))
            print(f"[{i}] {d.component_type} ({d.component_id[:8]}...)")
            print(f"    類型: {d.error_type.value}")
            print(f"    描述: {d.description}")
            print(f"    建議: {d.suggested_fix}")
            print(f"    信心: {confidence_bar} {d.confidence:.0%}")
            if d.fix_params:
                print(f"    修正參數: {d.fix_params}")
            print()

        print(f"{'='*60}")
        print(f"💡 高信心度修正 (>80%) 可自動應用")
        print(f"   低信心度修正建議人工確認")
        print(f"{'='*60}\n")

    def get_auto_fixes(self, min_confidence: float = 0.8) -> List[DiagnosticResult]:
        """
        獲取可自動修正的問題列表

        Args:
            min_confidence: 最低信心度閾值
        """
        return [d for d in self._diagnostics if d.confidence >= min_confidence]

    def suggest_placement_fixes(self, placement_info: Dict) -> List[Dict]:
        """
        分析 placement_info.json 並建議修正

        這是「預防性診斷」- 在部署前檢查配置檔
        """
        suggestions = []

        components = placement_info.get('components', [])
        connections = placement_info.get('connections', [])

        # 1. 檢查組件 GUID
        for comp in components:
            comp_type = comp.get('type')
            comp_guid = comp.get('guid')

            if comp_type in self.TRUSTED_GUIDS:
                trusted = self.TRUSTED_GUIDS[comp_type]
                if comp_guid and comp_guid != trusted:
                    suggestions.append({
                        'type': 'guid_warning',
                        'component_id': comp.get('id'),
                        'component_type': comp_type,
                        'current_guid': comp_guid,
                        'trusted_guid': trusted,
                        'message': f"{comp_type} 的 GUID 可能有誤，建議使用 {trusted[:8]}..."
                    })

        # 2. 檢查參數名
        for conn in connections:
            from_param = conn.get('fromParam')
            to_param = conn.get('toParam')

            # 找到對應的組件類型
            from_id = conn.get('from')
            to_id = conn.get('to')

            from_comp = next((c for c in components if c.get('id') == from_id), None)
            to_comp = next((c for c in components if c.get('id') == to_id), None)

            if from_comp:
                from_type = from_comp.get('type')
                if from_type in self.PARAM_MAPPINGS:
                    mappings = self.PARAM_MAPPINGS[from_type]
                    if from_param in mappings:
                        suggestions.append({
                            'type': 'param_warning',
                            'connection': f"{from_id}.{from_param} → {to_id}.{to_param}",
                            'message': f"參數 '{from_param}' 可能需要改為 '{mappings[from_param]}'"
                        })

            if to_comp:
                to_type = to_comp.get('type')
                if to_type in self.PARAM_MAPPINGS:
                    mappings = self.PARAM_MAPPINGS[to_type]
                    if to_param in mappings:
                        suggestions.append({
                            'type': 'param_warning',
                            'connection': f"{from_id}.{from_param} → {to_id}.{to_param}",
                            'message': f"參數 '{to_param}' 可能需要改為 '{mappings[to_param]}'"
                        })

        return suggestions


def validate_before_deploy(placement_path: str) -> bool:
    """
    部署前驗證 (便捷函數)

    Args:
        placement_path: placement_info.json 路徑

    Returns:
        是否通過驗證
    """
    import json
    from pathlib import Path

    with open(placement_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    debugger = GHAutoDebugger()
    suggestions = debugger.suggest_placement_fixes(config)

    if suggestions:
        print(f"\n⚠️ 發現 {len(suggestions)} 個潛在問題:\n")
        for s in suggestions:
            print(f"  • [{s['type']}] {s['message']}")
        print()
        return False

    print("✅ 配置檔驗證通過")
    return True


if __name__ == '__main__':
    # 測試：掃描當前畫布
    debugger = GHAutoDebugger()
    errors = debugger.scan_canvas()
    debugger.print_report(errors)
