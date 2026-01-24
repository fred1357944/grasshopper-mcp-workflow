#!/bin/bash
# GH_MCP 關鍵知識 - 每次對話開始時載入
# 解決 compaction 後遺忘的問題

cat << 'EOF'
=== GH_MCP 關鍵知識 (SessionStart) ===

【MCP 命令】
  ✅ 正確: clear_document, add_component, connect_components
  ❌ 錯誤: clear_canvas (不存在！用 clear_document)

【Slider 設定順序】
  1. 先設 min/max: set_slider_properties(id, min=0, max=720)
  2. 再設 value:   set_slider_properties(id, value=360)
  ⚠️ 預設範圍 0-1，value 會被 clamp

【Panel vs Slider】
  ❌ Panel 輸出文字，不能傳給數學組件
  ✅ 常數用 Number Slider，不是 Panel

【衝突組件 - 必須用 GUID】
  Rotate: 19c70daf-600f-4697-ace2-567f6702144d
  Pipe:   1ee25749-2e2d-4fc6-9209-0ea0515081f9
  Series: 651c4fa5-dff4-4be6-ba31-6dc267d3ab47
  Line:   31957fba-b08b-45f9-9ec0-5f9e52d3236b

【FuzzyMatcher 風險參數】
  R, N, P, C, V, GEO, CEN, UP
  → 用 fromParamIndex 替代 fromParam

【WASP 注意事項】
  - Part Name 必須用 Panel 且有內容
  - Connection 需要 Mesh 輸入，不是 Brep
  - R 參數會被誤解為 Radius，用 index

============================================
EOF
