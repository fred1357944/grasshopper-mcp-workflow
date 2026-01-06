---
name: review
description: "回顧優化過程，總結決策和結果，生成優化報告"
arguments:
  - name: session_id
    description: 要回顧的 session ID（可選，默認為最近的 session）
    required: false
---

# /review 命令

回顧優化過程，生成總結報告。

## 使用方式

```bash
# 回顧最近的優化 session
/review

# 回顧特定 session
/review abc123
```

## 報告內容

### 1. Session 概要

```markdown
## Optimization Session Summary

- **Topic**: [優化主題]
- **Mode**: [Iterative / Multi-Variant]
- **Duration**: [開始時間] - [結束時間]
- **Iterations**: [實際迭代次數] / [最大次數]
- **Final Status**: [Converged / Max Iterations / User Approved]
```

### 2. 方案演進

顯示從初始到最終的變化軌跡：

```markdown
## Proposal Evolution

### Iteration 1
- **Claude**: [摘要]
- **Gemini**: [摘要]
- **Key Change**: [主要變化]

### Iteration 2
...

### Final Proposal
[最終方案摘要]
```

### 3. 決策回顧

所有決策點的記錄：

```markdown
## Decisions Made

| # | Question | Choice | Impact |
|---|----------|--------|--------|
| 1 | [問題] | [選擇] | [影響] |
| 2 | ... | ... | ... |
```

### 4. 收斂分析

```markdown
## Convergence Analysis

- **Final Score**: 0.87
- **Convergence Trend**: [上升/震盪/穩定]
- **Key Agreement Points**: [共識點]
- **Remaining Differences**: [分歧點]
```

### 5. 建議和後續

```markdown
## Recommendations

### Immediate Actions
1. [行動 1]
2. [行動 2]

### Future Considerations
- [考慮 1]
- [考慮 2]

### Files to Update
- [ ] component_info.mmd
- [ ] placement_info.json
```

## 輸出位置

報告保存到：
- `GH_WIP/optimization_session/review_report.md`
- 同時顯示在對話中

## 額外功能

### 比較多個 Session

```bash
/review --compare session1 session2
```

### 導出為特定格式

```bash
/review --format json
/review --format markdown
```

### 包含詳細提案

```bash
/review --verbose
```

## 與 Grasshopper 工作流整合

回顧後的建議操作：

```bash
# 如果需要更新 component_info.mmd
# 報告會提供具體的修改建議

# 如果需要重新執行
python -m grasshopper_tools.cli execute-placement placement_info.json
```
