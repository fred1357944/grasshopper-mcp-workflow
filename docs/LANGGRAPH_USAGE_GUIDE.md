# LangGraph 優化工作流使用指南

> 版本：v0.1.0 | 日期：2026-01-06

本文件說明如何使用 LangGraph 整合模組和 Multi-AI Optimizer Plugin 來進行 Grasshopper 設計優化。

## 目錄

1. [概述](#概述)
2. [安裝與設置](#安裝與設置)
3. [兩種優化模式](#兩種優化模式)
4. [使用 Plugin 命令](#使用-plugin-命令)
5. [使用 Python API](#使用-python-api)
6. [工作流程整合](#工作流程整合)
7. [狀態持久化](#狀態持久化)
8. [最佳實踐](#最佳實踐)
9. [故障排除](#故障排除)

---

## 概述

本系統提供兩種設計優化模式：

| 模式 | 說明 | 適用場景 |
|------|------|----------|
| **Option A: 迭代優化** | Claude 和 Gemini 交替提出/評論方案，逐步收斂 | 有明確目標，需要精煉 |
| **Option B: 多變體探索** | 並行生成多個設計變體，評估後選擇最佳 | 探索設計空間，比較可能性 |

### 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph 狀態機架構                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [需求澄清] ──→ [幾何分解] ──→ [組件規劃] ──→ [執行]         │
│       ↑              ↓              ↓            ↓          │
│       │         ┌────┴────┐    ┌────┴────┐  ┌───┴───┐      │
│       │         │ 驗證迴圈 │    │ 衝突檢測 │  │ 錯誤  │      │
│       │         └────┬────┘    └────┬────┘  │ 分析  │      │
│       │              ↓              ↓       └───┬───┘      │
│       └──────── [人工決策點] ←─────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 安裝與設置

### 前置需求

1. **Python 3.8+**
2. **Gemini CLI** - 用於雙 AI 協作

```bash
# 確認 Gemini CLI 已安裝
which gemini
gemini --version
```

### 確認模組可用

```bash
cd /path/to/grasshopper-mcp-workflow

# 測試 import
python3 -c "from grasshopper_mcp.langgraph import create_workflow, WorkflowType; print('OK')"
```

---

## 兩種優化模式

### Option A: 迭代優化 (Iterative)

**流程：**
```
Claude 提案 → Gemini 評論 → Claude 改進 → Gemini 評論 → ... → 收斂/達最大次數
```

**特點：**
- 單一設計，多次精煉
- 計算收斂分數（0.0 - 1.0）
- 收斂度 > 0.85 時自動觸發確認

**適用場景：**
- "優化這個組件連接"
- "改進參數化設計"
- "調整桌腿比例"

### Option B: 多變體探索 (Multi-Variant)

**流程：**
```
生成 N 個變體 → 並行評估 → 計算品質分數 → 選擇最佳 → 可選進一步優化
```

**特點：**
- 多個設計並行
- 每個變體獨立評分
- 可比較不同參數組合

**適用場景：**
- "探索不同的桌腿設計"
- "比較三種連接方式"
- "生成多種尺寸變體"

---

## 使用 Plugin 命令

### /optimize - 啟動優化

```bash
# 自動選擇模式（根據關鍵詞判斷）
/optimize "優化桌子的組件連接"

# 指定迭代模式，最多 5 次
/optimize "改進參數化設計" iterative 5

# 指定多變體模式，生成 3 個變體
/optimize "探索不同桌腿設計" variants 3
```

**參數說明：**

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `topic` | 優化主題（必填） | - |
| `mode` | `iterative` / `variants` / `auto` | `auto` |
| `iterations` | 最大迭代數或變體數 | 5 |

### /thinking - 協作探索

```bash
/thinking "我需要設計一個可調整高度的桌子"
```

進入探索模式後，Claude 會：
1. 先問 3-5 個探索性問題
2. 記錄對話中的洞察
3. 連結不同概念
4. 等您準備好再進入執行模式

### /review - 回顧結果

```bash
# 回顧最近的 session
/review

# 回顧特定 session
/review abc123
```

輸出包含：
- Session 概要
- 方案演進歷程
- 決策記錄
- 收斂分析
- 後續建議

---

## 使用 Python API

### 基本使用

```python
from grasshopper_mcp.langgraph.integration import GrasshopperLangGraphIntegration

# 初始化
integration = GrasshopperLangGraphIntegration(
    work_dir="./GH_WIP",
    grasshopper_host="localhost",
    grasshopper_port=8080
)

# 啟動優化
state = integration.start_optimization(
    topic="優化桌子組件連接",
    mode="iterative",  # 或 "variants" 或 "auto"
    max_iterations=5
)

print(f"Session ID: {state['session_id']}")
print(f"Mode: {state['mode']}")
```

### 執行步驟

```python
# 執行一步
state = integration.run_step()

# 檢查是否需要用戶輸入
if state.get('awaiting_confirmation'):
    reason = state.get('confirmation_reason')
    print(f"需要確認: {reason}")

    # 提供用戶輸入
    state = integration.provide_input({"approved": True})
```

### 處理決策點

```python
# 檢查待決策項目
pending = state.get('pending_decisions', [])
for decision in pending:
    print(f"問題: {decision['question']}")
    print(f"選項: {decision['options']}")

# 提供決策
state = integration.provide_input({
    "decision": {
        "id": decision['id'],
        "choice": "選項1"
    }
})
```

### 獲取報告

```python
report = integration.get_report()
print(report)

# 獲取狀態
status = integration.get_status()
print(f"階段: {status['stage']}")
print(f"迭代: {status['iteration']}/{status['max_iterations']}")
print(f"收斂度: {status['convergence']}")
```

### 恢復 Session

```python
# 列出所有 sessions
from grasshopper_mcp.langgraph.checkpointers import FileCheckpointer
checkpointer = FileCheckpointer()
sessions = checkpointer.list_sessions()

for s in sessions:
    print(f"{s['session_id']}: {s['topic']} ({s['stage']})")

# 恢復特定 session
state = integration.resume_session(session_id="abc123")

# 或恢復最近的
state = integration.resume_session()
```

---

## 工作流程整合

### 完整 Grasshopper 工作流

```
Step 1: 需求澄清
    └── /thinking 探索設計需求

Step 2: 幾何分解 (part_info.mmd)
    └── /optimize "優化幾何分解結構" iterative 3

Step 3: 組件連接 (component_info.mmd)
    └── /optimize "優化組件連接圖" iterative 5

Step 4: GUID 解析
    └── 使用現有 MCP 工具

Step 5: 執行
    └── python -m grasshopper_tools.cli execute-placement placement_info.json

Step 6: 回顧
    └── /review
```

### 整合現有工具

```python
# 解析 MMD
components, connections = integration.parse_component_info("component_info.mmd")

# 生成 placement_info
placement = integration.generate_placement_info(components, connections)

# 執行
result = integration.execute_placement(placement)
print(f"成功: {result['add_success']} 組件, {result['connect_success']} 連接")
```

---

## 狀態持久化

### 存儲結構

所有狀態保存在 `GH_WIP/optimization_session/`：

```
GH_WIP/optimization_session/
├── sessions/
│   └── {session_id}/
│       ├── state.json          # 當前狀態
│       ├── history/            # 狀態歷史
│       │   ├── 001_state.json
│       │   ├── 002_state.json
│       │   └── ...
│       └── proposals/          # 提案記錄
│           ├── 001_claude.md
│           └── 002_gemini.md
└── index.json                  # Session 索引
```

### 回滾到先前狀態

```python
checkpointer = FileCheckpointer()

# 獲取歷史
history = checkpointer.get_history(session_id)
print(f"共 {len(history)} 個快照")

# 回滾到第 3 個快照
state = checkpointer.rollback(session_id, history_index=3)
```

---

## 最佳實踐

### 1. 選擇正確的模式

| 情況 | 推薦模式 |
|------|----------|
| 有明確的優化目標 | 迭代優化 |
| 不確定最佳方向 | 多變體探索 |
| 需要比較多種參數 | 多變體探索 |
| 需要逐步精煉 | 迭代優化 |

### 2. 設定合理的迭代數

- **簡單優化**：3 次
- **中等複雜度**：5 次
- **複雜設計**：10 次

### 3. 關注收斂信號

當收斂度 > 0.85 時，通常表示兩個 AI 已達成共識，可以考慮停止迭代。

### 4. 善用探索模式

在不確定需求時，先使用 `/thinking` 探索，再使用 `/optimize` 執行。

### 5. 記錄決策理由

在做出決策時，記住為什麼選擇特定選項，方便後續回顧。

---

## 故障排除

### Gemini CLI 無法調用

```bash
# 確認安裝
which gemini

# 測試調用
gemini "Hello"
```

### 狀態無法保存

確認 `GH_WIP/` 目錄有寫入權限：

```bash
ls -la GH_WIP/
```

### Import 錯誤

確認在專案根目錄執行：

```bash
cd /path/to/grasshopper-mcp-workflow
python3 -c "from grasshopper_mcp.langgraph import *"
```

### 工作流卡住

1. 檢查是否有未處理的決策點
2. 使用 `integration.get_status()` 查看當前狀態
3. 如需重置，刪除 session：

```python
checkpointer.delete_session(session_id)
```

---

## 相關資源

- [設計文件](./MULTI_AI_OPTIMIZER_DESIGN.md)
- [Plugin 文檔](../.claude/plugins/multi-ai-optimizer/PLUGIN.md)
- [Claudesidian 參考](https://github.com/heyitsnoah/claudesidian)
- [LangGraph 官方文檔](https://langchain-ai.github.io/langgraph/)
