"""
Graph State Definition
======================
定義 LangGraph 流程中的狀態結構
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from operator import add


class GraphState(TypedDict, total=False):
    """
    LangGraph 流程狀態
    
    包含從自然語言描述到 GH Code 生成過程中的所有中間狀態
    """
    
    # ==========================================
    # 使用者輸入
    # ==========================================
    
    # 原始設計意圖描述
    design_intent: str
    
    # 附加約束條件
    constraints: Optional[List[str]]
    
    # 使用者偏好的參數
    user_preferences: Optional[Dict[str, Any]]
    
    # ==========================================
    # 意圖解析結果
    # ==========================================
    
    # 識別出的設計意圖類型
    intent_type: Optional[str]
    
    # 識別出的核心操作
    core_operations: Optional[List[str]]
    
    # 識別出的參數化需求
    parametric_requirements: Optional[List[Dict[str, Any]]]
    
    # 匹配的設計意圖模式
    matched_intent_patterns: Optional[List[str]]
    
    # 意圖解析的置信度
    intent_confidence: Optional[float]
    
    # ==========================================
    # Mermaid 流程圖
    # ==========================================
    
    # 生成的 Mermaid 流程圖代碼
    mermaid_graph: Optional[str]
    
    # Mermaid 圖的結構化表示
    mermaid_structure: Optional[Dict[str, Any]]
    
    # ==========================================
    # GH Code 輸出
    # ==========================================
    
    # 生成的 GH Code (元件和連接定義)
    gh_code: Optional[Dict[str, Any]]
    
    # GH Code 的 XML 表示 (可直接導入 Grasshopper)
    gh_xml: Optional[str]
    
    # 使用的元件列表
    components_used: Optional[List[str]]
    
    # 連接定義
    connections_defined: Optional[List[Dict[str, str]]]
    
    # ==========================================
    # 模式庫參考
    # ==========================================
    
    # 匹配的連接模式
    matched_patterns: Optional[List[str]]
    
    # 建議使用的元件
    suggested_components: Optional[List[str]]
    
    # 可選的替代方案
    alternative_approaches: Optional[List[Dict[str, Any]]]
    
    # ==========================================
    # 評估結果
    # ==========================================
    
    # 總優雅度分數 (0-1)
    elegance_score: Optional[float]
    
    # 各項指標分數
    elegance_breakdown: Optional[Dict[str, float]]
    
    # 發現的問題
    issues: Optional[List[str]]
    
    # 改進建議
    suggestions: Optional[List[str]]
    
    # ==========================================
    # 迭代控制
    # ==========================================
    
    # 當前迭代次數
    iteration_count: int
    
    # 最大迭代次數
    max_iterations: int
    
    # 接受閾值 (優雅度分數達到此值則停止)
    acceptance_threshold: float
    
    # 下一步動作: "refine_intent" | "refine_mermaid" | "refine_gh" | "accept"
    next_action: Optional[str]
    
    # ==========================================
    # 歷史記錄 (使用 Annotated 支援累積)
    # ==========================================
    
    # 評估歷史 (每次迭代的評估結果)
    critique_history: Annotated[List[Dict[str, Any]], add]
    
    # 修改歷史 (每次修改的說明)
    modification_history: Annotated[List[str], add]
    
    # ==========================================
    # 錯誤處理
    # ==========================================
    
    # 錯誤訊息
    error_message: Optional[str]
    
    # 是否發生錯誤
    has_error: bool
    
    # 警告訊息
    warnings: Optional[List[str]]


def create_initial_state(
    design_intent: str,
    constraints: Optional[List[str]] = None,
    max_iterations: int = 5,
    acceptance_threshold: float = 0.8
) -> GraphState:
    """
    創建初始狀態
    
    Args:
        design_intent: 使用者的設計意圖描述
        constraints: 附加約束條件
        max_iterations: 最大迭代次數
        acceptance_threshold: 優雅度接受閾值
        
    Returns:
        初始化的 GraphState
    """
    return GraphState(
        # 使用者輸入
        design_intent=design_intent,
        constraints=constraints or [],
        user_preferences={},
        
        # 初始化控制參數
        iteration_count=0,
        max_iterations=max_iterations,
        acceptance_threshold=acceptance_threshold,
        next_action=None,
        
        # 初始化歷史記錄 (空列表)
        critique_history=[],
        modification_history=[],
        
        # 初始化錯誤狀態
        has_error=False,
        error_message=None,
        warnings=[],
    )


def state_summary(state: GraphState) -> str:
    """
    產生狀態摘要
    
    Args:
        state: 當前狀態
        
    Returns:
        人類可讀的狀態摘要
    """
    lines = [
        "=== GraphState Summary ===",
        f"Design Intent: {state.get('design_intent', 'N/A')[:50]}...",
        f"Iteration: {state.get('iteration_count', 0)} / {state.get('max_iterations', 5)}",
        f"Next Action: {state.get('next_action', 'N/A')}",
        f"Elegance Score: {state.get('elegance_score', 'N/A')}",
    ]
    
    if state.get('intent_type'):
        lines.append(f"Intent Type: {state['intent_type']}")
    
    if state.get('matched_patterns'):
        lines.append(f"Matched Patterns: {', '.join(state['matched_patterns'])}")
    
    if state.get('components_used'):
        lines.append(f"Components Used: {len(state['components_used'])}")
    
    if state.get('issues'):
        lines.append(f"Issues: {len(state['issues'])}")
        for issue in state['issues'][:3]:
            lines.append(f"  - {issue}")
    
    if state.get('has_error'):
        lines.append(f"ERROR: {state.get('error_message', 'Unknown error')}")
    
    return "\n".join(lines)
