#!/usr/bin/env python3
"""
Vision Diagnostic Client - 連接 GH_MCP_Vision (8081)
==================================================

功能：
- diagnose_connection: AI 分析連接失敗
- auto_fix_connection: AI 建議修復
- learn_from_failure: 批量學習失敗模式
- capture_canvas: 截取畫布截圖

整合到 WorkflowExecutor 的失敗處理流程。
"""

import socket
import json
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class DiagnosticLevel(Enum):
    """診斷層級"""
    QUICK = "quick"       # 快速診斷（不調用 AI）
    STANDARD = "standard" # 標準診斷（調用 AI）
    DEEP = "deep"         # 深度分析（批量學習）


@dataclass
class DiagnosticResult:
    """診斷結果"""
    success: bool
    cause: Optional[str] = None
    solution: Optional[str] = None
    correct_params: Optional[Dict[str, str]] = None
    risk_level: str = "info"
    raw_response: Optional[str] = None
    patterns_learned: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    error: Optional[str] = None


class VisionDiagnosticClient:
    """
    GH_MCP_Vision 客戶端

    連接到 8081 端口，提供診斷功能。
    """

    def __init__(self, host: str = "localhost", port: int = 8081, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """建立連接"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"[VisionDiagnostic] Connection failed: {e}")
            self._socket = None
            return False

    def disconnect(self):
        """關閉連接"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

    def _send_command(self, command_type: str, parameters: Optional[Dict] = None) -> Dict:
        """發送命令並接收回應"""
        if not self._socket:
            if not self.connect():
                return {"success": False, "error": "Cannot connect to GH_MCP_Vision"}

        try:
            command = {
                "type": command_type,
                "parameters": parameters or {}
            }

            # 發送 (socket 已確認非 None)
            message = json.dumps(command) + "\n"
            sock = self._socket
            assert sock is not None
            sock.sendall(message.encode('utf-8'))

            # 接收
            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk

            response_str = buffer.decode('utf-8').strip()
            return json.loads(response_str)

        except socket.timeout:
            return {"success": False, "error": "Connection timeout"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def diagnose_connection(
        self,
        source_component: str,
        source_param: str,
        target_component: str,
        target_param: str,
        error_message: str
    ) -> DiagnosticResult:
        """
        診斷連接失敗

        調用 GH_MCP_Vision::diagnose_connection，使用 Gemini 分析原因。

        Args:
            source_component: 來源組件類型
            source_param: 來源參數名
            target_component: 目標組件類型
            target_param: 目標參數名
            error_message: 錯誤訊息

        Returns:
            DiagnosticResult
        """
        response = self._send_command("diagnose_connection", {
            "source_component": source_component,
            "source_param": source_param,
            "target_component": target_component,
            "target_param": target_param,
            "error_message": error_message
        })

        if not response.get("success"):
            return DiagnosticResult(
                success=False,
                error=response.get("error", "Unknown error")
            )

        data = response.get("data", {})

        return DiagnosticResult(
            success=True,
            cause=data.get("cause"),
            solution=data.get("solution"),
            correct_params=data.get("correct_params"),
            raw_response=data.get("raw_response")
        )

    def auto_fix_connection(
        self,
        source_id: str,
        target_id: str,
        original_error: str
    ) -> Dict:
        """
        自動修復連接

        先診斷，再嘗試使用正確參數重新連接。

        Args:
            source_id: 來源組件 ID
            target_id: 目標組件 ID
            original_error: 原始錯誤

        Returns:
            包含 fixed, new_connection, diagnosis 的字典
        """
        response = self._send_command("auto_fix_connection", {
            "source_id": source_id,
            "target_id": target_id,
            "error": original_error
        })

        return response.get("data", response)

    def learn_from_failure(self, failures: List[Dict]) -> DiagnosticResult:
        """
        從失敗記錄中學習模式

        批量分析失敗，提取共同模式和建議。

        Args:
            failures: 失敗記錄列表，每個包含：
                - source_component, source_param
                - target_component, target_param
                - error_message

        Returns:
            DiagnosticResult，包含 patterns_learned 和 suggestions
        """
        response = self._send_command("learn_from_failure", {
            "failures": failures
        })

        if not response.get("success"):
            return DiagnosticResult(
                success=False,
                error=response.get("error", "Unknown error")
            )

        data = response.get("data", {})

        return DiagnosticResult(
            success=True,
            patterns_learned=data.get("patterns_learned", []),
            suggestions=data.get("suggestions", []),
            raw_response=data.get("raw_response")
        )

    def get_connection_diagnostics(self) -> Dict:
        """
        獲取當前畫布的連接診斷

        掃描所有連接，檢測潛在問題。

        Returns:
            包含 total_connections, issues, warnings 的字典
        """
        response = self._send_command("get_connection_diagnostics", {})
        return response.get("data", response)

    def capture_canvas(self, bounds: Optional[Dict] = None) -> Optional[str]:
        """
        截取畫布截圖

        Args:
            bounds: 可選的截取區域 {x, y, width, height}

        Returns:
            Base64 編碼的 PNG 圖片，失敗返回 None
        """
        params = {}
        if bounds:
            params["bounds"] = bounds

        response = self._send_command("capture_canvas", params)

        if response.get("success"):
            return response.get("data", {}).get("image")
        return None

    def is_available(self) -> bool:
        """檢查 Vision 服務是否可用"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except:
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ANN001
        self.disconnect()


# ============================================================================
# Integration Helper
# ============================================================================

class ExecutionDiagnosticHelper:
    """
    執行診斷輔助器

    整合到 WorkflowExecutor，在執行失敗時自動調用診斷。
    """

    def __init__(self, vision_client: Optional[VisionDiagnosticClient] = None):
        self.vision = vision_client or VisionDiagnosticClient()
        self.failure_buffer: List[Dict] = []
        self.max_buffer_size = 20

    def diagnose_execution_failure(
        self,
        config: Dict,  # noqa: ARG002
        errors: List[str],
        level: DiagnosticLevel = DiagnosticLevel.QUICK
    ) -> Dict:
        """
        診斷執行失敗

        Args:
            config: 執行的配置
            errors: 錯誤列表
            level: 診斷層級

        Returns:
            診斷報告
        """
        report = {
            "diagnosed": False,
            "diagnostics": [],
            "patterns": [],
            "suggestions": [],
            "screenshots": []
        }

        # 檢查 Vision 服務
        if not self.vision.is_available():
            report["error"] = "GH_MCP_Vision service not available (port 8081)"
            return report

        # 連接
        if not self.vision.connect():
            report["error"] = "Failed to connect to GH_MCP_Vision"
            return report

        try:
            # 從錯誤中提取連接失敗
            connection_failures = self._extract_connection_failures(errors)

            for failure in connection_failures:
                if level == DiagnosticLevel.QUICK:
                    # 快速診斷：只記錄
                    report["diagnostics"].append({
                        "type": "connection_failure",
                        "details": failure,
                        "ai_analyzed": False
                    })
                else:
                    # 標準/深度診斷：調用 AI
                    result = self.vision.diagnose_connection(
                        source_component=failure.get("source_component", "Unknown"),
                        source_param=failure.get("source_param", "Unknown"),
                        target_component=failure.get("target_component", "Unknown"),
                        target_param=failure.get("target_param", "Unknown"),
                        error_message=failure.get("error", "Unknown error")
                    )

                    if result.success:
                        report["diagnostics"].append({
                            "type": "connection_failure",
                            "details": failure,
                            "ai_analyzed": True,
                            "cause": result.cause,
                            "solution": result.solution,
                            "correct_params": result.correct_params
                        })

                    # 加入失敗緩衝區
                    self.failure_buffer.append(failure)

            # 深度分析：批量學習
            if level == DiagnosticLevel.DEEP and len(self.failure_buffer) >= 3:
                learn_result = self.vision.learn_from_failure(self.failure_buffer)

                if learn_result.success:
                    report["patterns"] = learn_result.patterns_learned
                    report["suggestions"] = learn_result.suggestions

                # 清空緩衝區
                self.failure_buffer = []

            # 截取畫布截圖
            screenshot = self.vision.capture_canvas()
            if screenshot:
                report["screenshots"].append(screenshot)

            report["diagnosed"] = True

        finally:
            self.vision.disconnect()

        return report

    def _extract_connection_failures(self, errors: List[str]) -> List[Dict]:
        """從錯誤訊息中提取連接失敗資訊"""
        failures = []

        for error in errors:
            error_lower = error.lower()

            # 嘗試解析連接相關錯誤
            if any(kw in error_lower for kw in ["connect", "connection", "parameter", "input", "output"]):
                # 嘗試從錯誤訊息中提取組件和參數資訊
                failure = {
                    "error": error,
                    "source_component": "Unknown",
                    "source_param": "Unknown",
                    "target_component": "Unknown",
                    "target_param": "Unknown"
                }

                # 簡單的模式匹配
                if "→" in error or "->" in error:
                    parts = error.replace("→", "->").split("->")
                    if len(parts) >= 2:
                        failure["source_component"] = parts[0].strip().split(".")[0] if "." in parts[0] else parts[0].strip()
                        failure["target_component"] = parts[1].strip().split(".")[0] if "." in parts[1] else parts[1].strip()

                failures.append(failure)

        return failures

    def record_failure(self, failure: Dict):
        """記錄失敗（供後續批量學習）"""
        self.failure_buffer.append(failure)

        # 超出緩衝區時移除最舊的
        if len(self.failure_buffer) > self.max_buffer_size:
            self.failure_buffer = self.failure_buffer[-self.max_buffer_size:]

    def get_failure_count(self) -> int:
        """獲取緩衝區中的失敗數量"""
        return len(self.failure_buffer)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    print("Testing VisionDiagnosticClient...")

    client = VisionDiagnosticClient()

    if client.is_available():
        print("✅ GH_MCP_Vision is available")

        with client:
            # 測試診斷
            result = client.diagnose_connection(
                source_component="Mesh Box",
                source_param="M",
                target_component="Face Normals",
                target_param="M",
                error_message="Connection failed: parameter not found"
            )

            print(f"Diagnosis: {result}")
    else:
        print("❌ GH_MCP_Vision is not available (port 8081)")
        print("   Make sure Grasshopper is running with GH_MCP_Vision component")
