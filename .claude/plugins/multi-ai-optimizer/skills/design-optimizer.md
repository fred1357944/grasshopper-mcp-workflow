---
name: design-optimizer
description: "Claude + Gemini 交替優化設計方案。用於需要迭代改進的設計任務，如 Grasshopper 參數化建模、架構設計、演算法優化。支援方案 A（迭代優化）和方案 B（多變體探索）。"
activationKeywords:
  - optimize design
  - 優化設計
  - 迭代改進
  - 交替方案
  - multi-ai
  - 雙AI協作
---

# Design Optimizer Skill

## 概述

此 Skill 啟用 Claude + Gemini 交替優化模式，適用於需要多輪迭代的設計任務。

## 工作模式選擇

### 方案 A：迭代設計優化 (Iterative)

單一設計，多次精煉：

```
Claude 方案 → Gemini 評論 → Claude 改進 → Gemini 評論 → ... → 收斂
```

適用於：
- 明確的設計目標
- 需要逐步精煉
- 單一最優解

### 方案 B：多變體探索 (Multi-Variant)

多個設計，並行評估：

```
生成變體 1, 2, 3, ... N → 並行評估 → 選擇最佳 → 可選：進一步優化最佳
```

適用於：
- 探索設計空間
- 不確定最優方向
- 需要比較多種可能

## 使用方式

### 啟動迭代優化

```
我需要優化這個 Grasshopper 組件連接設計，請使用迭代優化模式，最多 5 次迭代。
```

### 啟動多變體探索

```
我想探索這個參數化設計的多種可能，請生成 3 個變體並比較。
```

## Claude-Gemini 交互協議

### 調用 Gemini

使用終端機命令調用 Gemini：

```bash
# 基本調用
gemini "請評論以下設計方案並提出改進建議：[方案內容]"

# 要求結構化輸出
gemini "分析以下 Grasshopper 組件連接，以 JSON 格式回應：[組件圖]"
```

### 交互格式

每輪交互記錄：

```markdown
## Iteration {N}

### Claude 提案
[方案內容]

### Gemini 回應
[評論或替代方案]

### 分析
- 共識點：[...]
- 分歧點：[...]
- 收斂度：[0.0-1.0]

### 決策點
- [ ] [需要確認的決策]
```

## 確認觸發點

在以下情況暫停等待用戶確認：

1. **關鍵決策** - 架構選擇、技術方向變更
2. **收斂達成** - 兩 AI 意見趨於一致（收斂度 > 0.85）
3. **最大次數** - 達到用戶指定的迭代上限

## 狀態持久化

優化過程持久化到 `GH_WIP/optimization_session/`：

```
GH_WIP/optimization_session/
├── session_state.json      # 當前狀態
├── proposals/              # 所有提案
│   ├── 001_claude.md
│   ├── 002_gemini.md
│   └── ...
├── decisions.json          # 決策記錄
└── optimization_log.md     # 完整日誌
```

## 輸出格式

最終輸出包含：

1. **方案演進摘要** - 從初始到最終的變化軌跡
2. **關鍵決策回顧** - 影響結果的重要決策點
3. **最終推薦方案** - 經過優化的設計方案
4. **實施建議** - 後續步驟和注意事項

## 與 Grasshopper 工作流整合

```
Step 1: 需求澄清
    └── 可用 /thinking 探索

Step 2: 幾何分解 (part_info.mmd)
    └── 可用本 Skill 優化結構

Step 3: 組件連接 (component_info.mmd)
    └── 可用本 Skill 優化連接

Step 4-5: GUID 解析 + 執行
    └── 使用現有 MCP 工具

Step 6: 回顧
    └── 可用 /review 總結
```

## 最佳實踐

1. **明確優化目標** - 開始前說明想優化什麼
2. **設定合理迭代數** - 簡單任務 3 次，複雜任務 5-10 次
3. **關注收斂信號** - 當兩 AI 開始同意時考慮停止
4. **記錄決策理由** - 方便後續回顧和調整
