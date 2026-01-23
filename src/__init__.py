"""
Grasshopper LangGraph MCP - 整合版
===================================
結合專家的 LangGraph 流程 + 本專案的 GH_MCP Client

核心架構：
    [使用者] -> [Intent Parser] -> [Mermaid Generator] -> [GH Code Generator]
                      ^                                           |
                      |                                           v
                      +-------- [Elegance Evaluator] <------------+
                                        |
                                        v
                            [MCP Adapter] -> [GH_MCP Client] -> [Grasshopper]

主要模組：
    - langgraph/: LangGraph 流程定義 (from 專家)
    - elegance_metrics: 優雅度評估 (from 專家)
    - smart_layout: 智能佈局 (from 專家)
    - safety: 安全護欄 (from 專家)
    - mcp_adapter: 整合層 (本專案新增)
    - grasshopper_mcp/client_optimized: GH_MCP 客戶端 (本專案)
"""

__version__ = "0.2.0"

# ============================================================
# Models (always available)
# ============================================================
try:
    from .models import (
        GHDocument, GHComponent, GHConnection, GHGroup,
        Parameter, DataType, ComponentCategory,
        ComponentVocabulary, ConnectionPattern, IntentPattern,
        EleganceScore
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# ============================================================
# Parser (always available)
# ============================================================
try:
    from .ghx_parser import GHXParser, parse_ghx, parse_ghx_string
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    GHXParser = None
    parse_ghx = None
    parse_ghx_string = None

# ============================================================
# Pattern Extraction
# ============================================================
try:
    from .pattern_extractor import PatternExtractor, extract_patterns_from_file
    PATTERN_AVAILABLE = True
except ImportError:
    PATTERN_AVAILABLE = False
    PatternExtractor = None
    extract_patterns_from_file = None

# ============================================================
# Elegance Evaluation
# ============================================================
try:
    from .elegance_metrics import (
        EleganceEvaluator, EleganceReport,
        evaluate_gh_code, quick_score
    )
    ELEGANCE_AVAILABLE = True
except ImportError:
    ELEGANCE_AVAILABLE = False
    EleganceEvaluator = None
    EleganceReport = None
    evaluate_gh_code = None
    quick_score = None

# ============================================================
# Smart Layout
# ============================================================
try:
    from .smart_layout import (
        SmartLayoutEngine, LayoutConfig, ComponentLayer
    )
    LAYOUT_AVAILABLE = True
except ImportError:
    LAYOUT_AVAILABLE = False
    SmartLayoutEngine = None
    LayoutConfig = None
    ComponentLayer = None

# ============================================================
# Safety Guard
# ============================================================
try:
    from .safety import SafetyGuard, SafetyConfig
    SAFETY_AVAILABLE = True
except ImportError:
    SAFETY_AVAILABLE = False
    SafetyGuard = None
    SafetyConfig = None

# ============================================================
# MCP Adapter (整合層)
# ============================================================
try:
    from .mcp_adapter import MCPAdapter, DeploymentResult, deploy_gh_code
    ADAPTER_AVAILABLE = True
except ImportError:
    ADAPTER_AVAILABLE = False
    MCPAdapter = None
    DeploymentResult = None
    deploy_gh_code = None

# ============================================================
# LangGraph Pipeline (requires langgraph package)
# ============================================================
try:
    from .langgraph import (
        GraphState,
        build_graph, run_generation,
        parse_intent, generate_mermaid, generate_gh_code, evaluate_elegance
    )
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    GraphState = None
    build_graph = None
    run_generation = None
    parse_intent = None
    generate_mermaid = None
    generate_gh_code = None
    evaluate_elegance = None

# ============================================================
# GH_MCP Client (本專案核心)
# ============================================================
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from grasshopper_mcp.client_optimized import (
        GH_MCP_ClientOptimized,
        create_client,
        quick_test,
        PARAM_ALIASES
    )
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    GH_MCP_ClientOptimized = None
    create_client = None
    quick_test = None
    PARAM_ALIASES = None

__all__ = [
    # Version & Availability Flags
    "__version__",
    "LANGGRAPH_AVAILABLE",
    "ELEGANCE_AVAILABLE",
    "LAYOUT_AVAILABLE",
    "SAFETY_AVAILABLE",
    "ADAPTER_AVAILABLE",
    "CLIENT_AVAILABLE",

    # LangGraph (optional)
    "GraphState", "build_graph", "run_generation",
    "parse_intent", "generate_mermaid", "generate_gh_code", "evaluate_elegance",

    # Elegance Evaluation
    "EleganceEvaluator", "EleganceReport",
    "evaluate_gh_code", "quick_score",

    # Smart Layout
    "SmartLayoutEngine", "LayoutConfig", "ComponentLayer",

    # Safety
    "SafetyGuard", "SafetyConfig",

    # MCP Adapter (整合層)
    "MCPAdapter", "DeploymentResult", "deploy_gh_code",

    # GH_MCP Client
    "GH_MCP_ClientOptimized", "create_client", "quick_test", "PARAM_ALIASES",
]


def check_availability():
    """檢查各模組可用性"""
    print("=" * 50)
    print("Grasshopper LangGraph MCP - 模組狀態")
    print("=" * 50)
    print(f"LangGraph Pipeline: {'✓' if LANGGRAPH_AVAILABLE else '✗'}")
    print(f"Elegance Metrics:   {'✓' if ELEGANCE_AVAILABLE else '✗'}")
    print(f"Smart Layout:       {'✓' if LAYOUT_AVAILABLE else '✗'}")
    print(f"Safety Guard:       {'✓' if SAFETY_AVAILABLE else '✗'}")
    print(f"MCP Adapter:        {'✓' if ADAPTER_AVAILABLE else '✗'}")
    print(f"GH_MCP Client:      {'✓' if CLIENT_AVAILABLE else '✗'}")
    print("=" * 50)


if __name__ == "__main__":
    check_availability()
