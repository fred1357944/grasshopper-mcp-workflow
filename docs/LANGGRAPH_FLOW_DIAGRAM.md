# LangGraph 工作流程圖

> 目前狀態：**模擬執行模式**（使用 dict 定義圖，Python 函數模擬執行）
> 尚未整合真正的 `langgraph.graph.StateGraph` 編譯版本

---

## 1. 整體架構總覽

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Multi-Mode Workflow                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────────────┐                                                       │
│    │     START       │                                                       │
│    └────────┬────────┘                                                       │
│             │                                                                │
│             ▼                                                                │
│    ┌─────────────────┐     意圖分類                                           │
│    │  Intent Router  │────────────────────────────────────────────┐          │
│    │    (入口節點)    │                                            │          │
│    └────────┬────────┘                                            │          │
│             │                                                      │          │
│             ▼                                                      │          │
│    ┌─────────────────┐                                            │          │
│    │   Mode Router   │     根據 intent_type 分發                   │          │
│    └────────┬────────┘                                            │          │
│             │                                                      │          │
│    ┌────────┴────────┬─────────────────┬────────────────┐         │          │
│    │                 │                 │                │         │          │
│    ▼                 ▼                 ▼                ▼         │          │
│ ┌──────┐        ┌──────┐         ┌──────┐         ┌──────┐        │          │
│ │THINK │        │BRAIN-│         │ META │         │WORK- │        │          │
│ │PARTNER│       │STORM │         │AGENT │         │FLOW  │        │          │
│ └───┬──┘        └───┬──┘         └───┬──┘         └───┬──┘        │          │
│     │               │                │                │           │          │
│     └───────────────┴────────────────┴────────────────┘           │          │
│                          │                                        │          │
│                          ▼                                        │          │
│                 ┌─────────────────┐     共享節點                    │          │
│                 │  Human Decision │◄──────────────────────────────┘          │
│                 │   (可選審核)    │                                           │
│                 └────────┬────────┘                                          │
│                          │                                                   │
│                          ▼                                                   │
│                 ┌─────────────────┐                                          │
│                 │  Final Output   │                                          │
│                 └────────┬────────┘                                          │
│                          │                                                   │
│                          ▼                                                   │
│                 ┌─────────────────┐                                          │
│                 │      END        │                                          │
│                 └─────────────────┘                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 四種模式子圖詳解

### 2.1 Think-Partner 模式（蘇格拉底式探索）

```
┌─────────────────────────────────────────────────────────────┐
│                    Think-Partner Subgraph                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌───────────────────┐                                    │
│    │ enter_think_partner│  初始化 thinking_mode="thinking"  │
│    └─────────┬─────────┘                                    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────┐                                    │
│    │think_partner_process│  生成問題、探索假設              │
│    │                    │  ├─ 提出蘇格拉底式問題            │
│    │                    │  ├─ 記錄思考日誌                  │
│    │                    │  └─ 等待用戶回應                  │
│    └─────────┬─────────┘                                    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────┐                                    │
│    │   用戶回應？       │                                    │
│    └────┬────────┬─────┘                                    │
│         │        │                                          │
│    繼續探索   切換到寫作模式                                   │
│         │        │                                          │
│         ▼        ▼                                          │
│    ┌─────┐  ┌──────────────────┐                            │
│    │Loop │  │ thinking_mode=   │                            │
│    │     │  │    "writing"     │                            │
│    └─────┘  └────────┬─────────┘                            │
│                      │                                      │
│                      ▼                                      │
│             ┌───────────────────┐                           │
│             │exit_think_partner │  輸出 thinking_insights   │
│             └───────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

關鍵狀態欄位：
- thinking_mode: "thinking" | "writing"
- thinking_log: List[ThinkingEntry]    # 問題+反思+洞察
- thinking_insights: List[str]          # 最終洞察
```

---

### 2.2 Brainstorm 模式（三階段腦力激盪）

```
┌─────────────────────────────────────────────────────────────┐
│                    Brainstorm Subgraph                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌───────────────────┐                                    │
│    │  enter_brainstorm │  初始化 phase="understanding"      │
│    └─────────┬─────────┘                                    │
│              │                                              │
│              ▼                                              │
│    ┌─────────────────────────────────────────┐              │
│    │         Phase 1: Understanding          │              │
│    │  ├─ 釐清問題空間                         │              │
│    │  ├─ 收集約束條件 (constraints)           │              │
│    │  └─ 定義成功標準 (success_criteria)      │              │
│    └─────────┬───────────────────────────────┘              │
│              │ awaiting_confirmation → human_decision       │
│              ▼                                              │
│    ┌─────────────────────────────────────────┐              │
│    │         Phase 2: Exploring              │              │
│    │  ├─ 發散式創意生成                       │              │
│    │  ├─ 不批判、鼓勵野點子                   │              │
│    │  └─ 建立 brainstorm_ideas 列表           │              │
│    └─────────┬───────────────────────────────┘              │
│              │                                              │
│              ▼                                              │
│    ┌─────────────────────────────────────────┐              │
│    │         Phase 3: Presenting             │              │
│    │  ├─ 評估每個想法 (feasibility, novelty) │              │
│    │  ├─ 聚焦收斂                             │              │
│    │  └─ 標記 is_recommended                  │              │
│    └─────────┬───────────────────────────────┘              │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────┐                                    │
│    │  exit_brainstorm  │  phase="complete"                  │
│    └───────────────────┘                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

關鍵狀態欄位：
- brainstorm_phase: "understanding" | "exploring" | "presenting" | "complete"
- brainstorm_ideas: List[BrainstormIdea]
- brainstorm_constraints: List[str]
- brainstorm_success_criteria: List[str]
```

---

### 2.3 Meta-Agent 模式（動態工具創建）

```
┌─────────────────────────────────────────────────────────────┐
│                    Meta-Agent Subgraph                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌───────────────────┐                                    │
│    │ enter_meta_agent  │  meta_agent_active=True            │
│    └─────────┬─────────┘                                    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────────────────────────────────────┐    │
│    │                meta_agent_process                  │    │
│    │                                                    │    │
│    │    ┌──────────────┐                               │    │
│    │    │ search_tool  │ 搜尋現有工具/Joseki           │    │
│    │    └──────┬───────┘                               │    │
│    │           │                                        │    │
│    │           ▼                                        │    │
│    │    ┌──────────────┐                               │    │
│    │    │ create_tool  │ 動態生成新工具                 │    │
│    │    │ ├─ 定義 input_schema                         │    │
│    │    │ ├─ 定義 output_schema                        │    │
│    │    │ └─ 生成 implementation                       │    │
│    │    └──────┬───────┘                               │    │
│    │           │                                        │    │
│    │           ▼                                        │    │
│    │    ┌──────────────┐                               │    │
│    │    │   ask_user   │ 詢問用戶確認/補充資訊         │    │
│    │    └──────┬───────┘                               │    │
│    │           │                                        │    │
│    │           ▼                                        │    │
│    │    ┌──────────────┐                               │    │
│    │    │create_agent_ │ 生成 Agent 配置               │    │
│    │    │    config    │                               │    │
│    │    └──────────────┘                               │    │
│    │                                                    │    │
│    └───────────────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────┐                                    │
│    │ exit_meta_agent   │  meta_agent_active=False           │
│    └───────────────────┘                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

關鍵狀態欄位：
- meta_agent_active: bool
- meta_agent_operation: "search_tool" | "create_tool" | "ask_user" | "create_agent_config"
- generated_tools: List[GeneratedTool]
- agent_configs: List[AgentConfig]
```

---

### 2.4 Workflow 模式（確定性四階段管線）

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Pipeline Subgraph               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌───────────────────┐                                    │
│    │  enter_workflow   │  current_stage="decomposition"     │
│    └─────────┬─────────┘                                    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────────────────────────────────────┐    │
│    │     Stage 1: Intent Decomposition (意圖分解)      │    │
│    │  ├─ 解析用戶意圖                                   │    │
│    │  ├─ 拆解為 subtasks                                │    │
│    │  └─ 識別依賴關係                                   │    │
│    │                                                    │    │
│    │  輸出: workflow_subtasks, subtasks                 │    │
│    └─────────┬─────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────────────────────────────────────┐    │
│    │     Stage 2: Tool Retrieval (工具檢索)            │    │
│    │  ├─ 搜尋 Joseki 模式庫                             │    │
│    │  ├─ 匹配相似組件                                   │    │
│    │  └─ 檢索連接模式                                   │    │
│    │                                                    │    │
│    │  輸出: retrieved_tools, joseki_patterns            │    │
│    └─────────┬─────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────────────────────────────────────┐    │
│    │     Stage 3: Prompt Generation (提示生成)         │    │
│    │  ├─ 為每個 subtask 生成執行提示                    │    │
│    │  ├─ 填入工具參數                                   │    │
│    │  └─ 生成執行計劃                                   │    │
│    │                                                    │    │
│    │  輸出: execution_prompts, execution_plan           │    │
│    └─────────┬─────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────────────────────────────────────┐    │
│    │     Stage 4: Config Assembly (配置組裝)           │    │
│    │  ├─ 組裝 placement_info.json                       │    │
│    │  ├─ 解析組件 GUID                                  │    │
│    │  └─ 建立連接關係                                   │    │
│    │                                                    │    │
│    │  輸出: placement_info, component_id_map, final_output │
│    └─────────┬─────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│    ┌───────────────────┐                                    │
│    │  workflow_exit    │  current_stage="complete"          │
│    └───────────────────┘                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

關鍵狀態欄位：
- current_stage: "decomposition" | "tool_retrieval" | "prompt_generation" | "config_assembly" | "complete"
- subtasks: List[SubTask]
- retrieved_tools: List[Dict]
- execution_prompts: List[Dict]
- placement_info: Optional[Dict]
- component_id_map: Dict[str, str]
```

---

## 3. 意圖路由邏輯

```python
# 關鍵詞觸發規則
INTENT_PATTERNS = {
    IntentType.THINK_PARTNER: [
        "/think", "how should", "what if", "why", "explore",
        "consider", "reflect", "深入思考", "探索"
    ],
    IntentType.BRAINSTORM: [
        "/brainstorm", "brainstorm", "ideas for", "creative",
        "generate ideas", "possibilities", "腦力激盪", "發想"
    ],
    IntentType.META_AGENT: [
        "/meta", "create tool", "new capability", "extend",
        "dynamic tool", "創建工具", "新功能"
    ],
    IntentType.WORKFLOW: [
        "/workflow", "create", "build", "make", "design",
        "implement", "execute", "建立", "創建", "設計"
    ],
}
```

---

## 4. 狀態結構 (DesignState)

```python
class DesignState(TypedDict):
    # === 基本資訊 ===
    session_id: str
    topic: str
    created_at: str

    # === 意圖分類 ===
    intent_type: str           # "workflow" | "think_partner" | "brainstorm" | "meta_agent"
    intent_confidence: float   # 0-1
    intent_keywords: List[str]

    # === Think-Partner ===
    thinking_mode: str         # "thinking" | "writing"
    thinking_log: List[ThinkingEntry]
    thinking_insights: List[str]

    # === Brainstorm ===
    brainstorm_phase: str      # "understanding" | "exploring" | "presenting" | "complete"
    brainstorm_ideas: List[BrainstormIdea]
    brainstorm_constraints: List[str]
    brainstorm_success_criteria: List[str]

    # === Meta-Agent ===
    meta_agent_active: bool
    meta_agent_operation: str
    generated_tools: List[GeneratedTool]
    agent_configs: List[AgentConfig]

    # === Workflow Pipeline ===
    current_stage: str
    subtasks: List[SubTask]
    retrieved_tools: List[Dict]
    execution_prompts: List[Dict]
    placement_info: Optional[Dict]
    component_id_map: Dict[str, str]
    final_output: Optional[Dict]

    # === 人工審核 ===
    awaiting_confirmation: bool
    pending_decisions: List[Decision]
    user_approved: bool
```

---

## 5. 使用方式

### 5.1 簡化版（推薦）

```python
from grasshopper_mcp.langgraph.core.integration import EnhancedGHOrchestrator

# 初始化
orch = EnhancedGHOrchestrator.create()

# 自動模式選擇
result = await orch.execute_with_mode_selection(
    task="brainstorm ideas for a parametric table"
)
print(f"Mode: {result['mode']}")  # → "brainstorm"

# 強制特定模式
from grasshopper_mcp.langgraph.state import IntentType
result = await orch.execute_with_mode_selection(
    task="design a chair",
    force_mode=IntentType.WORKFLOW
)

# 繼續對話
result = orch.continue_conversation("I prefer minimalist style")
```

### 5.2 CLI 命令版

```python
from grasshopper_mcp.cli import CommandHandler

handler = CommandHandler()

# 直接指定模式
await handler.execute("/think parametric design approach")
await handler.execute("/brainstorm table leg ideas")
await handler.execute("/workflow create a simple box")
await handler.execute("/meta create spiral pattern tool")
```

### 5.3 完整 Graph 執行版

```python
from grasshopper_mcp.langgraph.graphs.multi_mode_workflow import run_multi_mode_workflow

# 執行完整工作流
final_state = run_multi_mode_workflow(
    topic="design a parametric chair",
    requirements="modern style, adjustable height"
)

print(final_state["final_proposal"])
```

---

## 6. 目前限制與待辦

### 已完成 ✅
- [x] DesignState 完整定義
- [x] 四種模式的節點函數
- [x] Intent Router 意圖分類
- [x] Mode Selector 模式選擇
- [x] Graph 定義（dict 格式）
- [x] 模擬執行器 (MultiModeWorkflowRunner)
- [x] CLI 命令支援

### 待辦 ⏳
- [ ] 整合真正的 `langgraph.graph.StateGraph`
- [ ] 實作 FileCheckpointer 持久化
- [ ] 連接 `execution.py` 到真實 GrasshopperClient
- [ ] 加入 Vision nodes（截圖分析）
- [ ] 實作錯誤自動修復 (auto_fix.py)
- [ ] 加入 Gemini 作為 Critic AI

---

## 7. 檔案對照表

| 檔案 | 功能 |
|------|------|
| `langgraph/state.py` | 狀態定義 (DesignState, TypedDicts) |
| `langgraph/core/intent_router.py` | 意圖分類 |
| `langgraph/core/mode_selector.py` | 模式選擇 |
| `langgraph/core/integration.py` | EnhancedGHOrchestrator |
| `langgraph/nodes/think_partner.py` | Think-Partner 節點 |
| `langgraph/nodes/brainstorm.py` | Brainstorm 節點 |
| `langgraph/nodes/meta_agent.py` | Meta-Agent 節點 |
| `langgraph/nodes/workflow_pipeline.py` | Workflow 4階段節點 |
| `langgraph/graphs/multi_mode_workflow.py` | 完整圖定義與執行器 |
| `cli/commands.py` | CLI 命令處理 |

---

**文件版本**：1.0
**建立日期**：2026-01-18
