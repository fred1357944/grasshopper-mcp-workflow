---
name: gh-reset
description: 重置 Grasshopper 工作流程 — 清空 GH_WIP 目錄，準備開始新專案
---

# /gh-reset — 重置工作流程

## 用途

清空 `GH_WIP/` 目錄，讓 `/grasshopper` 可以從 Phase 1 重新開始。

適用於：
- 課堂示範重來
- 放棄目前設計，開始新專案
- 清理測試檔案

## 行為

### 執行步驟

1. 檢查 `GH_WIP/` 是否存在
2. 顯示將被刪除的檔案列表
3. 詢問使用者確認
4. 刪除所有檔案（保留目錄）
5. 顯示完成訊息

### 輸出格式

```
【重置工作流程】

將刪除以下檔案:
- GH_WIP/part_info.mmd
- GH_WIP/component_info.mmd
- GH_WIP/placement_info.json

確定要重置嗎？(Y/N)
```

確認後：
```
✓ 已清空 GH_WIP/

現在可以使用 /grasshopper 開始新設計
```

## 安全措施

- **不會刪除** `GH_PKG/` 中的歸檔檔案
- **不會刪除** `GH_WIP/` 目錄本身
- **必須確認** 才會執行刪除

## 使用方式

```
User: /gh-reset
User: 重來 (在 /grasshopper 流程中)
```
