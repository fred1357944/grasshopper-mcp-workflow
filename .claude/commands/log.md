---
description: 快速記錄本次開發 session 的重點
arguments:
  - name: summary
    description: 本次 session 的簡短摘要
    required: false
---

# 開發記錄

記錄本次 Claude Code session 的重點到 `DEV_LOG.md`。

## 記錄內容

1. **日期時間**：自動填入
2. **摘要**：$ARGUMENTS（如未提供，自動從 git log 分析）
3. **變更檔案**：從 git status/diff 取得
4. **關鍵決策**：記錄重要的設計決策

## 格式範例

```markdown
## 2026-01-06 14:30

### 摘要
$ARGUMENTS

### 變更
- `file1.py` - 描述
- `file2.md` - 描述

### 決策
- 選擇 X 而非 Y，因為...

---
```

## 執行步驟

1. 檢查 git 狀態
2. 分析變更內容
3. 追加到 `DEV_LOG.md`（如不存在則創建）
4. 不需要 git commit（這是純記錄用）
