# Superpower Integration Architecture

> 整合 Superpowers + Claudesidian + Baoyu-skills 到 GH_MCP 智能調度系統

**Status**: ✅ Implemented (2026-01-18)

## Quick Start

```python
# 使用 CLI
from grasshopper_mcp.cli import CommandHandler
import asyncio

handler = CommandHandler()

# Think-Partner 模式
result = await handler.execute("/think parametric chair design")

# Brainstorm 模式
result = await handler.execute("/brainstorm ideas for a modern table")

# Workflow 模式
result = await handler.execute("/workflow create a simple box")

# Meta-Agent 模式
result = await handler.execute("/meta create spiral pattern tool")
```

```python
# 使用 EnhancedGHOrchestrator
from grasshopper_mcp.langgraph.core.integration import EnhancedGHOrchestrator

orch = EnhancedGHOrchestrator.create()

# 自動模式選擇
result = await orch.execute_with_mode_selection(
    task="brainstorm ideas for a parametric chair",
    context={}
)

# 強制特定模式
from grasshopper_mcp.langgraph.core import IntentType
result = await orch.execute_with_mode_selection(
    task="parametric table",
    force_mode=IntentType.WORKFLOW
)
```

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Hybrid Agent Orchestration                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Workflow Mode (確定性管線)                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│   │
│  │  │    Intent    │→ │    Tool      │→ │   Prompt     │→ │  Config  ││   │
│  │  │Decomposition │  │  Retrieval   │  │ Generation   │  │ Assembly ││   │
│  │  │  (意圖分解)  │  │ (工具檢索)   │  │ (提示生成)   │  │ (配置組裝)││   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Meta-Agent Mode (彈性架構師)                     │   │
│  │                                                                      │   │
│  │    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │   │
│  │    │ search_tool │   │ create_tool │   │  ask_user   │              │   │
│  │    │  搜尋工具   │   │  創建工具   │   │  詢問用戶   │              │   │
│  │    └─────────────┘   └─────────────┘   └─────────────┘              │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │                   ┌─────────────────────┐                           │   │
│  │                   │ create_agent_config │                           │   │
│  │                   │     生成配置        │                           │   │
│  │                   └─────────────────────┘                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 來源專案精華萃取

### 1. Superpowers 核心模式

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Superpowers 三階段方法論                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: Brainstorming (理解)                                      │
│  ├── 單一問題/消息原則                                              │
│  ├── 選擇題優先                                                     │
│  └── 聚焦：目的、約束、成功標準                                     │
│                                                                     │
│  Phase 2: Writing Plans (規劃)                                      │
│  ├── 2-5 分鐘粒度任務                                               │
│  ├── TDD 循環：Write Test → Run → Implement → Run → Commit         │
│  └── 完整可執行代碼 + 精確路徑                                      │
│                                                                     │
│  Phase 3: Subagent Execution (執行)                                 │
│  ├── 每任務獨立 Agent（防止上下文污染）                             │
│  ├── 雙層審查：Spec Compliance → Code Quality                       │
│  └── 問題發現 → 修復循環 → 重新審查                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**關鍵原則**:
- YAGNI (You Aren't Gonna Need It)
- 漸進驗證 (每 200-300 字驗證一次)
- 文檔優先 (`docs/plans/YYYY-MM-DD-<topic>.md`)

### 2. Claudesidian Think-Partner 模式

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Think-Partner 協作探索                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Thinking Mode (探索階段)                                           │
│  ├── 詢問澄清問題                                                   │
│  ├── 搜索現有知識庫                                                 │
│  ├── 識別不同想法間的連結                                           │
│  └── 維護進度日誌記錄洞見                                           │
│                                                                     │
│  Writing Mode (創作階段)                                            │
│  └── 基於思考階段的研究進行內容創作                                 │
│                                                                     │
│  核心理念：AI 放大思考，而非僅僅寫作                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Baoyu-skills 擴展機制

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Baoyu Style × Layout 系統                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  二維自定義矩陣：                                                   │
│  ┌─────────────┐                                                    │
│  │  Style      │  視覺美學 (tech, warm, minimal, ...)              │
│  │  ×          │                                                    │
│  │  Layout     │  內容組織 (density, arrangement, ...)             │
│  └─────────────┘                                                    │
│                                                                     │
│  EXTEND.md 擴展機制：                                               │
│  ├── 專案級: .baoyu-skills/EXTEND.md                                │
│  └── 用戶級: ~/.baoyu-skills/EXTEND.md                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 整合設計：GH_MCP Superpower System

### 核心架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GH_MCP Superpower System                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Layer 1: Intent Router                            │   │
│  │                                                                      │   │
│  │    User Request ──► Intent Classifier ──┬── EXPLORE ──► Think Mode  │   │
│  │                                         ├── DESIGN  ──► Brainstorm  │   │
│  │                                         ├── BUILD   ──► Workflow    │   │
│  │                                         └── DEBUG   ──► Cascade     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Layer 2: Mode Selector                            │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐          ┌──────────────────┐                 │   │
│  │  │   Workflow Mode  │          │  Meta-Agent Mode │                 │   │
│  │  │  (確定性管線)    │    OR    │   (彈性架構)     │                 │   │
│  │  │                  │          │                  │                 │   │
│  │  │  已知任務類型    │          │  未知/複雜任務   │                 │   │
│  │  │  有現成工具      │          │  需要創建工具    │                 │   │
│  │  │  明確執行路徑    │          │  需要探索路徑    │                 │   │
│  │  └──────────────────┘          └──────────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Layer 3: Execution Engine                         │   │
│  │                                                                      │   │
│  │    Workflow Pipeline:                                                │   │
│  │    ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐               │   │
│  │    │Decompose│→ │Retrieve│→ │Generate│→ │Assemble│ → Execute       │   │
│  │    └────────┘   └────────┘   └────────┘   └────────┘               │   │
│  │                                                                      │   │
│  │    Meta-Agent Toolkit:                                               │   │
│  │    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │   │
│  │    │ search   │ │ create   │ │ ask_user │ │ configure│             │   │
│  │    └──────────┘ └──────────┘ └──────────┘ └──────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Layer 4: Quality Gates                            │   │
│  │                                                                      │   │
│  │    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐   │   │
│  │    │ Spec Reviewer  │ →  │Quality Reviewer│ →  │ User Validator │   │   │
│  │    │ (規格符合性)   │    │  (代碼品質)    │    │  (用戶確認)    │   │   │
│  │    └────────────────┘    └────────────────┘    └────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 目錄結構

```
grasshopper_mcp/
├── superpower/
│   ├── __init__.py
│   ├── core/
│   │   ├── intent_router.py      # 意圖路由器
│   │   ├── mode_selector.py      # 模式選擇器
│   │   ├── workflow_engine.py    # 工作流引擎
│   │   └── meta_agent.py         # 元代理
│   │
│   ├── skills/
│   │   ├── brainstorm.py         # 腦力激盪 (from Superpowers)
│   │   ├── think_partner.py      # 思考夥伴 (from Claudesidian)
│   │   ├── write_plan.py         # 計劃撰寫
│   │   ├── execute_plan.py       # 計劃執行
│   │   └── subagent_dispatch.py  # 子代理調度
│   │
│   ├── tools/
│   │   ├── search_tool.py        # 搜尋工具
│   │   ├── create_tool.py        # 創建工具
│   │   └── tool_registry.py      # 工具註冊表
│   │
│   ├── quality/
│   │   ├── spec_reviewer.py      # 規格審查
│   │   ├── quality_reviewer.py   # 品質審查
│   │   └── review_loop.py        # 審查循環
│   │
│   └── extensions/
│       ├── extend_loader.py      # EXTEND.md 載入器
│       └── style_layout.py       # Style×Layout 系統
│
├── langgraph/
│   └── core/
│       ├── confidence.py         # 已有：Cascade 信心度
│       └── routing.py            # 已有：MoE 路由
```

---

## 核心組件設計

### 1. Intent Router (意圖路由器)

```python
class IntentType(Enum):
    EXPLORE = "explore"     # 探索/研究 → Think-Partner
    DESIGN = "design"       # 設計/規劃 → Brainstorm
    BUILD = "build"         # 建構/實作 → Workflow
    DEBUG = "debug"         # 除錯/修復 → Cascade
    UNKNOWN = "unknown"     # 未知 → Meta-Agent

class IntentRouter:
    """
    意圖分解器 - 四階段管線第一步

    分析用戶請求，決定進入哪種處理模式
    """

    INTENT_KEYWORDS = {
        IntentType.EXPLORE: ["what", "how", "why", "explain", "understand", "研究", "了解"],
        IntentType.DESIGN: ["design", "plan", "architect", "structure", "設計", "規劃"],
        IntentType.BUILD: ["build", "create", "implement", "add", "建構", "實作", "做"],
        IntentType.DEBUG: ["fix", "debug", "error", "bug", "issue", "修復", "錯誤"],
    }

    def classify(self, request: str, context: dict) -> IntentType:
        # 關鍵字匹配 + 上下文分析
        ...

    def decompose(self, request: str) -> List[SubTask]:
        # 將複雜請求分解為子任務
        ...
```

### 2. Mode Selector (模式選擇器)

```python
class ModeSelector:
    """
    根據意圖和上下文選擇處理模式

    Workflow Mode: 已知路徑，確定性執行
    Meta-Agent Mode: 未知路徑，需要探索和創建
    """

    def select(self, intent: IntentType, context: dict) -> str:
        # 檢查是否有現成工具
        has_tools = self.tool_registry.has_tools_for(intent)

        # 檢查路徑是否明確
        path_clear = self.confidence_evaluator.evaluate(intent) > 0.7

        if has_tools and path_clear:
            return "workflow"
        else:
            return "meta_agent"
```

### 3. Workflow Engine (工作流引擎)

```python
class WorkflowEngine:
    """
    確定性四階段管線

    1. Intent Decomposition - 意圖分解
    2. Tool Retrieval - 工具檢索
    3. Prompt Generation - 提示生成
    4. Config Assembly - 配置組裝
    """

    async def execute(self, request: str, intent: IntentType) -> Result:
        # Stage 1: 意圖分解
        subtasks = self.intent_router.decompose(request)

        # Stage 2: 工具檢索
        tools = []
        for task in subtasks:
            tool = self.tool_registry.find_tool(task)
            if not tool:
                tool = self.synthesize_tool(task)  # 沒有就合成
            tools.append(tool)

        # Stage 3: 提示生成
        prompts = self.generate_prompts(subtasks, tools)

        # Stage 4: 配置組裝
        config = self.assemble_config(prompts, tools)

        return await self.execute_pipeline(config)
```

### 4. Meta-Agent (元代理)

```python
class MetaAgent:
    """
    彈性架構師 Agent

    具備四種核心能力：
    - search_tool: 搜尋現有工具
    - create_tool: 創建新工具
    - ask_user: 詢問用戶澄清
    - create_agent_config: 生成配置
    """

    def __init__(self):
        self.tools = {
            "search_tool": self.search_tool,
            "create_tool": self.create_tool,
            "ask_user": self.ask_user,
            "create_agent_config": self.create_agent_config,
        }

    async def search_tool(self, query: str) -> List[Tool]:
        """搜尋知識庫和工具註冊表"""
        ...

    async def create_tool(self, spec: ToolSpec) -> Tool:
        """動態創建新工具"""
        ...

    async def ask_user(self, question: str, options: List[str] = None) -> str:
        """詢問用戶（單一問題原則）"""
        ...

    async def create_agent_config(self, task: Task) -> AgentConfig:
        """生成 Agent 配置"""
        ...
```

### 5. Think-Partner Skill

```python
class ThinkPartner:
    """
    思考夥伴 - 來自 Claudesidian

    核心理念：AI 放大思考，而非僅僅寫作

    兩種模式：
    - Thinking Mode: 探索、提問、連結
    - Writing Mode: 基於探索結果創作
    """

    def __init__(self):
        self.insights = []
        self.connections = []
        self.questions_asked = []

    async def think(self, topic: str, knowledge_base: KnowledgeBase) -> ThinkResult:
        """
        思考階段

        1. 詢問澄清問題
        2. 搜索現有知識
        3. 識別連結
        4. 記錄洞見
        """
        # 單一問題原則
        question = self.generate_clarifying_question(topic)
        answer = await self.ask_user(question)

        # 搜索知識庫
        relevant = knowledge_base.search(topic)

        # 識別連結
        connections = self.find_connections(topic, relevant)

        # 記錄洞見
        insight = self.synthesize_insight(answer, connections)
        self.insights.append(insight)

        return ThinkResult(insight, connections, self.insights)

    async def write(self, topic: str) -> str:
        """
        寫作階段

        基於思考階段的洞見進行創作
        """
        return self.generate_content(topic, self.insights)
```

### 6. Brainstorm Skill

```python
class Brainstorm:
    """
    腦力激盪 - 來自 Superpowers

    三階段方法：
    1. 理解想法
    2. 探索方案
    3. 呈現設計
    """

    async def phase1_understand(self, idea: str) -> Understanding:
        """
        Phase 1: 理解想法

        - 審查專案上下文
        - 依序詢問澄清問題（單一問題/消息）
        - 優先使用選擇題
        - 聚焦：目的、約束、成功標準
        """
        questions = [
            ("purpose", "這個功能的主要目的是什麼？"),
            ("constraints", "有什麼技術或業務約束？"),
            ("success", "如何定義成功？"),
        ]

        answers = {}
        for key, question in questions:
            answer = await self.ask_user(question)
            answers[key] = answer

        return Understanding(**answers)

    async def phase2_explore(self, understanding: Understanding) -> List[Approach]:
        """
        Phase 2: 探索方案

        - 提出 2-3 個不同方案
        - 分析取捨
        - 推薦首選並解釋原因
        """
        approaches = self.generate_approaches(understanding, count=3)

        # 推薦首選
        recommended = self.rank_approaches(approaches)[0]
        recommended.is_recommended = True

        return approaches

    async def phase3_present(self, approach: Approach) -> Design:
        """
        Phase 3: 呈現設計

        - 分段呈現（200-300 字/段）
        - 每段後驗證
        - 涵蓋：架構、組件、數據流、錯誤處理、測試
        """
        sections = [
            "architecture",
            "components",
            "data_flow",
            "error_handling",
            "testing",
        ]

        design_parts = {}
        for section in sections:
            content = self.generate_section(approach, section)
            confirmed = await self.validate_with_user(content)
            if not confirmed:
                content = await self.revise_section(section)
            design_parts[section] = content

        return Design(**design_parts)
```

---

## 擴展機制 (EXTEND.md)

```python
class ExtendLoader:
    """
    EXTEND.md 載入器 - 來自 Baoyu-skills

    優先級：
    1. 專案級: .gh_mcp/EXTEND.md
    2. 用戶級: ~/.gh_mcp/EXTEND.md
    """

    def load_extensions(self) -> Extensions:
        project_ext = self.load_project_extend()
        user_ext = self.load_user_extend()

        # 專案級覆蓋用戶級
        return self.merge_extensions(user_ext, project_ext)

    def load_project_extend(self) -> Optional[Extensions]:
        path = Path(".gh_mcp/EXTEND.md")
        if path.exists():
            return self.parse_extend_md(path)
        return None
```

### EXTEND.md 格式範例

```markdown
# GH_MCP Extensions

## Style Preferences
- default_style: "minimal"
- color_scheme: "earth_tones"
- verbosity: "concise"

## Custom Components
- prefer_cylinder_over_pipe: true
- default_tolerance: 0.01

## Workflow Overrides
- skip_brainstorm_for_simple_tasks: true
- auto_commit_plans: false

## Expert Mappings
- geometry_tasks: "gemini-pro"
- connection_tasks: "flash"
```

---

## 整合到現有 ML Ensemble 架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ML Ensemble + Superpower Integration                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  現有架構 (langgraph/core/)          新增架構 (superpower/)                 │
│  ┌──────────────────────┐            ┌──────────────────────┐              │
│  │ MoE (Expert Routing) │ ◄────────► │   Intent Router      │              │
│  │   routing.py         │            │   意圖路由器         │              │
│  └──────────────────────┘            └──────────────────────┘              │
│           │                                    │                            │
│           ▼                                    ▼                            │
│  ┌──────────────────────┐            ┌──────────────────────┐              │
│  │ Cascade (Confidence) │ ◄────────► │   Mode Selector      │              │
│  │   confidence.py      │            │   Workflow/Meta      │              │
│  └──────────────────────┘            └──────────────────────┘              │
│           │                                    │                            │
│           ▼                                    ▼                            │
│  ┌──────────────────────┐            ┌──────────────────────┐              │
│  │  Expert Execution    │ ◄────────► │  Subagent Dispatch   │              │
│  │                      │            │  + Quality Gates     │              │
│  └──────────────────────┘            └──────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

整合點：
1. Intent Router 使用 MoE 的專家定義
2. Mode Selector 使用 Cascade 的信心度評估
3. Subagent Dispatch 複用 Expert Execution 機制
4. Quality Gates 整合到 Confidence 評估
```

---

## 實作路線圖

### Phase 1: 核心框架 (本次)
- [ ] Intent Router
- [ ] Mode Selector
- [ ] Think-Partner Skill
- [ ] Brainstorm Skill

### Phase 2: 工作流引擎
- [ ] Workflow Engine 四階段管線
- [ ] Tool Registry
- [ ] Prompt Generation

### Phase 3: Meta-Agent
- [ ] search_tool
- [ ] create_tool
- [ ] ask_user
- [ ] create_agent_config

### Phase 4: 品質保證
- [ ] Spec Reviewer
- [ ] Quality Reviewer
- [ ] Review Loop

### Phase 5: 擴展系統
- [ ] EXTEND.md 載入器
- [ ] Style × Layout 系統

---

*最後更新: 2026-01-18*
