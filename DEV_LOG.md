# Development Log

## 2026-01-06 22:55 - Project Consolidation

### Summary
Consolidated grasshopper-mcp-workflow repository and cleaned up branch structure.

### Changes
- Set `master` as default branch on GitHub
- Deleted old `main` branch (redundant content)
- Created backup: `grasshopper-mcp-workflow-backup-20260106-225028`

### Current State
```
Repository: fred1357944/grasshopper-mcp-workflow
Branch: master (only branch)
Status: Clean, in sync with remote
```

### Key Components
| Component | Status | Description |
|-----------|--------|-------------|
| LangGraph Integration | ✅ | Workflow orchestration |
| Multi-AI Optimizer | ✅ | Claude + Gemini collaboration |
| Gemini API Mode | ✅ | Dual-mode (CLI + API) |
| FileCheckpointer | ✅ | State persistence |

### Next Steps
- [ ] Explore wasp_ghx examples for learning
- [ ] Discuss Grasshopper background integration with Gemini
- [ ] Plan next development phase

---

## Session Notes

### Gemini API Configuration
- API Key stored in `.env` (local only)
- Auto-detection: uses API if key available
- Fallback to CLI mode

### Quick Commands Available
- `/doc-update [changes]` - Update documentation
- `/log [summary]` - Quick session logging

---

## 2026-01-06 23:10 - Gemini 5-Round Discussion Summary

### Round 1: Background Grasshopper Integration
**問題**: macOS 如何讓 Grasshopper 背景運行？

**結論**: macOS 無法真正 Headless，採用「自動化 TCP 橋接」方案
- 建立 `mcp_server.gh` 自動啟動檔
- Shell Script 開啟 Rhino + 載入檔案
- C# 端避免 Modal Dialog，改用 Log/JSON Error

### Round 2: LangGraph & AI Collaboration
**問題**: LangGraph 整合策略？AI 如何分工？

**建議分工**:
| 環節 | AI | 角色 |
|------|-----|------|
| 幾何拆解 | Claude | Builder |
| 錯誤診斷 | Gemini | Critic |
| 創意發想 | Gemini | Visionary |
| 參數調優 | Claude | Modifier |

**收斂判斷**: 硬指標 (錯誤數、幾何穩定性) + 軟指標 (AI 評分)

### Round 3: Wasp Knowledge Base
**問題**: 如何從 37 個範例學習？

**策略**:
1. Pattern Extractor 解析 .ghx XML
2. 建立 `wasp_patterns.json` 知識庫
3. 三層推薦：頻率/模板/參數預判

### Round 4: 4-Week Roadmap
| Week | Goal | Milestone |
|------|------|-----------|
| 1 | Connectivity | 成功透過 AI 放置組件到 GH |
| 2 | Knowledge | AI 正確識別 50+ 組件 GUID |
| 3 | Feedback | AI 自動修復類型錯誤 |
| 4 | Templates | Wasp 聚合從提示詞生成 |

### Round 5: Risks & Value
**最大風險**: AI State 與 GH 實際狀態脫節

**緩解策略**:
1. 防止 macOS App Nap (NSProcessInfo)
2. Heartbeat 心跳檢測
3. Dry Run 預演驗證
4. 狀態反向同步 (State Re-sync)

**最有價值場景**: 自然語言參數化建模助理
- 語意轉譯需求 → 組件組合
- 自動化繁瑣操作
- 錯誤診斷解釋

---

## Next Actions

1. [ ] 實作 `mcp_server.gh` 自動啟動檔
2. [ ] 修改 `execution.py` 接入真實 `GrasshopperClient`
3. [ ] 建立 Wasp pattern extractor
4. [ ] 實作狀態反向同步機制

---

## 2026-01-06 23:45 - LangGraph + 原始工作流程整合

### Summary
整合原始 AmemiyaLai/grasshopper-mcp-workflow 的 6 步驟工作流程與 LangGraph 狀態機。

### 問題分析
之前的 LangGraph 實作存在以下問題：
1. 跳過 Mermaid 預覽步驟，直接執行
2. 節點只更新狀態，未實際寫入檔案
3. 缺少用戶確認檢查點

### 解決方案
1. **SKILL.md 增強 (v2.0)**
   - 整合 6 步驟工作流程圖
   - 強調「絕對不要跳過 Mermaid 預覽」原則
   - 加入 AI 協作分工表

2. **LangGraph Nodes 增強**
   - `decomposition.py`: 產生 `GH_WIP/part_info.mmd`，暫停等待確認
   - `connectivity.py`: 產生 `GH_WIP/component_info.mmd`，暫停等待確認
   - 新增 `confirm_decomposition_node` 和 `confirm_connectivity_node`

3. **核心原則**
   ```
   檔案優先 → 漸進揭露 → 驗證迴圈 → AI 協作
   ```

### 變更檔案
| 檔案 | 變更 |
|------|------|
| `.claude/skills/grasshopper-workflow/SKILL.md` | 增強為 v2.0 |
| `grasshopper-workflow/SKILL.md` | 同步更新 |
| `grasshopper_mcp/langgraph/nodes/decomposition.py` | 新增檔案寫入、用戶確認 |
| `grasshopper_mcp/langgraph/nodes/connectivity.py` | 新增檔案寫入、用戶確認 |
| `grasshopper_mcp/langgraph/nodes/__init__.py` | 匯出新函數 |

### 工作流程對照
| 原始工作流程 | LangGraph Stage | 產出檔案 |
|-------------|-----------------|----------|
| Step 1: 釐清需求 | requirements | - |
| Step 2: 拆分幾何 | decomposition | `part_info.mmd` |
| Step 3: 規劃連接 | connectivity | `component_info.mmd` |
| Step 4: GUID 查詢 | guid_resolution | 更新 `component_info.mmd` |
| Step 5: 執行 | execution | `placement_info.json` |
| Step 6: 清理 | evaluation | 封存到 `GH_PKG/` |

### AI 協作模式
| 步驟 | Claude | Gemini |
|------|--------|--------|
| Step 2 | 提案 | 評論優化 |
| Step 3 | 規劃 | 完整性檢查 |
| Step 5 | 修復 | 錯誤診斷 |

---

## 2026-01-07 00:15 - 測試驗證與版本控制

### Summary
完成「畫桌子」工作流程的完整測試，驗證 LangGraph + 檔案優先機制正常運作。

### 測試結果
```
通過率: 6/6

✓ test_1: 狀態初始化
✓ test_2: Decomposition 節點（生成 part_info.mmd）
✓ test_3: 用戶確認機制
✓ test_4: Connectivity 節點（生成 component_info.mmd）
✓ test_5: 衝突檢測
✓ test_6: 工作流程整合
```

### 開發思考過程

#### 1. 問題識別
原始 LangGraph 實作的問題：
- 只更新內部狀態，不產出實際檔案
- 用戶無法預覽 Mermaid 圖表
- 缺乏「暫停等待確認」機制

#### 2. 設計決策
採用「檔案優先」原則：
```
狀態更新之前 → 先寫入 .mmd 檔案 → 暫停等待用戶預覽 → 確認後才繼續
```

這解決了 AI 狀態與實際檔案脫節的問題，讓用戶可以：
- 用 Mermaid 預覽工具查看設計
- 手動修改 .mmd 檔案後繼續
- 在任何階段中斷並恢復

#### 3. 實作細節

**模板系統**：根據 topic 關鍵字自動選擇模板
```python
if "桌" in topic or "table" in topic_lower:
    return _generate_table_template()
elif "椅" in topic or "chair" in topic_lower:
    return _generate_chair_template()
else:
    return _generate_default_template()
```

**確認機制**：使用 `awaiting_confirmation` + `pending_decisions` 實現
```python
return {
    "awaiting_confirmation": True,
    "confirmation_reason": "part_info_preview",
    "pending_decisions": [...Decision(question="請預覽...")]
}
```

#### 4. 測試策略
- 單元測試各個節點功能
- 整合測試工作流程從頭到尾
- 驗證檔案實際寫入 GH_WIP/

### Git Commit
```
0f17bdd feat: Enhanced LangGraph workflow with file-first approach v2.0
```

**變更統計**: 7 files, +1629/-338 lines

### 架構優化想法（下一步）

參考用戶分享的「Automated Generation Mechanism」圖：

| 模式 | 適用場景 | 實作方向 |
|------|---------|---------|
| Workflow Mode | 明確需求（如「120x80 桌子」） | 目前的 6 步驟流程 |
| Meta-Agent Mode | 模糊需求（如「有創意的家具」） | 新增 Intent Classifier + Wasp 搜索 |

**混合模式架構**：
1. `classify_intent_node` - 判斷需求明確度
2. 明確 → 直接進入 Workflow Mode
3. 模糊 → Meta-Agent 探索（搜索範例、詢問用戶）後再進入 Workflow

---
