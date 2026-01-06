# Multi-AI Optimizer Plugin 設計文件

> 版本：v0.1.0 | 日期：2026-01-06 | 狀態：✅ 實作完成

## 概述

本文件記錄 Claude + Gemini 多次交互優化 Plugin 的設計，參考 [Claudesidian](https://github.com/heyitsnoah/claudesidian) 的設計模式。

## 設計背景

### 需求分析

1. **階段性優化** - Grasshopper 設計需要迭代優化
2. **持續互動** - 需要多輪對話來精煉設計
3. **雙 AI 協作** - Claude (Opus) 與 Gemini 交替生成方案，互相評論
4. **人工確認機制** - 關鍵決策點、收斂時、最大次數時確認

### 參考設計：Claudesidian

#### 核心模式

| 模式 | 功能 | 適用場景 |
|------|------|----------|
| `/thinking-partner` | 協作探索，問問題優先於給答案 | 複雜問題探索 |
| `/daily-review` | 每日回顧，總結進度 | 工作流結束 |
| `/research-assistant` | 深度研究，知識綜合 | 資料收集階段 |

#### 設計哲學

```
Thinking Mode ──→ Writing Mode
   (探索)            (執行)

"Your value is in the quality of exploration,
 not the speed of resolution"
```

---

## 架構設計

### 核心概念：交替生成 + 多重確認

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Multi-AI Collaborative Loop                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [用戶需求] ───┬──→ [Claude 方案 A] ──→ [Gemini 評論/方案 B]        │
│               │          ↓                      ↓                  │
│               │    [Claude 整合 B 建議] ──→ [Gemini 評論/方案 C]    │
│               │          ↓                      ↓                  │
│               │    [迭代 N 次或收斂]                                │
│               │          ↓                                         │
│  [決策確認] ←─┴──── [最終方案呈現]                                  │
│               │                                                     │
│  確認點：                                                           │
│  - 關鍵架構決策                                                     │
│  - 達到收斂（兩 AI 共識）                                           │
│  - 達到最大迭代次數                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 狀態定義

```python
from typing import TypedDict, Literal, Optional
from datetime import datetime

class OptimizationState(TypedDict):
    # 基本信息
    session_id: str
    topic: str
    created_at: datetime

    # 迭代控制
    current_iteration: int
    max_iterations: int  # 用戶每次指定

    # 方案歷史
    proposals: list[dict]  # [{ai: "claude"|"gemini", content: str, timestamp: datetime}]

    # 收斂狀態
    convergence_score: float  # 0.0 - 1.0
    is_converged: bool

    # 決策點
    pending_decisions: list[dict]  # [{question: str, options: list, importance: "high"|"medium"|"low"}]
    decisions_made: list[dict]

    # 最終輸出
    final_proposal: Optional[str]
    user_approved: bool
```

### 確認觸發邏輯

```python
def should_pause_for_confirmation(state: OptimizationState) -> tuple[bool, str]:
    """
    判斷是否需要暫停等待用戶確認

    Returns:
        (should_pause, reason)
    """
    # 1. 關鍵決策點
    high_importance_decisions = [
        d for d in state["pending_decisions"]
        if d["importance"] == "high"
    ]
    if high_importance_decisions:
        return True, "critical_decision"

    # 2. 達到收斂
    if state["is_converged"] and state["convergence_score"] > 0.85:
        return True, "convergence_reached"

    # 3. 達到最大次數
    if state["current_iteration"] >= state["max_iterations"]:
        return True, "max_iterations_reached"

    return False, "continue"
```

---

## Plugin 結構

### 目錄結構

```
~/.claude/plugins/multi-ai-optimizer/
├── plugin.json                    # Plugin 配置
├── PLUGIN.md                      # Plugin 說明
│
├── skills/
│   ├── design-optimizer.md        # 主要 Skill: 設計優化迴圈
│   ├── thinking-partner.md        # 協作探索 (參考 Claudesidian)
│   └── research-synthesis.md      # 研究綜合
│
├── commands/
│   ├── optimize.md                # /optimize [topic] [iterations]
│   ├── thinking.md                # /thinking [topic]
│   └── review.md                  # /review
│
├── agents/
│   ├── optimizer-coordinator.md   # 協調 Claude-Gemini 交互
│   └── convergence-detector.md    # 收斂檢測代理
│
├── hooks/
│   ├── pre-iteration.md           # 迭代前檢查
│   └── post-iteration.md          # 迭代後分析
│
└── scripts/
    ├── gemini_caller.py           # Gemini CLI 調用封裝
    ├── iteration_manager.py       # 迭代管理器
    ├── convergence_analyzer.py    # 收斂分析器
    └── session_state.py           # 狀態持久化
```

### plugin.json

```json
{
  "name": "multi-ai-optimizer",
  "version": "0.1.0",
  "description": "Claude + Gemini 多次交互優化 Plugin，支援交替生成方案、迭代優化、智能收斂檢測",
  "author": "laihongyi",
  "skills": ["skills/"],
  "commands": ["commands/"],
  "agents": ["agents/"],
  "hooks": ["hooks/"],
  "settings": {
    "default_max_iterations": 5,
    "convergence_threshold": 0.85,
    "auto_gemini_timeout": 60,
    "confirmation_triggers": [
      "critical_decision",
      "convergence_reached",
      "max_iterations_reached"
    ]
  }
}
```

---

## 核心 Skill 設計

### design-optimizer.md

```markdown
---
name: design-optimizer
description: "Claude + Gemini 交替優化設計方案。用於需要迭代改進的設計任務，如 Grasshopper 參數化建模、架構設計、演算法優化。"
activationKeywords:
  - optimize design
  - 優化設計
  - 迭代改進
  - 交替方案
---

# Design Optimizer Skill

## 工作模式

### 交替生成方案

你與 Gemini 交替提出方案：

1. **你 (Claude)**: 提出初始方案 A
2. **Gemini**: 評論方案 A + 提出改進方案 B
3. **你 (Claude)**: 整合 B 的優點 + 提出方案 C
4. **循環直到收斂或達到最大次數**

### 調用 Gemini

使用終端機調用 Gemini：

\`\`\`bash
# 非交互模式，獲取單次回應
gemini "請評論以下設計方案並提出改進建議：[方案內容]"

# 或使用 -p 參數
gemini -p "分析這個 Grasshopper 組件連接是否合理：[組件圖]"
\`\`\`

### 迭代記錄格式

每次迭代記錄到 `GH_WIP/optimization_log.md`：

\`\`\`markdown
## Iteration {N}

### Claude 方案
[方案內容]

### Gemini 評論
[評論內容]

### 決策點
- [ ] [需要確認的決策]

### 下一步
[計劃]
\`\`\`

## 確認觸發點

在以下情況暫停等待用戶確認：

1. **關鍵決策** - 架構選擇、技術方向
2. **收斂達成** - 兩 AI 意見趨於一致
3. **最大次數** - 達到用戶指定的迭代上限

## 輸出格式

最終輸出包含：

1. 方案演進摘要
2. 關鍵決策點回顧
3. 最終推薦方案
4. 實施建議
```

### thinking-partner.md (參考 Claudesidian)

```markdown
---
name: thinking-partner
description: "協作探索模式，通過提問引導思考而非直接給答案。適用於複雜問題的初期探索。"
activationKeywords:
  - think together
  - explore idea
  - 一起想想
  - 探索
---

# Thinking Partner Skill

## 核心原則

> "Your value is in the quality of exploration, not the speed of resolution."

### 行為模式

1. **問問題優先** - 先問 3-5 個探索性問題
2. **記錄洞察** - 系統性記錄對話中的發現
3. **連結概念** - 找出不同想法之間的關聯
4. **挑戰假設** - 質疑潛在的限制性假設

### 探索性問題範例

- "這個想法背後的動機是什麼？"
- "這與 [其他概念] 有什麼關聯？"
- "如果相反的情況成立呢？"
- "我們可能忽略了什麼？"

## 與 Gemini 協作探索

可以讓 Gemini 提供不同視角：

\`\`\`bash
gemini "從不同角度思考：[問題]。請提出 3 個挑戰性問題。"
\`\`\`

## 輸出到 GH_WIP/thinking_log.md
```

---

## 命令設計

### /optimize 命令

```markdown
---
name: optimize
description: "啟動 Claude + Gemini 優化迴圈"
arguments:
  - name: topic
    description: 優化主題
    required: true
  - name: iterations
    description: 最大迭代次數
    required: false
    default: "由用戶指定"
---

# /optimize 命令

## 使用方式

\`\`\`
/optimize "Grasshopper 桌子組件連接優化" 5
/optimize "API 架構設計" 3
\`\`\`

## 執行流程

1. 詢問用戶確認迭代次數（如未指定）
2. 創建優化 session
3. 啟動 Claude-Gemini 交替迴圈
4. 在確認點暫停
5. 輸出最終方案
```

---

## Grasshopper 工作流整合

### 整合點

```
┌─────────────────────────────────────────────────────────────────────┐
│                Grasshopper Workflow + Multi-AI Optimizer             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: 需求澄清                                                   │
│    └── /thinking 探索設計需求                                        │
│                                                                     │
│  Step 2: 幾何分解                                                   │
│    └── /optimize "part_info.mmd 結構" [N]                           │
│                                                                     │
│  Step 3: 組件連接規劃                                               │
│    └── /optimize "component_info.mmd 連接" [N]                      │
│                                                                     │
│  Step 4-5: GUID 解析 + 執行                                         │
│    └── 使用現有 MCP 工具                                            │
│                                                                     │
│  Step 6: 回顧                                                       │
│    └── /review 總結優化過程                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 範例工作流

```bash
# 1. 探索設計需求
/thinking "需要設計一張參數化桌子"

# 2. 優化幾何分解（3 次迭代）
/optimize "桌子幾何分解方案" 3

# 3. 優化組件連接（5 次迭代）
/optimize "Grasshopper 組件連接圖" 5

# 4. 執行
python -m grasshopper_tools.cli execute-placement placement_info.json

# 5. 回顧
/review
```

---

## 全局 Claude 配置建議

### 是否需要導入全局？

#### 評估

| 因素 | 全局導入 | 專案級導入 |
|------|----------|------------|
| **適用性** | 所有專案可用 | 僅此專案 |
| **衝突風險** | 可能與其他配置衝突 | 隔離 |
| **維護成本** | 統一維護 | 分散維護 |
| **載入開銷** | 每次都載入 | 按需載入 |

#### 建議

**推薦：專案級導入 + 全局命令**

1. **全局**：添加通用命令到 `~/.claude/commands/`
   - `/thinking.md` - 通用探索模式
   - `/ai-collab.md` - AI 協作基礎命令

2. **專案級**：完整 Plugin 放在專案內
   - `grasshopper-mcp-workflow/.claude/plugins/multi-ai-optimizer/`

### 全局添加的內容

#### ~/.claude/commands/thinking.md

```markdown
---
name: thinking
description: "協作探索模式，通過提問引導深度思考"
---

# Thinking Partner

## 模式

進入探索模式：

1. 先問 3-5 個探索性問題
2. 記錄對話中的洞察
3. 連結不同概念
4. 質疑潛在假設

## 問題範例

- "這個想法背後的動機是什麼？"
- "這與 [X] 有什麼關聯？"
- "反過來思考會如何？"
- "我們忽略了什麼？"

## 可選：調用 Gemini 獲取不同視角

\`\`\`bash
gemini "從批判角度分析：[主題]"
\`\`\`
```

#### ~/.claude/commands/ai-collab.md

```markdown
---
name: ai-collab
description: "啟動 Claude + Gemini 協作模式"
arguments:
  - name: task
    description: 協作任務描述
    required: true
---

# AI 協作模式

調用 Gemini 獲取第二意見：

\`\`\`bash
gemini "[任務描述]。請提供你的分析和建議。"
\`\`\`

整合 Gemini 回應後，提出綜合方案。
```

---

## 下一步

### Phase 1: 基礎實現
- [ ] 創建 Plugin 目錄結構
- [ ] 實現 `gemini_caller.py`
- [ ] 實現基礎 `/optimize` 命令

### Phase 2: 完整功能
- [ ] 實現收斂檢測
- [ ] 實現狀態持久化
- [ ] 添加 hooks

### Phase 3: Grasshopper 整合
- [ ] 整合到 6 步驟工作流
- [ ] 添加 MMD 優化專用模式
- [ ] 測試端到端流程

---

## 附錄：Claudesidian 參考資料

### 設計模式摘要

1. **Thinking vs Writing Mode** - 分離探索與執行
2. **Vault as Memory** - 使用檔案系統持久化上下文
3. **Human-in-the-loop** - 關鍵點暫停確認
4. **Multi-source Integration** - 整合多個來源

### 關鍵引用

> "Ask before answering - Lead with questions that help clarify and deepen understanding."

> "Your value is in the quality of exploration, not the speed of resolution."
