#!/usr/bin/env python3
"""
Semantic Review Prompt - LLM 語義審查提示詞
=============================================

核心理念：
    與其用 hardcoded 規則驗證語義，不如讓 LLM 自己審查配置。
    LLM 理解語義的能力可以處理未知情況，規則庫永遠無法完備。

用法：
    在 Phase 4.6 (Semantic Review) 階段，生成提示詞讓 Claude 審查配置。

2026-01-24
"""

from typing import Dict, List
import json


def generate_semantic_review_prompt(placement_info: Dict) -> str:
    """
    生成讓 Claude 進行語義審查的提示詞

    流程：
    1. 提供配置的完整內容
    2. 提供組件行為的關鍵提示
    3. 要求 Claude 分析資料流
    4. 要求 Claude 識別潛在風險
    """

    components = placement_info.get("components", [])
    connections = placement_info.get("connections", [])
    meta = placement_info.get("_meta", {})

    # 構建組件摘要
    component_summary = []
    for comp in components:
        comp_type = comp.get("type", "Unknown")
        nickname = comp.get("nickname", comp.get("id", ""))
        props = comp.get("properties", {})

        if props:
            props_str = ", ".join(f"{k}={v}" for k, v in props.items())
            component_summary.append(f"- {nickname} ({comp_type}): {props_str}")
        else:
            component_summary.append(f"- {nickname} ({comp_type})")

    # 構建連接摘要
    connection_summary = []
    for conn in connections:
        from_comp = conn.get("from", "")
        to_comp = conn.get("to", "")
        from_param = conn.get("from_param", conn.get("from_param_index", "?"))
        to_param = conn.get("to_param", conn.get("to_param_index", "?"))
        connection_summary.append(f"- {from_comp}.{from_param} → {to_comp}.{to_param}")

    prompt = f"""## 🧠 Grasshopper 配置語義審查

請審查以下 Grasshopper 配置，識別潛在的語義問題。

### 配置信息

**名稱**: {meta.get("name", "Unknown")}
**描述**: {meta.get("description", "無描述")}

### 組件列表

{chr(10).join(component_summary)}

### 連接關係

{chr(10).join(connection_summary)}

---

### 審查要點

請針對以下問題進行分析：

1. **組件行為理解**
   - 每個組件的輸入/輸出是什麼？
   - 組件的參數語義是否正確理解？
     - 例如：Mesh Box 的 X/Y/Z 是「細分數量」還是「尺寸」？
     - 例如：Series 的 N 是「數量」還是「步長」？

2. **資料流分析**
   - 追蹤資料從輸入到輸出的流向
   - 估算每個節點的輸出數量
   - 是否有「資料爆炸」風險？
     - 例如：10×10×10 細分會產生多少個面？
     - 這些面流向後續組件會產生什麼影響？

3. **模式正確性**
   - 使用的組件組合是否符合最佳實踐？
   - 有沒有更簡單或更可靠的替代方案？
     - 例如：WASP 通常用 Center Box + Deconstruct Brep，而非 Mesh Box

4. **潛在問題**
   - 有沒有未連接的必要輸入？
   - 參數值是否在合理範圍？
   - 會不會導致 Rhino/Grasshopper 崩潰？

---

### 輸出格式

請按以下格式回覆：

```
## 語義審查結果

### 資料流追蹤
[描述資料從輸入到輸出的流向，估算每個節點的輸出數量]

### 🔴 Critical 問題
[可能導致崩潰或完全錯誤的結果]

### 🟡 Warning
[不推薦但可以運作的配置]

### ✅ 確認事項
[需要使用者確認的設計決策]

### 建議
[如何改進配置]

### 結論
✅ 通過 / ⚠️ 有風險 / ❌ 需要修改
```

請開始審查。
"""

    return prompt


def generate_quick_check_prompt(components: List[Dict]) -> str:
    """
    生成快速組件行為檢查提示詞

    用於在 Phase 3 (組件規劃) 階段預先檢查
    """

    comp_types = set(c.get("type", "") for c in components)

    prompt = f"""## 快速組件行為檢查

我計劃使用以下 Grasshopper 組件：

{chr(10).join(f"- {t}" for t in comp_types if t)}

請簡要說明每個組件的：
1. 輸入參數的「真正含義」（例如：X 是尺寸還是數量？）
2. 輸出數量（1:1 還是 1:N？）
3. 常見誤用

格式：
```
**組件名**:
- 輸入：[參數名] = [含義]
- 輸出數量：[1:1 / 1:N / 說明]
- 注意：[常見誤用]
```
"""

    return prompt


def generate_dataflow_trace_prompt(placement_info: Dict) -> str:
    """
    生成資料流追蹤提示詞

    專注於估算每個節點的輸出數量
    """

    components = placement_info.get("components", [])
    connections = placement_info.get("connections", [])

    # 找出輸入組件（Slider, Panel, Toggle）
    input_comps = []
    for comp in components:
        comp_type = comp.get("type", "")
        if any(t in comp_type for t in ["Slider", "Panel", "Toggle"]):
            nickname = comp.get("nickname", "")
            value = comp.get("properties", {}).get("value", "?")
            input_comps.append(f"- {nickname}: {value}")

    prompt = f"""## 資料流追蹤分析

請追蹤這個 Grasshopper 配置的資料流，估算每個節點的輸出數量。

### 輸入值
{chr(10).join(input_comps) if input_comps else "- 無明確輸入值"}

### 組件連接
{json.dumps(connections, indent=2, ensure_ascii=False)}

### 分析要求

1. 從輸入開始，追蹤資料流經過每個組件
2. 估算每個組件的輸出數量
3. 標記可能的「爆炸點」（輸出數量 > 100）

### 輸出格式

```
【資料流追蹤】

輸入 → 組件1 → 組件2 → ... → 輸出

組件1: 輸入 X 個 → 輸出 Y 個
組件2: 輸入 Y 個 → 輸出 Z 個
...

【爆炸風險】
⚠️ 組件X: 預計輸出 1000+ 個
```
"""

    return prompt


if __name__ == "__main__":
    # 示範用法
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            config = json.load(f)

        prompt = generate_semantic_review_prompt(config)
        print(prompt)
    else:
        print("Usage: python semantic_review_prompt.py <placement_info.json>")
