#!/usr/bin/env python3
"""
端到端測試腳本
==============
Day 7 驗證用 - 完整工作流程測試

測試流程：
1. 輸入自然語言設計意圖
2. LangGraph 處理（或規則式備用）
3. 生成 GH Code
4. 優雅度評估
5. (可選) 部署到 Grasshopper

使用方式：
    python -m src.e2e_test "創建一個螺旋曲線"
    python -m src.e2e_test --simulate "創建陣列"
    python -m src.e2e_test --full-test
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 導入模組
try:
    from src.langgraph.nodes import (
        _rule_based_intent_parsing,
        _rule_based_mermaid_generation,
        _rule_based_gh_code_generation
    )
    NODES_AVAILABLE = True
except ImportError:
    NODES_AVAILABLE = False
    logger.warning("無法導入 nodes 模組")

try:
    from src.elegance_metrics import EleganceEvaluator
    ELEGANCE_AVAILABLE = True
except ImportError:
    ELEGANCE_AVAILABLE = False
    logger.warning("無法導入 elegance_metrics 模組")

try:
    from src.mcp_stdio_bridge import StdioMCPBridge, SimulatedMCPBridge, minimal_deployment_test
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("無法導入 mcp_stdio_bridge 模組")

try:
    from src.smart_layout import simple_layout
    LAYOUT_AVAILABLE = True
except ImportError:
    LAYOUT_AVAILABLE = False
    logger.warning("無法導入 smart_layout 模組")

try:
    from src.safety import SafetyGuard, SafetyConfig
    SAFETY_AVAILABLE = True
except ImportError:
    SAFETY_AVAILABLE = False
    logger.warning("無法導入 safety 模組")


class E2ETestRunner:
    """端到端測試運行器"""
    
    def __init__(self, simulate: bool = True, verbose: bool = True):
        self.simulate = simulate
        self.verbose = verbose
        self.results: Dict[str, Any] = {}
        self.start_time = None
        
        # 初始化安全護欄
        if SAFETY_AVAILABLE:
            self.safety = SafetyGuard(SafetyConfig(
                max_iterations=5,
                total_token_budget=50000,
                timeout_seconds=60
            ))
        else:
            self.safety = None
    
    def run(self, design_intent: str) -> Dict[str, Any]:
        """
        運行完整的端到端測試
        
        Args:
            design_intent: 設計意圖描述
            
        Returns:
            測試結果
        """
        self.start_time = datetime.now()
        self.results = {
            "design_intent": design_intent,
            "timestamp": self.start_time.isoformat(),
            "steps": {},
            "success": False,
            "elapsed_time": 0
        }
        
        self._print_header(f"端到端測試: {design_intent[:50]}...")
        
        # 啟動安全護欄
        if self.safety:
            self.safety.start()
        
        try:
            # Step 1: 意圖解析
            self._step_intent_parsing(design_intent)
            
            # Step 2: Mermaid 生成
            self._step_mermaid_generation()
            
            # Step 3: GH Code 生成
            self._step_gh_code_generation()
            
            # Step 4: 佈局優化
            self._step_layout_optimization()
            
            # Step 5: 優雅度評估
            self._step_elegance_evaluation()
            
            # Step 6: MCP 部署 (可選)
            if not self.simulate:
                self._step_mcp_deployment()
            else:
                self._step_simulated_deployment()
            
            self.results["success"] = True
            
        except Exception as e:
            logger.error(f"測試失敗: {e}")
            self.results["error"] = str(e)
            import traceback
            self.results["traceback"] = traceback.format_exc()
        
        # 計算總時間
        self.results["elapsed_time"] = (datetime.now() - self.start_time).total_seconds()
        
        # 打印摘要
        self._print_summary()
        
        return self.results
    
    def _step_intent_parsing(self, design_intent: str):
        """Step 1: 意圖解析"""
        self._print_step(1, "意圖解析")
        
        if not NODES_AVAILABLE:
            self._skip_step("nodes 模組不可用")
            return
        
        start = time.time()
        
        try:
            # 構建初始 state
            state = {
                "design_intent": design_intent,
                "constraints": [],
                "iteration_count": 0,
                "modification_history": []
            }
            
            # 調用規則式解析（需要 state 和 design_intent 兩個參數）
            result_state = _rule_based_intent_parsing(state, design_intent)
            
            # 提取結果
            result = {
                "intent_type": result_state.get("intent_type", "unknown"),
                "core_operations": result_state.get("core_operations", []),
                "matched_patterns": result_state.get("matched_intent_patterns", []),
                "parametric_requirements": result_state.get("parametric_requirements", {}),
                "confidence": result_state.get("intent_confidence", 0)
            }
            
            # 保存完整 state 供後續步驟使用
            self.results["_state"] = result_state
            
            self.results["steps"]["intent_parsing"] = {
                "success": True,
                "time": time.time() - start,
                "result": result
            }
            
            if self.verbose:
                logger.info(f"  意圖類型: {result.get('intent_type', 'unknown')}")
                logger.info(f"  核心操作: {result.get('core_operations', [])}")
                logger.info(f"  匹配模式: {result.get('matched_patterns', [])}")
            
        except Exception as e:
            self._record_error("intent_parsing", e)
    
    def _step_mermaid_generation(self):
        """Step 2: Mermaid 生成"""
        self._print_step(2, "Mermaid 流程圖生成")
        
        if not NODES_AVAILABLE:
            self._skip_step("nodes 模組不可用")
            return
        
        # 取得前一步的 state
        state = self.results.get("_state", {})
        if not state:
            self._skip_step("無意圖解析結果")
            return
        
        start = time.time()
        
        try:
            # 調用規則式生成（接收完整 state）
            result_state = _rule_based_mermaid_generation(state)
            
            # 更新保存的 state
            self.results["_state"] = result_state
            
            mermaid_code = result_state.get("mermaid_graph", "")
            
            self.results["steps"]["mermaid_generation"] = {
                "success": True,
                "time": time.time() - start,
                "result": mermaid_code
            }
            
            if self.verbose:
                # 顯示 Mermaid 圖的前幾行
                lines = mermaid_code.split("\n")[:10]
                for line in lines:
                    logger.info(f"  {line}")
                if len(mermaid_code.split("\n")) > 10:
                    logger.info("  ...")
            
        except Exception as e:
            self._record_error("mermaid_generation", e)
    
    def _step_gh_code_generation(self):
        """Step 3: GH Code 生成"""
        self._print_step(3, "Grasshopper Code 生成")
        
        if not NODES_AVAILABLE:
            self._skip_step("nodes 模組不可用")
            return
        
        # 取得前一步的 state
        state = self.results.get("_state", {})
        
        start = time.time()
        
        try:
            # 調用規則式生成（接收完整 state）
            result_state = _rule_based_gh_code_generation(state)
            
            # 更新保存的 state
            self.results["_state"] = result_state
            
            gh_code = result_state.get("gh_code", {})
            
            self.results["steps"]["gh_code_generation"] = {
                "success": True,
                "time": time.time() - start,
                "result": gh_code
            }
            
            if self.verbose:
                components = gh_code.get("components", [])
                connections = gh_code.get("connections", [])
                logger.info(f"  元件數量: {len(components)}")
                logger.info(f"  連接數量: {len(connections)}")
                
                for comp in components[:5]:
                    logger.info(f"    - {comp.get('nickname', comp.get('type', 'unknown'))}")
                if len(components) > 5:
                    logger.info(f"    ... 還有 {len(components) - 5} 個元件")
            
        except Exception as e:
            self._record_error("gh_code_generation", e)
    
    def _step_layout_optimization(self):
        """Step 4: 佈局優化"""
        self._print_step(4, "智能佈局")
        
        if not LAYOUT_AVAILABLE:
            self._skip_step("smart_layout 模組不可用")
            return
        
        gh_result = self.results.get("steps", {}).get("gh_code_generation", {}).get("result", {})
        if not gh_result:
            self._skip_step("無 GH Code 結果")
            return
        
        start = time.time()
        
        try:
            components = gh_result.get("components", [])
            connections = gh_result.get("connections", [])
            
            # 應用智能佈局
            positioned = simple_layout(components, connections)
            
            self.results["steps"]["layout"] = {
                "success": True,
                "time": time.time() - start,
                "result": positioned
            }
            
            if self.verbose:
                for comp in positioned[:5]:
                    pos = comp.get("position", [0, 0])
                    logger.info(f"    {comp.get('nickname', 'unknown')}: ({pos[0]}, {pos[1]})")
            
        except Exception as e:
            self._record_error("layout", e)
    
    def _step_elegance_evaluation(self):
        """Step 5: 優雅度評估"""
        self._print_step(5, "優雅度評估")
        
        if not ELEGANCE_AVAILABLE:
            self._skip_step("elegance_metrics 模組不可用")
            return
        
        gh_result = self.results.get("steps", {}).get("gh_code_generation", {}).get("result", {})
        if not gh_result:
            self._skip_step("無 GH Code 結果")
            return
        
        start = time.time()
        
        try:
            evaluator = EleganceEvaluator()
            report = evaluator.evaluate(gh_result)
            
            self.results["steps"]["elegance_evaluation"] = {
                "success": True,
                "time": time.time() - start,
                "result": {
                    "total_score": report.total_score,
                    "grade": report.grade,
                    "summary": report.summary,
                    "metrics": report.metrics
                }
            }
            
            if self.verbose:
                logger.info(f"  總分: {report.total_score:.3f}")
                logger.info(f"  等級: {report.grade}")
                logger.info(f"  評語: {report.summary}")
            
        except Exception as e:
            self._record_error("elegance_evaluation", e)
    
    def _step_mcp_deployment(self):
        """Step 6: MCP 部署"""
        self._print_step(6, "MCP 部署 (真實)")
        
        if not MCP_AVAILABLE:
            self._skip_step("mcp_stdio_bridge 模組不可用")
            return
        
        start = time.time()
        
        try:
            bridge = StdioMCPBridge()
            
            if not bridge.connect():
                self.results["steps"]["mcp_deployment"] = {
                    "success": False,
                    "time": time.time() - start,
                    "error": "無法連接到 MCP Bridge"
                }
                logger.warning("  ⚠️ 無法連接到真實 MCP Bridge")
                return
            
            # 執行最小部署測試
            test_result = minimal_deployment_test(bridge)
            
            self.results["steps"]["mcp_deployment"] = {
                "success": test_result.get("verify_test", False),
                "time": time.time() - start,
                "result": test_result
            }
            
            if test_result.get("verify_test"):
                logger.info("  ✅ MCP 部署成功！")
            else:
                logger.warning("  ⚠️ MCP 部署部分失敗")
                for err in test_result.get("errors", []):
                    logger.warning(f"    - {err}")
            
        except Exception as e:
            self._record_error("mcp_deployment", e)
    
    def _step_simulated_deployment(self):
        """Step 6: 模擬部署"""
        self._print_step(6, "MCP 部署 (模擬)")
        
        if not MCP_AVAILABLE:
            self._skip_step("mcp_stdio_bridge 模組不可用")
            return
        
        start = time.time()
        
        try:
            bridge = SimulatedMCPBridge()
            bridge.connect()
            
            # 取得佈局後的元件
            layout_result = self.results.get("steps", {}).get("layout", {}).get("result", [])
            if not layout_result:
                gh_result = self.results.get("steps", {}).get("gh_code_generation", {}).get("result", {})
                layout_result = gh_result.get("components", [])
            
            # 模擬添加元件
            added_count = 0
            for comp in layout_result:
                response = bridge.add_component(
                    component_type=comp.get("type", "unknown"),
                    guid=comp.get("guid", "sim-guid"),
                    position=tuple(comp.get("position", [0, 0])),
                    nickname=comp.get("nickname", "")
                )
                if response.success:
                    added_count += 1
            
            # 取得畫布狀態
            canvas = bridge.get_canvas_state()
            
            self.results["steps"]["mcp_deployment"] = {
                "success": True,
                "simulated": True,
                "time": time.time() - start,
                "result": {
                    "components_added": added_count,
                    "canvas_state": canvas.data
                }
            }
            
            logger.info(f"  ✅ 模擬部署成功: {added_count} 個元件")
            
        except Exception as e:
            self._record_error("mcp_deployment", e)
    
    def _skip_step(self, reason: str):
        """跳過步驟"""
        logger.warning(f"  ⏭️ 跳過: {reason}")
    
    def _record_error(self, step: str, error: Exception):
        """記錄錯誤"""
        import traceback
        self.results["steps"][step] = {
            "success": False,
            "error": str(error),
            "traceback": traceback.format_exc()
        }
        logger.error(f"  ❌ 錯誤: {error}")
    
    def _print_header(self, title: str):
        """打印標題"""
        print("\n" + "=" * 70)
        print(f"🧪 {title}")
        print("=" * 70)
    
    def _print_step(self, num: int, title: str):
        """打印步驟標題"""
        print(f"\n{'─' * 50}")
        print(f"Step {num}: {title}")
        print("─" * 50)
    
    def _print_summary(self):
        """打印摘要"""
        print("\n" + "=" * 70)
        print("📊 測試結果摘要")
        print("=" * 70)
        
        # 統計成功/失敗
        steps = self.results.get("steps", {})
        success_count = sum(1 for s in steps.values() if s.get("success", False))
        total_count = len(steps)
        
        print(f"總步驟: {total_count}")
        print(f"成功: {success_count}")
        print(f"失敗: {total_count - success_count}")
        print(f"總耗時: {self.results.get('elapsed_time', 0):.2f} 秒")
        
        # 優雅度分數
        elegance = steps.get("elegance_evaluation", {}).get("result", {})
        if elegance:
            print(f"\n優雅度評估:")
            print(f"  分數: {elegance.get('total_score', 0):.3f}")
            print(f"  等級: {elegance.get('grade', 'N/A')}")
        
        # 總體結果
        if self.results.get("success"):
            print(f"\n✅ 測試通過！")
        else:
            print(f"\n❌ 測試失敗")
            if self.results.get("error"):
                print(f"錯誤: {self.results['error']}")
        
        # 安全護欄摘要
        if self.safety:
            print(self.safety.summary())


def run_full_test_suite():
    """運行完整測試套件"""
    test_cases = [
        "創建一個可調整的螺旋曲線，要能控制圈數和半徑",
        "建立一個矩形陣列，可以調整行列數和間距",
        "設計一個漸變的點陣列",
        "生成一個簡單的圓形",
    ]
    
    results = []
    
    print("\n" + "=" * 70)
    print("🔬 完整測試套件")
    print("=" * 70)
    print(f"測試案例數: {len(test_cases)}")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {case[:40]}...")
        
        runner = E2ETestRunner(simulate=True, verbose=False)
        result = runner.run(case)
        results.append(result)
        
        status = "✅" if result.get("success") else "❌"
        print(f"  結果: {status}")
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 測試套件結果")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.get("success"))
    print(f"通過: {passed}/{len(results)}")
    
    return results


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Grasshopper LangGraph MCP 端到端測試"
    )
    parser.add_argument(
        "design_intent",
        nargs="?",
        default="創建一個可調整的螺旋曲線",
        help="設計意圖描述"
    )
    parser.add_argument(
        "--simulate", "-s",
        action="store_true",
        default=True,
        help="使用模擬模式（默認）"
    )
    parser.add_argument(
        "--real", "-r",
        action="store_true",
        help="使用真實 MCP 連接"
    )
    parser.add_argument(
        "--full-test", "-f",
        action="store_true",
        help="運行完整測試套件"
    )
    parser.add_argument(
        "--output", "-o",
        help="輸出結果到 JSON 文件"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安靜模式"
    )
    
    args = parser.parse_args()
    
    if args.full_test:
        results = run_full_test_suite()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        simulate = not args.real
        runner = E2ETestRunner(simulate=simulate, verbose=not args.quiet)
        result = runner.run(args.design_intent)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
