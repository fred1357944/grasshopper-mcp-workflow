"""
LangGraph Graph Definition
==========================
定義完整的 LangGraph 流程圖結構
"""

from typing import Dict, Any, Callable, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .graph_state import GraphState, create_initial_state, state_summary
from .nodes import (
    parse_intent,
    generate_mermaid,
    generate_gh_code,
    evaluate_elegance,
    error_handler
)


def should_continue(state: GraphState) -> str:
    """
    條件邊界函數：決定下一步動作
    
    Returns:
        下一個節點的名稱
    """
    next_action = state.get("next_action", "accept")
    
    # 檢查錯誤狀態
    if state.get("has_error", False):
        return "end"
    
    # 根據評估結果決定下一步
    if next_action == "accept":
        return "end"
    elif next_action == "refine_intent":
        return "parse_intent"
    elif next_action == "refine_mermaid":
        return "generate_mermaid"
    elif next_action == "refine_gh":
        return "generate_gh_code"
    else:
        return "end"


def build_graph(
    with_checkpointing: bool = False,
    custom_nodes: Optional[Dict[str, Callable]] = None
) -> StateGraph:
    """
    建構 LangGraph 流程圖
    
    Args:
        with_checkpointing: 是否啟用檢查點（支援暫停/恢復）
        custom_nodes: 自定義節點函數覆蓋
        
    Returns:
        編譯後的 StateGraph
    """
    # 初始化圖
    workflow = StateGraph(GraphState)
    
    # 取得節點函數（支援自定義覆蓋）
    nodes = {
        "parse_intent": parse_intent,
        "generate_mermaid": generate_mermaid,
        "generate_gh_code": generate_gh_code,
        "evaluate_elegance": evaluate_elegance,
        "error_handler": error_handler,
    }
    
    if custom_nodes:
        nodes.update(custom_nodes)
    
    # 添加節點
    workflow.add_node("parse_intent", nodes["parse_intent"])
    workflow.add_node("generate_mermaid", nodes["generate_mermaid"])
    workflow.add_node("generate_gh_code", nodes["generate_gh_code"])
    workflow.add_node("evaluate_elegance", nodes["evaluate_elegance"])
    workflow.add_node("error_handler", nodes["error_handler"])
    
    # 設定入口點
    workflow.set_entry_point("parse_intent")
    
    # 添加固定邊界（線性流程部分）
    workflow.add_edge("parse_intent", "generate_mermaid")
    workflow.add_edge("generate_mermaid", "generate_gh_code")
    workflow.add_edge("generate_gh_code", "evaluate_elegance")
    
    # 添加條件邊界（迴圈核心）
    workflow.add_conditional_edges(
        "evaluate_elegance",
        should_continue,
        {
            "end": END,
            "parse_intent": "parse_intent",
            "generate_mermaid": "generate_mermaid",
            "generate_gh_code": "generate_gh_code",
        }
    )
    
    # 錯誤處理邊界
    workflow.add_edge("error_handler", END)
    
    # 編譯圖
    if with_checkpointing:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    else:
        return workflow.compile()


def run_generation(
    design_intent: str,
    constraints: Optional[list] = None,
    max_iterations: int = 5,
    acceptance_threshold: float = 0.8,
    verbose: bool = True,
    stream: bool = False
) -> Dict[str, Any]:
    """
    執行完整的生成流程
    
    Args:
        design_intent: 設計意圖描述
        constraints: 附加約束條件
        max_iterations: 最大迭代次數
        acceptance_threshold: 優雅度接受閾值
        verbose: 是否輸出過程資訊
        stream: 是否使用串流模式
        
    Returns:
        最終狀態字典
    """
    # 建立初始狀態
    initial_state = create_initial_state(
        design_intent=design_intent,
        constraints=constraints,
        max_iterations=max_iterations,
        acceptance_threshold=acceptance_threshold
    )
    
    # 建立並編譯圖
    graph = build_graph()
    
    if verbose:
        print("=" * 60)
        print("🚀 Starting Grasshopper Code Generation")
        print("=" * 60)
        print(f"Design Intent: {design_intent}")
        print(f"Max Iterations: {max_iterations}")
        print(f"Acceptance Threshold: {acceptance_threshold}")
        print("=" * 60)
    
    if stream:
        # 串流模式 - 逐步輸出
        final_state = None
        for event in graph.stream(initial_state):
            for node_name, node_state in event.items():
                if verbose:
                    print(f"\n📍 Node: {node_name}")
                    if node_state.get("elegance_score"):
                        print(f"   Score: {node_state['elegance_score']:.3f}")
                    if node_state.get("next_action"):
                        print(f"   Next: {node_state['next_action']}")
                final_state = node_state
        result = final_state
    else:
        # 批次模式 - 一次完成
        result = graph.invoke(initial_state)
    
    if verbose:
        print("\n" + "=" * 60)
        print("✅ Generation Complete")
        print("=" * 60)
        print(state_summary(result))
    
    return result


def run_generation_async(
    design_intent: str,
    constraints: Optional[list] = None,
    **kwargs
):
    """
    非同步執行生成流程（用於與 MCP 整合）
    """
    import asyncio
    
    async def _run():
        return run_generation(design_intent, constraints, **kwargs)
    
    return asyncio.run(_run())


# ============================================================
# 視覺化工具
# ============================================================

def visualize_graph():
    """
    產生流程圖的 Mermaid 視覺化
    
    Returns:
        Mermaid 格式的流程圖代碼
    """
    return """
```mermaid
graph TD
    START((開始)) --> PI[parse_intent<br/>意圖解析]
    PI --> GM[generate_mermaid<br/>生成流程圖]
    GM --> GC[generate_gh_code<br/>生成 GH Code]
    GC --> EE[evaluate_elegance<br/>優雅度評估]
    
    EE -->|score >= threshold| ACCEPT((接受))
    EE -->|refine_intent| PI
    EE -->|refine_mermaid| GM
    EE -->|refine_gh| GC
    EE -->|max_iterations| ACCEPT
    
    style PI fill:#e1f5fe
    style GM fill:#fff3e0
    style GC fill:#e8f5e9
    style EE fill:#fce4ec
    style ACCEPT fill:#c8e6c9
```
"""


def export_graph_png(output_path: str = "graph.png"):
    """
    匯出流程圖為 PNG（需要 graphviz）
    """
    try:
        graph = build_graph()
        # LangGraph 提供的視覺化功能
        png_data = graph.get_graph().draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(png_data)
        return output_path
    except Exception as e:
        print(f"無法匯出 PNG: {e}")
        print("請確保安裝了 graphviz 和 pygraphviz")
        return None


# ============================================================
# CLI 測試入口
# ============================================================

if __name__ == "__main__":
    # 測試範例
    test_intents = [
        "創建一個可調整的螺旋樓梯，要能控制圈數、半徑和高度",
        "沿著曲線均勻分布方塊，數量和間距可調",
        "生成一個參數化的穿孔表皮",
    ]
    
    print("\n🧪 Testing LangGraph Pipeline\n")
    
    result = run_generation(
        design_intent=test_intents[0],
        max_iterations=3,
        acceptance_threshold=0.7,
        verbose=True,
        stream=True
    )
    
    print("\n📊 Final GH Code:")
    if result.get("gh_code"):
        import json
        print(json.dumps(result["gh_code"], indent=2, ensure_ascii=False))
