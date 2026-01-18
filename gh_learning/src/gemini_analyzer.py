#!/usr/bin/env python3
"""
Gemini Analyzer - 使用 Gemini CLI 進行深度分析

功能:
1. 分析組件使用模式
2. 發現隱藏的設計模式
3. 生成驗證問題
4. 提供知識更新建議
"""

import subprocess
import json
from typing import Dict, List, Any, Optional


class GeminiAnalyzer:
    """Gemini CLI 分析器"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self.last_error = None

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """調用 Gemini CLI"""
        try:
            result = subprocess.run(
                ["gemini", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                self.last_error = result.stderr
                return None

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            self.last_error = f"Gemini timeout after {self.timeout}s"
            return None
        except FileNotFoundError:
            self.last_error = "Gemini CLI not found. Install with: npm install -g @google/gemini-cli"
            return None
        except Exception as e:
            self.last_error = str(e)
            return None

    def analyze_patterns(self, knowledge_report: str) -> Dict[str, Any]:
        """分析組件使用模式"""
        prompt = f"""分析以下 Grasshopper 組件統計報告，找出:

1. 隱藏的設計模式（常見的組件組合）
2. 參數命名規則（哪些參數名最可靠）
3. 連線最佳實踐
4. 需要特別注意的組件（如有 OLD 版本）

報告內容:
{knowledge_report[:8000]}

請用 JSON 格式回覆，包含:
- patterns: 設計模式列表
- naming_rules: 參數命名規則
- best_practices: 最佳實踐
- warnings: 警告事項"""

        response = self._call_gemini(prompt)

        if not response:
            return {"error": self.last_error}

        # 嘗試解析 JSON
        try:
            # 找到 JSON 部分
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_response": response}

    def generate_verification_questions(
        self,
        component_name: str,
        uncertain_params: List[Dict]
    ) -> List[str]:
        """生成驗證問題"""
        params_desc = "\n".join([
            f"- {p['nickname']}: 可能是 {p['candidates']}"
            for p in uncertain_params
        ])

        prompt = f"""針對 Grasshopper 組件 "{component_name}"，以下參數有不確定性:

{params_desc}

請生成 3-5 個驗證問題，讓用戶可以在 Grasshopper 中快速測試確認。
問題要具體、可操作。用 JSON 格式回覆:
{{"questions": ["問題1", "問題2", ...]}}"""

        response = self._call_gemini(prompt)

        if not response:
            return [f"請在 Grasshopper 中查看 {component_name} 的參數面板確認參數名稱"]

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                return data.get('questions', [])
        except:
            pass

        return [response[:500]]

    def suggest_knowledge_update(
        self,
        current_knowledge: Dict,
        new_findings: Dict
    ) -> Dict[str, Any]:
        """建議知識庫更新"""
        prompt = f"""比較現有知識庫和新發現，提供更新建議:

現有知識:
{json.dumps(current_knowledge, indent=2, ensure_ascii=False)[:4000]}

新發現:
{json.dumps(new_findings, indent=2, ensure_ascii=False)[:4000]}

請用 JSON 格式回覆:
- add: 需要新增的項目
- update: 需要更新的項目
- verify: 需要人工驗證的項目
- remove: 可能過時的項目"""

        response = self._call_gemini(prompt)

        if not response:
            return {"error": self.last_error}

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass

        return {"raw_response": response}

    def explain_component(self, component_name: str) -> str:
        """解釋組件用途和參數"""
        prompt = f"""解釋 Grasshopper 組件 "{component_name}":

1. 這個組件的主要用途是什麼？
2. 輸入參數的精確名稱和用途？
3. 輸出參數的精確名稱和用途？
4. 常見的連線組合？
5. 需要注意的陷阱？

用中文回答，格式清晰。"""

        response = self._call_gemini(prompt)
        return response or f"無法獲取 {component_name} 的資訊"

    def analyze_connection_failure(
        self,
        source_comp: str,
        target_comp: str,
        error_msg: str
    ) -> Dict[str, Any]:
        """分析連線失敗原因"""
        prompt = f"""Grasshopper MCP 連線失敗:

來源: {source_comp}
目標: {target_comp}
錯誤: {error_msg}

請分析:
1. 可能的原因
2. 正確的參數名稱應該是什麼
3. 修復建議

用 JSON 格式回覆:
{{"cause": "原因", "correct_params": {{"source": "xxx", "target": "yyy"}}, "solution": "建議"}}"""

        response = self._call_gemini(prompt)

        if not response:
            return {"error": self.last_error}

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass

        return {"raw_response": response}


# CLI 介面
if __name__ == "__main__":
    import sys

    analyzer = GeminiAnalyzer()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python gemini_analyzer.py explain <component_name>")
        print("  python gemini_analyzer.py analyze <knowledge_report.json>")
        print("\nExamples:")
        print("  python gemini_analyzer.py explain 'Orient'")
        print("  python gemini_analyzer.py analyze knowledge_report.json")
        sys.exit(1)

    command = sys.argv[1]

    if command == "explain" and len(sys.argv) > 2:
        component = sys.argv[2]
        print(f"\n=== Analyzing {component} ===\n")
        result = analyzer.explain_component(component)
        print(result)

    elif command == "analyze" and len(sys.argv) > 2:
        report_path = sys.argv[2]
        with open(report_path, 'r', encoding='utf-8') as f:
            report = f.read()

        print("\n=== Pattern Analysis ===\n")
        result = analyzer.analyze_patterns(report)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {command}")
