# GH-MCP 智能學習系統架構

## 核心理念

```
.ghx 批量解析 → 知識萃取 → 蘇格拉底對話 → 洞見沉澱 → 知識庫更新
      ↑                                              ↓
      └────────── Gemini 深度分析 ←──────────────────┘
```

## 整體系統流程

```mermaid
flowchart TB
    subgraph Input["📁 輸入層"]
        GHX[(".ghx 文件<br/>(批量)")]
        USER["👤 用戶反饋"]
    end

    subgraph Parser["🔧 Layer 1: GHX Parser"]
        UNZIP["解壓 gzip"]
        XML["解析 XML"]
        EXTRACT["提取組件/連線"]
        GHX --> UNZIP --> XML --> EXTRACT
    end

    subgraph Extractor["🧠 Layer 2: Knowledge Extractor"]
        REG["組件註冊表<br/>(GUID → 參數)"]
        PAT["模式庫<br/>(連線統計)"]
        RPT["洞見報告"]
        EXTRACT --> REG
        EXTRACT --> PAT
        REG --> RPT
        PAT --> RPT
    end

    subgraph Gemini["🔬 Layer 3: Gemini 深度分析"]
        ANALYZE["模式分析"]
        VERIFY_Q["生成驗證問題"]
        SUGGEST["知識更新建議"]
        RPT --> ANALYZE
        ANALYZE --> VERIFY_Q
    end

    subgraph Dialogue["💬 Layer 4: Socratic Dialogue"]
        EXPLORE["探索階段<br/>🔍 Ask Questions"]
        HYPOTHESIZE["假設階段<br/>💡 Form Hypothesis"]
        VERIFY["驗證階段<br/>✅ Verify with User"]
        SYNTHESIZE["總結階段<br/>📝 Synthesize"]

        EXPLORE --> HYPOTHESIZE
        HYPOTHESIZE --> VERIFY
        VERIFY -->|"驗證成功"| SYNTHESIZE
        VERIFY -->|"需要修正"| EXPLORE
        USER --> EXPLORE
    end

    subgraph Output["📚 輸出層"]
        KB["component_registry.json<br/>(知識庫)"]
        PATTERNS["patterns.json<br/>(設計模式)"]
        SESSION["session.json<br/>(對話記錄)"]
    end

    VERIFY_Q --> EXPLORE
    SYNTHESIZE --> KB
    SYNTHESIZE --> PATTERNS
    SYNTHESIZE --> SESSION
    SUGGEST --> KB

    style Input fill:#e1f5fe
    style Parser fill:#fff3e0
    style Extractor fill:#f3e5f5
    style Gemini fill:#e8f5e9
    style Dialogue fill:#fce4ec
    style Output fill:#fffde7
```

---

## 蘇格拉底對話流程詳解

```mermaid
stateDiagram-v2
    [*] --> Exploration: 開始會話

    Exploration --> Exploration: 收集洞見 (< 3)
    Exploration --> Hypothesis: 洞見 >= 3

    Hypothesis --> Verification: 形成假設

    Verification --> Synthesis: 用戶確認 ✓
    Verification --> Exploration: 用戶否定 ✗
    Verification --> Hypothesis: 需要調整

    Synthesis --> [*]: 導出知識

    note right of Exploration
        - 問開放式問題
        - 搜索知識庫
        - 追蹤洞見
    end note

    note right of Hypothesis
        - 從洞見形成假設
        - 生成驗證方法
        - 評估信心度
    end note

    note right of Verification
        - 用戶在 GH 實測
        - 確認或否定
        - 記錄修正
    end note

    note right of Synthesis
        - 總結確認知識
        - 列出待解問題
        - 更新知識庫
    end note
```

---

## 知識萃取流程

```mermaid
flowchart LR
    subgraph Raw["原始數據"]
        A1["file1.ghx"]
        A2["file2.ghx"]
        A3["file3.ghx"]
        AN["..."]
    end

    subgraph Parse["解析結果"]
        B1["components[]"]
        B2["connections[]"]
        B3["groups[]"]
    end

    subgraph Aggregate["聚合統計"]
        C1["GUID → 使用次數"]
        C2["參數名 → 變體列表"]
        C3["連線模式 → 頻率"]
    end

    subgraph Knowledge["知識產出"]
        D1["🎯 確定參數映射<br/>'A' = 'Source'"]
        D2["⚠️ 待驗證假設<br/>'A' ∈ {'Source', 'Plane A'}"]
        D3["📊 設計模式<br/>Point → Curve → Surface"]
    end

    Raw --> Parse --> Aggregate --> Knowledge
```

---

## Claude + Gemini 協作模式

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant C as 🤖 Claude
    participant G as 🔮 Gemini
    participant KB as 📚 Knowledge Base

    U->>C: 開始學習會話
    C->>KB: 載入現有知識
    C->>U: 蘇格拉底式提問

    U->>C: 回答 + 提供 .ghx
    C->>C: 解析 .ghx
    C->>G: 請求模式分析
    G->>C: 返回深度洞見

    C->>U: 形成假設 + 驗證問題
    U->>C: 在 GH 驗證後回報

    alt 假設正確
        C->>KB: 更新確認知識
        C->>U: 繼續下一主題
    else 假設錯誤
        C->>G: 請求調整建議
        G->>C: 返回修正方向
        C->>U: 重新探索
    end

    U->>C: 結束會話
    C->>KB: 保存所有洞見
    C->>U: 輸出總結報告
```

---

## 組件知識結構

```mermaid
erDiagram
    COMPONENT ||--o{ INPUT_PARAM : has
    COMPONENT ||--o{ OUTPUT_PARAM : has
    COMPONENT ||--o{ EXAMPLE_FILE : appears_in

    COMPONENT {
        string guid PK
        string name
        string nickname
        string category
        int usage_count
    }

    INPUT_PARAM {
        string nickname PK
        string[] names
        string[] types
        float confidence
        bool verified
    }

    OUTPUT_PARAM {
        string nickname PK
        string[] names
        string[] types
        float confidence
        bool verified
    }

    EXAMPLE_FILE {
        string path PK
        string context
    }

    DESIGN_PATTERN ||--o{ COMPONENT : uses
    DESIGN_PATTERN {
        string pattern_id PK
        string description
        int frequency
        string[] component_sequence
    }
```

---

## 驗證循環

```mermaid
flowchart TD
    START["發現參數不確定性"] --> GEN["生成驗證問題"]
    GEN --> ASK["詢問用戶"]
    ASK --> TEST["用戶在 GH 測試"]
    TEST --> RESULT{"測試結果"}

    RESULT -->|"確認"| CONFIRM["標記為已驗證<br/>confidence = 1.0"]
    RESULT -->|"否定"| UPDATE["更新正確值<br/>記錄錯誤假設"]
    RESULT -->|"部分正確"| REFINE["細化假設<br/>再次驗證"]

    CONFIRM --> KB["更新知識庫"]
    UPDATE --> KB
    REFINE --> GEN

    KB --> NEXT["下一個不確定項"]
    NEXT --> GEN
```

---

## 目錄結構

```
gh_learning/
├── main.py                    # 主程式入口
├── src/
│   ├── ghx_parser.py          # Layer 1: GHX 解析器
│   ├── knowledge_extractor.py # Layer 2: 知識萃取器
│   ├── gemini_analyzer.py     # Layer 3: Gemini 分析器
│   └── socratic_dialogue.py   # Layer 4: 蘇格拉底對話 (待實作)
├── knowledge/
│   ├── component_registry.json    # 主知識庫
│   ├── extracted_knowledge.json   # 萃取結果
│   └── gemini_analysis.json       # Gemini 分析
├── ghx_samples/               # .ghx 範例文件
│   └── *.ghx
└── docs/
    └── ARCHITECTURE.md        # 本文件
```

---

## 使用方式

```bash
# 解析 .ghx 文件
python main.py parse ./ghx_samples/

# 萃取知識並用 Gemini 分析
python main.py analyze ./ghx_samples/

# 開始學習會話
python main.py learn "Orient 組件參數"

# 解釋特定組件
python main.py explain "Solid Union"
```

---

## 關鍵指標

| 指標           | 目標        | 衡量方式                  |
| -------------- | ----------- | ------------------------- |
| 解析覆蓋率     | > 95%       | 成功解析的 .ghx 數 / 總數 |
| 參數識別準確率 | > 90%       | 驗證正確的參數 / 總參數   |
| 對話效率       | < 5 輪      | 到達驗證的平均輪數        |
| 知識庫增長     | +10 組件/週 | 新增已驗證組件數          |
| 連線成功率     | > 85%       | MCP 連線成功 / 總嘗試     |
