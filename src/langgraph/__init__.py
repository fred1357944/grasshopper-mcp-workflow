"""
LangGraph Pipeline Components
=============================
自然語言 → Mermaid → GH Code 的迭代優化流程
"""

from .graph_state import GraphState

# 節點函數（不依賴 langgraph 套件）
from .nodes import (
    parse_intent,
    generate_mermaid,
    generate_gh_code,
    evaluate_elegance,
    # 規則式函數
    _rule_based_intent_parsing,
    _rule_based_mermaid_generation,
    _rule_based_gh_code_generation,
)

# 圖結構（需要 langgraph 套件）
try:
    from .graph import build_graph, run_generation
    GRAPH_AVAILABLE = True
except ImportError:
    build_graph = None
    run_generation = None
    GRAPH_AVAILABLE = False

__all__ = [
    "GraphState",
    "parse_intent",
    "generate_mermaid",
    "generate_gh_code",
    "evaluate_elegance",
    "build_graph",
    "run_generation",
    "GRAPH_AVAILABLE",
    # 規則式函數
    "_rule_based_intent_parsing",
    "_rule_based_mermaid_generation",
    "_rule_based_gh_code_generation",
]
