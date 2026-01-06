---
name: optimize
description: "啟動 Claude + Gemini 優化迴圈，支援迭代優化(A)或多變體探索(B)模式"
arguments:
  - name: topic
    description: 優化主題或設計需求
    required: true
  - name: mode
    description: "優化模式: iterative(迭代優化) 或 variants(多變體探索)"
    required: false
    default: "auto"
  - name: iterations
    description: 最大迭代次數或變體數量
    required: false
---

# /optimize 命令

啟動 Claude + Gemini 協作優化流程。

## 使用方式

```bash
# 自動選擇模式
/optimize "優化桌子的 Grasshopper 組件連接"

# 指定迭代優化模式 (Option A)
/optimize "改進參數化設計" iterative 5

# 指定多變體探索模式 (Option B)
/optimize "探索不同的腿部設計" variants 3
```

## 執行流程

### 1. 模式選擇

根據您的輸入自動或手動選擇：

| 模式 | 適用場景 | 關鍵詞 |
|------|----------|--------|
| **迭代優化 (A)** | 有明確目標，需要逐步精煉 | 優化、改進、調整、修正 |
| **多變體探索 (B)** | 不確定方向，想比較多種可能 | 探索、比較、嘗試、生成 |

### 2. Claude-Gemini 交互

**迭代模式**：
```
Claude 提出方案 → Gemini 評論/改進 → Claude 整合 → 循環至收斂
```

**多變體模式**：
```
生成 N 個變體 → 並行評估 → 選擇最佳 → 可選進一步優化
```

### 3. 確認點

在以下情況暫停等待您確認：

1. **關鍵決策** - 架構選擇、技術方向
2. **收斂達成** - 兩 AI 意見趨於一致
3. **最大次數** - 達到指定迭代上限
4. **變體選擇** - 多變體模式選出最佳後

## 輸出

優化過程持久化到 `GH_WIP/optimization_session/`：

```
GH_WIP/optimization_session/
├── session_state.json      # 當前狀態
├── proposals/              # 所有提案
├── decisions.json          # 決策記錄
└── optimization_log.md     # 完整日誌
```

## 範例

### 範例 1: 優化組件連接

```
/optimize "優化 component_info.mmd 中的 Slider 到 Rectangle 的連接效率" iterative 5
```

執行：
1. 分析當前連接結構
2. Claude 提出優化方案
3. Gemini 審核並建議改進
4. 迭代直到收斂或達 5 次
5. 輸出最終建議

### 範例 2: 探索設計變體

```
/optimize "探索桌腿的不同設計方案" variants 4
```

執行：
1. 分析設計需求
2. 生成 4 個不同變體
3. 評估每個變體
4. 比較並推薦最佳
5. 等待確認或進一步優化

## 進階選項

可以在對話中調整：

- "增加迭代次數到 10"
- "切換到多變體模式"
- "跳過這個決策點"
- "直接使用當前最佳方案"
