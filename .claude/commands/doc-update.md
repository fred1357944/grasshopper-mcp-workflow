---
description: 更新專案文檔和 CHANGELOG
arguments:
  - name: changes
    description: 本次變更的簡短描述
    required: false
---

# 文檔更新任務

請執行以下文檔更新流程：

## 1. 分析最近變更

檢查 git 狀態和最近的 commits：
```bash
git status
git log --oneline -5
git diff --name-only HEAD~1
```

## 2. 更新 CHANGELOG.md

在 `CHANGELOG.md` 中添加新條目：
- 日期：今天
- 變更類型：Added / Changed / Fixed / Security
- 變更描述：$ARGUMENTS

## 3. 更新相關文檔

根據變更類型，更新對應的文檔：
- 功能變更 → `docs/LANGGRAPH_USAGE_GUIDE.md`
- 設計變更 → `docs/MULTI_AI_OPTIMIZER_DESIGN.md`
- API 變更 → 相關模組的 docstring

## 4. 提交更新

```bash
git add CHANGELOG.md docs/
git commit -m "docs: 更新文檔 - $ARGUMENTS"
```

## 輸出格式

完成後，簡要列出：
- [ ] 更新了哪些文件
- [ ] CHANGELOG 新增了什麼
- [ ] 是否已提交
