"""
Compiled Multi-Mode Workflow - 真正的 LangGraph StateGraph 實作

這個模組使用 langgraph 的 StateGraph 來編譯工作流程，
取代之前的 dict 模擬版本。

特性：
- 真正的圖編譯
- 條件路由
- 串流輸出支援
- Checkpoint 支援
- 可視化支援
"""

from typing import Dict, Any, Literal, Optional, Annotated
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from ..state import (
    DesignState,
    create_initial_state,
    IntentType,
    BrainstormPhase,
    ThinkingMode,
    WorkflowStage,
)

# Import node functions
from ..nodes.think_partner import (
    think_partner_node,
    enter_think_partner_mode,
    exit_think_partner_mode,
)
from ..nodes.brainstorm import (
    brainstorm_node,
    enter_brainstorm_mode,
    exit_brainstorm_mode,
)
from ..nodes.meta_agent import (
    meta_agent_node,
    enter_meta_agent_mode,
    exit_meta_agent_mode,
)
from ..nodes.workflow_pipeline import (
    intent_decomposition_node,
    tool_retrieval_node,
    prompt_generation_node,
    config_assembly_node,
    enter_workflow_mode,
)
from ..nodes.human_review import human_decision_node
from ..core.intent_router import classify_intent


# === Node Wrapper Functions ===
# LangGraph 需要 node 函數返回完整 state 或部分更新

def intent_router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """入口節點：分類意圖"""
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    task = f"{topic} {requirements}".strip()

    classification = classify_intent(task, state)

    return {
        "intent_type": classification.intent_type.value,
        "intent_confidence": classification.confidence,
        "intent_keywords": classification.matched_keywords,
    }


def enter_think_partner_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 enter_think_partner_mode"""
    return enter_think_partner_mode(state)


def think_partner_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    包裝 think_partner_node - 簡化版，直接生成洞察
    """
    topic = state.get("topic", "")

    insights = [
        f"關於 {topic}，首先要考慮的是使用場景和目標用戶",
        "參數化設計的核心在於找到可調整的關鍵維度",
        "建議從簡單的幾何基礎開始，逐步增加複雜度",
    ]

    return {
        "thinking_mode": "writing",
        "thinking_insights": insights,
        "thinking_log": [
            {"question": "What is the primary use case?", "reflection": "Need to understand context"},
            {"question": "What parameters matter most?", "reflection": "Size and proportion are key"},
        ],
    }


def exit_think_partner_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 exit_think_partner_mode"""
    return exit_think_partner_mode(state)


def enter_brainstorm_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 enter_brainstorm_mode"""
    return enter_brainstorm_mode(state)


def brainstorm_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    包裝 brainstorm_node - 簡化版，直接完成而不等待人工輸入
    """
    # 直接生成一些想法並完成
    topic = state.get("topic", "")

    ideas = [
        {
            "id": "idea_1",
            "content": f"方案 A: 簡約現代風格的 {topic}",
            "feasibility": 0.8,
            "novelty": 0.6,
            "is_recommended": True,
        },
        {
            "id": "idea_2",
            "content": f"方案 B: 工業風格的 {topic}",
            "feasibility": 0.7,
            "novelty": 0.7,
            "is_recommended": False,
        },
        {
            "id": "idea_3",
            "content": f"方案 C: 參數化幾何風格的 {topic}",
            "feasibility": 0.6,
            "novelty": 0.9,
            "is_recommended": False,
        },
    ]

    return {
        "brainstorm_phase": "complete",
        "brainstorm_ideas": ideas,
        "brainstorm_constraints": ["cost effective", "manufacturable"],
        "brainstorm_success_criteria": ["aesthetically pleasing", "functional"],
    }


def exit_brainstorm_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 exit_brainstorm_mode"""
    return exit_brainstorm_mode(state)


def enter_meta_agent_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 enter_meta_agent_mode"""
    return enter_meta_agent_mode(state)


def meta_agent_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    包裝 meta_agent_node - 簡化版，直接生成工具
    """
    topic = state.get("topic", "")

    tools = [
        {
            "name": "parametric_tool",
            "description": f"A tool for creating {topic}",
            "input_schema": {"width": "number", "height": "number"},
            "output_schema": {"geometry": "object"},
        }
    ]

    return {
        "meta_agent_active": False,
        "generated_tools": tools,
        "agent_configs": [],
    }


def exit_meta_agent_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 exit_meta_agent_mode"""
    return exit_meta_agent_mode(state)


def enter_workflow_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """包裝 enter_workflow_mode"""
    return enter_workflow_mode(state)


def workflow_decompose_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 1: Decompose"""
    return intent_decomposition_node(state)


def workflow_retrieve_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2: Retrieve"""
    return tool_retrieval_node(state)


def workflow_prompt_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 3: Prompt"""
    return prompt_generation_node(state)


def workflow_assemble_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4: Assemble"""
    result = config_assembly_node(state)
    # 標記完成
    result["current_stage"] = WorkflowStage.COMPLETE.value
    return result


def final_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """生成最終輸出"""
    intent_type = state.get("intent_type")
    topic = state.get("topic", "")

    output_parts = [
        f"# Workflow Complete: {topic}",
        f"Mode: {intent_type}",
        "",
    ]

    if intent_type == IntentType.THINK_PARTNER.value:
        insights = state.get("thinking_insights", [])
        output_parts.append("## Think-Partner Insights")
        for insight in insights:
            output_parts.append(f"- {insight}")

    elif intent_type == IntentType.BRAINSTORM.value:
        ideas = state.get("brainstorm_ideas", [])
        output_parts.append("## Brainstorm Ideas")
        for idea in ideas:
            recommended = " (Recommended)" if idea.get("is_recommended") else ""
            output_parts.append(f"- {idea.get('content', '')[:100]}{recommended}")

    elif intent_type == IntentType.META_AGENT.value:
        tools = state.get("generated_tools", [])
        output_parts.append("## Generated Tools")
        for tool in tools:
            output_parts.append(f"- {tool.get('name', 'Unknown')}: {tool.get('description', '')}")

    elif intent_type == IntentType.WORKFLOW.value:
        placement_info = state.get("placement_info")
        if placement_info:
            output_parts.append("## Workflow Output")
            output_parts.append(f"Components: {len(placement_info.get('components', []))}")
            output_parts.append(f"Connections: {len(placement_info.get('connections', []))}")

    final_output = "\n".join(output_parts)

    return {
        "final_proposal": final_output,
        "user_approved": True,
    }


# === Routing Functions ===

def route_by_intent(state: Dict[str, Any]) -> str:
    """
    根據意圖類型路由到對應模式

    重要：LangGraph 條件邊是在節點輸出「合併到 state 之前」執行的。
    因此這裡需要重新從 topic 分類意圖，而不是讀取 state 中的 intent_type。
    """
    # 從 topic 重新分類（因為 state 還沒更新）
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    task = f"{topic} {requirements}".strip()

    classification = classify_intent(task, state)
    intent_type = classification.intent_type.value

    if intent_type == "think_partner":
        return "enter_think_partner"
    elif intent_type == "brainstorm":
        return "enter_brainstorm"
    elif intent_type == "meta_agent":
        return "enter_meta_agent"
    else:
        return "enter_workflow"


def route_think_partner(state: Dict[str, Any]) -> str:
    """Think-Partner 內部路由"""
    mode = state.get("thinking_mode")
    iterations = state.get("_think_iterations", 0)

    # 防止無限迴圈：最多 3 次迭代
    if iterations >= 3:
        return "exit_think_partner"

    if mode == ThinkingMode.WRITING.value or mode == "writing":
        return "exit_think_partner"
    elif state.get("awaiting_confirmation"):
        # 如果沒有啟用人工審核，直接退出
        return "exit_think_partner"
    elif len(state.get("thinking_log", [])) >= 3:
        return "exit_think_partner"
    else:
        return "think_partner_process"


def route_brainstorm(state: Dict[str, Any]) -> str:
    """Brainstorm 內部路由"""
    phase = state.get("brainstorm_phase")
    iterations = state.get("_brainstorm_iterations", 0)

    # 防止無限迴圈：最多 5 次迭代
    if iterations >= 5:
        return "exit_brainstorm"

    if phase == BrainstormPhase.COMPLETE.value or phase == "complete":
        return "exit_brainstorm"
    elif state.get("awaiting_confirmation"):
        # 如果沒有啟用人工審核，直接退出
        return "exit_brainstorm"
    else:
        return "brainstorm_process"


def route_meta_agent(state: Dict[str, Any]) -> str:
    """Meta-Agent 內部路由"""
    iterations = state.get("_meta_iterations", 0)

    # 防止無限迴圈：最多 3 次迭代
    if iterations >= 3:
        return "exit_meta_agent"

    if not state.get("meta_agent_active"):
        return "exit_meta_agent"

    if state.get("awaiting_confirmation"):
        # 如果沒有啟用人工審核，直接退出
        return "exit_meta_agent"

    # 檢查是否有足夠的工具生成
    if len(state.get("generated_tools", [])) >= 1:
        return "exit_meta_agent"

    return "meta_agent_process"


def route_after_human_decision(state: Dict[str, Any]) -> str:
    """人工決策後的路由"""
    intent_type = state.get("intent_type")

    # 清除等待標記
    if intent_type == IntentType.THINK_PARTNER.value:
        return "think_partner_process"
    elif intent_type == IntentType.BRAINSTORM.value:
        return "brainstorm_process"
    elif intent_type == IntentType.META_AGENT.value:
        return "meta_agent_process"
    else:
        return "final_output"


# === Graph Builder ===

def build_multi_mode_graph() -> StateGraph:
    """
    建立多模式工作流程圖

    Returns:
        StateGraph 實例（未編譯）
    """
    # 建立 StateGraph
    # 注意：DesignState 是 TypedDict，LangGraph 支援
    graph = StateGraph(dict)  # 使用 dict 作為 state schema

    # === 加入節點 ===

    # 入口節點
    graph.add_node("intent_router", intent_router_node)

    # Think-Partner 節點
    graph.add_node("enter_think_partner", enter_think_partner_wrapper)
    graph.add_node("think_partner_process", think_partner_wrapper)
    graph.add_node("exit_think_partner", exit_think_partner_wrapper)

    # Brainstorm 節點
    graph.add_node("enter_brainstorm", enter_brainstorm_wrapper)
    graph.add_node("brainstorm_process", brainstorm_wrapper)
    graph.add_node("exit_brainstorm", exit_brainstorm_wrapper)

    # Meta-Agent 節點
    graph.add_node("enter_meta_agent", enter_meta_agent_wrapper)
    graph.add_node("meta_agent_process", meta_agent_wrapper)
    graph.add_node("exit_meta_agent", exit_meta_agent_wrapper)

    # Workflow 節點
    graph.add_node("enter_workflow", enter_workflow_wrapper)
    graph.add_node("workflow_decompose", workflow_decompose_wrapper)
    graph.add_node("workflow_retrieve", workflow_retrieve_wrapper)
    graph.add_node("workflow_prompt", workflow_prompt_wrapper)
    graph.add_node("workflow_assemble", workflow_assemble_wrapper)

    # 共享節點
    graph.add_node("human_decision", human_decision_node)
    graph.add_node("final_output", final_output_node)

    # === 加入邊 ===

    # 入口
    graph.add_edge(START, "intent_router")

    # 意圖路由（條件邊）
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "enter_think_partner": "enter_think_partner",
            "enter_brainstorm": "enter_brainstorm",
            "enter_meta_agent": "enter_meta_agent",
            "enter_workflow": "enter_workflow",
        }
    )

    # Think-Partner 子圖（簡化版：直接走完）
    graph.add_edge("enter_think_partner", "think_partner_process")
    graph.add_edge("think_partner_process", "exit_think_partner")
    graph.add_edge("exit_think_partner", "final_output")

    # Brainstorm 子圖（簡化版：直接走完）
    graph.add_edge("enter_brainstorm", "brainstorm_process")
    graph.add_edge("brainstorm_process", "exit_brainstorm")
    graph.add_edge("exit_brainstorm", "final_output")

    # Meta-Agent 子圖（簡化版：直接走完）
    graph.add_edge("enter_meta_agent", "meta_agent_process")
    graph.add_edge("meta_agent_process", "exit_meta_agent")
    graph.add_edge("exit_meta_agent", "final_output")

    # Workflow 子圖（四階段管線）
    graph.add_edge("enter_workflow", "workflow_decompose")
    graph.add_edge("workflow_decompose", "workflow_retrieve")
    graph.add_edge("workflow_retrieve", "workflow_prompt")
    graph.add_edge("workflow_prompt", "workflow_assemble")
    graph.add_edge("workflow_assemble", "final_output")

    # Human Decision（簡化版不使用，但保留節點以備將來擴展）
    # 直接連到 final_output
    graph.add_edge("human_decision", "final_output")

    # 結束
    graph.add_edge("final_output", END)

    return graph


def compile_workflow(
    checkpointer: Optional[Any] = None,
    interrupt_before: Optional[list] = None,
    interrupt_after: Optional[list] = None,
):
    """
    編譯工作流程

    Args:
        checkpointer: Checkpoint 儲存器（可選）
        interrupt_before: 在這些節點前中斷（人工審核）
        interrupt_after: 在這些節點後中斷

    Returns:
        編譯後的 CompiledGraph
    """
    graph = build_multi_mode_graph()

    # 設定中斷點（人工審核）
    if interrupt_before is None:
        interrupt_before = ["human_decision"]

    compile_kwargs = {}

    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    if interrupt_before:
        compile_kwargs["interrupt_before"] = interrupt_before

    if interrupt_after:
        compile_kwargs["interrupt_after"] = interrupt_after

    return graph.compile(**compile_kwargs)


# === Convenience Functions ===

class CompiledWorkflowRunner:
    """
    編譯後工作流程的執行器

    Usage:
        runner = CompiledWorkflowRunner()

        # 執行
        result = runner.run("design a parametric table")

        # 串流執行
        for event in runner.stream("brainstorm chair ideas"):
            print(event)

        # 帶 checkpoint
        runner_with_memory = CompiledWorkflowRunner(use_memory=True)
        result = runner_with_memory.run("think about chair design", thread_id="session-1")
    """

    def __init__(
        self,
        use_memory: bool = False,
        interrupt_at_human_decision: bool = True
    ):
        """
        初始化執行器

        Args:
            use_memory: 是否使用 MemorySaver
            interrupt_at_human_decision: 是否在 human_decision 節點中斷
        """
        checkpointer = MemorySaver() if use_memory else None
        interrupt_before = ["human_decision"] if interrupt_at_human_decision else None

        self.app = compile_workflow(
            checkpointer=checkpointer,
            interrupt_before=interrupt_before
        )
        self.use_memory = use_memory

    def run(
        self,
        topic: str,
        requirements: str = "",
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行工作流程

        Args:
            topic: 設計主題
            requirements: 需求說明
            thread_id: 對話 ID（使用 memory 時需要）

        Returns:
            最終狀態
        """
        initial_state = create_initial_state(topic)
        initial_state["requirements"] = requirements

        config = {}
        if self.use_memory and thread_id:
            config["configurable"] = {"thread_id": thread_id}

        # 使用 stream 來收集完整狀態
        final_state = dict(initial_state)
        for event in self.app.stream(dict(initial_state), config):
            # 每個 event 是 {node_name: output_dict}
            for node_name, output in event.items():
                if isinstance(output, dict):
                    final_state.update(output)

        return final_state

    def stream(
        self,
        topic: str,
        requirements: str = "",
        thread_id: Optional[str] = None
    ):
        """
        串流執行工作流程

        Args:
            topic: 設計主題
            requirements: 需求說明
            thread_id: 對話 ID

        Yields:
            每個步驟的事件
        """
        initial_state = create_initial_state(topic)
        initial_state["requirements"] = requirements

        config = {}
        if self.use_memory and thread_id:
            config["configurable"] = {"thread_id": thread_id}

        for event in self.app.stream(dict(initial_state), config):
            yield event

    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取指定 thread 的當前狀態（需要 memory）

        Args:
            thread_id: 對話 ID

        Returns:
            當前狀態或 None
        """
        if not self.use_memory:
            return None

        config = {"configurable": {"thread_id": thread_id}}
        return self.app.get_state(config)

    def resume(
        self,
        thread_id: str,
        user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        恢復中斷的工作流程

        Args:
            thread_id: 對話 ID
            user_input: 用戶輸入（更新狀態）

        Returns:
            繼續執行後的狀態
        """
        if not self.use_memory:
            raise ValueError("Memory not enabled")

        config = {"configurable": {"thread_id": thread_id}}

        if user_input:
            # 更新狀態
            self.app.update_state(config, user_input)

        # 繼續執行
        result = self.app.invoke(None, config)
        return result

    def visualize(self) -> str:
        """
        獲取圖的 Mermaid 表示

        Returns:
            Mermaid 格式的圖定義
        """
        try:
            return self.app.get_graph().draw_mermaid()
        except Exception:
            return "Visualization not available"


# === Quick Functions ===

def run_compiled_workflow(
    topic: str,
    requirements: str = ""
) -> Dict[str, Any]:
    """快速執行編譯後的工作流程"""
    runner = CompiledWorkflowRunner(use_memory=False, interrupt_at_human_decision=False)
    return runner.run(topic, requirements)


def stream_compiled_workflow(
    topic: str,
    requirements: str = ""
):
    """快速串流執行編譯後的工作流程"""
    runner = CompiledWorkflowRunner(use_memory=False, interrupt_at_human_decision=False)
    yield from runner.stream(topic, requirements)


def get_workflow_mermaid() -> str:
    """獲取工作流程的 Mermaid 圖"""
    runner = CompiledWorkflowRunner(use_memory=False, interrupt_at_human_decision=False)
    return runner.visualize()
