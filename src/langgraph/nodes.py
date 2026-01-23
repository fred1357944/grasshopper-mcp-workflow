"""
LangGraph Nodes
===============
定義流程圖中各節點的處理函數
"""

from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime

from .graph_state import GraphState


# ============================================================
# LLM 設定 (支援 OpenAI 和 Anthropic)
# ============================================================

def get_llm(model_type: str = "anthropic"):
    """
    取得 LLM 實例
    
    Args:
        model_type: "anthropic" 或 "openai"
    """
    if model_type == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.7,
                max_tokens=4096
            )
        except ImportError:
            pass
    
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            max_tokens=4096
        )
    except ImportError:
        pass
    
    return None


# ============================================================
# Node 1: Intent Parser
# ============================================================

INTENT_PARSER_PROMPT = """你是一個 Grasshopper 參數化設計專家。請分析以下設計意圖描述，並提取結構化資訊。

設計意圖描述：
{design_intent}

附加約束：
{constraints}

請以 JSON 格式回答，包含以下欄位：
{{
    "intent_type": "設計意圖類型 (curve_generation | surface_generation | transformation | distribution | pattern_creation | optimization)",
    "core_operations": ["核心操作列表，如 'spiral_movement', 'parametric_curve', 'array_distribution'"],
    "parametric_requirements": [
        {{"name": "參數名稱", "type": "number|curve|point", "description": "說明", "suggested_range": [min, max]}}
    ],
    "matched_intent_patterns": ["匹配的已知模式 ID"],
    "confidence": 0.0-1.0,
    "analysis_notes": "分析說明"
}}

請只回答 JSON，不要其他文字。"""


def parse_intent(state: GraphState) -> GraphState:
    """
    Node 1: 解析設計意圖
    
    分析自然語言描述，識別：
    1. 核心幾何操作
    2. 參數化需求
    3. 設計模式匹配
    """
    design_intent = state.get("design_intent", "")
    constraints = state.get("constraints", [])
    
    # 更新迭代計數
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    
    # 記錄修改歷史
    state["modification_history"] = state.get("modification_history", []) + [
        f"[{datetime.now().isoformat()}] 開始意圖解析 (迭代 {state['iteration_count']})"
    ]
    
    # 取得 LLM
    llm = get_llm()
    
    if llm:
        try:
            prompt = INTENT_PARSER_PROMPT.format(
                design_intent=design_intent,
                constraints="\n".join(f"- {c}" for c in constraints) if constraints else "無"
            )
            
            response = llm.invoke(prompt)
            result = json.loads(response.content)
            
            state["intent_type"] = result.get("intent_type")
            state["core_operations"] = result.get("core_operations", [])
            state["parametric_requirements"] = result.get("parametric_requirements", [])
            state["matched_intent_patterns"] = result.get("matched_intent_patterns", [])
            state["intent_confidence"] = result.get("confidence", 0.5)
            
        except Exception as e:
            # LLM 失敗時使用規則式分析
            state = _rule_based_intent_parsing(state, design_intent)
            state["warnings"] = state.get("warnings", []) + [f"LLM 失敗，使用規則式分析: {str(e)}"]
    else:
        # 沒有 LLM 時使用規則式分析
        state = _rule_based_intent_parsing(state, design_intent)
        state["warnings"] = state.get("warnings", []) + ["未配置 LLM，使用規則式分析"]
    
    return state


def _rule_based_intent_parsing(state: GraphState, design_intent: str) -> GraphState:
    """
    規則式意圖解析（備用方案）

    支援的設計意圖：
    1. 3D 螺旋/helix - 包含高度參數
    2. 2D 螺旋/spiral - 平面螺旋
    3. 圓形陣列 - radial/circular array
    4. 線性陣列 - linear array
    5. 曲線生成 - curve
    6. 曲面生成 - surface/loft
    """
    intent_lower = design_intent.lower()

    # 識別參數化需求 (先識別，用於判斷 2D/3D)
    params = []
    if any(kw in intent_lower for kw in ["圈數", "turns", "rounds", "圈"]):
        params.append({"name": "turns", "type": "number", "suggested_range": [1, 10]})
    if any(kw in intent_lower for kw in ["半徑", "radius", "r"]):
        params.append({"name": "radius", "type": "number", "suggested_range": [5, 100]})
    if any(kw in intent_lower for kw in ["高度", "height", "z", "垂直"]):
        params.append({"name": "height", "type": "number", "suggested_range": [10, 200]})
    if any(kw in intent_lower for kw in ["數量", "count", "個", "steps", "階"]):
        params.append({"name": "count", "type": "number", "suggested_range": [1, 100]})
    if any(kw in intent_lower for kw in ["間距", "spacing", "距離"]):
        params.append({"name": "spacing", "type": "number", "suggested_range": [10, 100]})

    # 檢查是否有高度參數 (用於區分 2D/3D)
    has_height = any(p.get("name") == "height" for p in params)

    # 識別意圖類型
    if any(kw in intent_lower for kw in ["螺旋", "spiral", "helix", "螺線"]):
        state["intent_type"] = "curve_generation"
        if has_height or any(kw in intent_lower for kw in ["3d", "helix", "立體", "樓梯"]):
            state["core_operations"] = ["spiral_movement", "parametric_curve", "3d_helix"]
            state["matched_intent_patterns"] = ["3d_helix"]
            # 確保有高度參數
            if not has_height:
                params.append({"name": "height", "type": "number", "suggested_range": [10, 200]})
        else:
            state["core_operations"] = ["spiral_movement", "parametric_curve"]
            state["matched_intent_patterns"] = ["2d_spiral"]

    elif any(kw in intent_lower for kw in ["圓形陣列", "radial", "circular array", "環形"]):
        state["intent_type"] = "distribution"
        state["core_operations"] = ["radial_array", "array_distribution"]
        state["matched_intent_patterns"] = ["radial_array"]

    elif any(kw in intent_lower for kw in ["陣列", "array", "複製", "copy", "線性"]):
        state["intent_type"] = "distribution"
        state["core_operations"] = ["linear_array", "array_distribution"]
        state["matched_intent_patterns"] = ["linear_array"]

    elif any(kw in intent_lower for kw in ["曲線", "curve", "line"]):
        state["intent_type"] = "curve_generation"
        state["core_operations"] = ["parametric_curve"]
        state["matched_intent_patterns"] = ["parametric_curve"]

    elif any(kw in intent_lower for kw in ["曲面", "surface", "loft"]):
        state["intent_type"] = "surface_generation"
        state["core_operations"] = ["surface_creation"]
        state["matched_intent_patterns"] = ["surface_loft"]

    else:
        state["intent_type"] = "unknown"
        state["core_operations"] = []
        state["matched_intent_patterns"] = []

    state["parametric_requirements"] = params
    state["intent_confidence"] = 0.7 if state["intent_type"] != "unknown" else 0.3

    return state


# ============================================================
# Node 2: Mermaid Generator
# ============================================================

MERMAID_GENERATOR_PROMPT = """你是一個 Grasshopper 參數化設計專家。請根據以下設計意圖分析結果，生成 Mermaid 流程圖。

設計意圖類型: {intent_type}
核心操作: {core_operations}
參數化需求: {parametric_requirements}
匹配模式: {matched_patterns}

請生成一個 Mermaid flowchart (使用 graph LR 或 graph TD)，表示 Grasshopper 元件之間的連接流程。

要求：
1. 每個節點應該對應一個 Grasshopper 元件
2. 使用有意義的節點 ID 和標籤
3. 標註資料流向
4. 標記輸入參數 (Slider) 和輸出結果

請只回答 Mermaid 代碼，用 ```mermaid 和 ``` 包圍。"""


def generate_mermaid(state: GraphState) -> GraphState:
    """
    Node 2: 生成 Mermaid 流程圖
    
    將解析後的意圖轉為 Mermaid 流程圖
    """
    llm = get_llm()
    
    state["modification_history"] = state.get("modification_history", []) + [
        f"[{datetime.now().isoformat()}] 生成 Mermaid 流程圖"
    ]
    
    if llm:
        try:
            prompt = MERMAID_GENERATOR_PROMPT.format(
                intent_type=state.get("intent_type", "unknown"),
                core_operations=state.get("core_operations", []),
                parametric_requirements=state.get("parametric_requirements", []),
                matched_patterns=state.get("matched_intent_patterns", [])
            )
            
            response = llm.invoke(prompt)
            content = response.content
            
            # 提取 Mermaid 代碼
            if "```mermaid" in content:
                mermaid_code = content.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in content:
                mermaid_code = content.split("```")[1].split("```")[0].strip()
            else:
                mermaid_code = content.strip()
            
            state["mermaid_graph"] = mermaid_code
            
        except Exception as e:
            state = _rule_based_mermaid_generation(state)
            state["warnings"] = state.get("warnings", []) + [f"LLM 失敗，使用規則式生成: {str(e)}"]
    else:
        state = _rule_based_mermaid_generation(state)
    
    return state


def _rule_based_mermaid_generation(state: GraphState) -> GraphState:
    """規則式 Mermaid 生成（備用方案）"""
    intent_type = state.get("intent_type", "unknown")
    params = state.get("parametric_requirements", [])
    
    # 基於意圖類型生成模板
    if intent_type == "curve_generation" and "spiral_movement" in state.get("core_operations", []):
        # 螺旋曲線模板
        mermaid = """graph LR
    subgraph Inputs
        S1[/"圈數 Slider"/]
        S2[/"半徑 Slider"/]
        S3[/"高度 Slider"/]
    end
    
    subgraph Processing
        SER[Series] --> SIN[Sin]
        SER --> COS[Cos]
        SIN --> |X| PT[Construct Point]
        COS --> |Y| PT
        S3 --> |Z| PT
    end
    
    subgraph Output
        PT --> INT[Interpolate Curve]
        INT --> OUT((曲線輸出))
    end
    
    S1 --> SER
    S2 --> |Scale| SIN
    S2 --> |Scale| COS"""
    
    elif intent_type == "distribution":
        mermaid = """graph LR
    subgraph Inputs
        GEO[/"幾何輸入"/]
        COUNT[/"數量 Slider"/]
        STEP[/"間距 Slider"/]
    end
    
    GEO --> ARR[Linear Array]
    COUNT --> ARR
    STEP --> ARR
    ARR --> OUT((陣列輸出))"""
    
    else:
        # 通用模板
        mermaid = """graph LR
    INPUT[/"輸入參數"/] --> PROCESS[處理]
    PROCESS --> OUTPUT((輸出))"""
    
    state["mermaid_graph"] = mermaid
    return state


# ============================================================
# Node 3: GH Code Generator
# ============================================================

GH_CODE_GENERATOR_PROMPT = """你是一個 Grasshopper 參數化設計專家。請根據以下 Mermaid 流程圖，生成 Grasshopper 元件定義。

Mermaid 流程圖:
{mermaid_graph}

設計意圖: {design_intent}
參數化需求: {parametric_requirements}

請以 JSON 格式回答，包含以下結構：
{{
    "components": [
        {{
            "id": "唯一 ID",
            "type": "元件類型名稱 (如 Number Slider, Series, Sin, Construct Point 等)",
            "nickname": "元件暱稱",
            "position": [x, y],
            "properties": {{}}
        }}
    ],
    "connections": [
        {{
            "from": {{"component": "來源元件 ID", "output": "輸出名稱或索引"}},
            "to": {{"component": "目標元件 ID", "input": "輸入名稱或索引"}}
        }}
    ],
    "sliders": [
        {{
            "id": "Slider ID",
            "name": "參數名稱",
            "min": 0,
            "max": 100,
            "default": 50
        }}
    ]
}}

請只回答 JSON，不要其他文字。確保元件類型使用正確的 Grasshopper 元件名稱。"""


def generate_gh_code(state: GraphState) -> GraphState:
    """
    Node 3: 生成 GH Code
    
    將 Mermaid 流程圖轉為 Grasshopper 元件定義
    """
    llm = get_llm()
    
    state["modification_history"] = state.get("modification_history", []) + [
        f"[{datetime.now().isoformat()}] 生成 GH Code"
    ]
    
    if llm:
        try:
            prompt = GH_CODE_GENERATOR_PROMPT.format(
                mermaid_graph=state.get("mermaid_graph", ""),
                design_intent=state.get("design_intent", ""),
                parametric_requirements=json.dumps(
                    state.get("parametric_requirements", []), 
                    ensure_ascii=False
                )
            )
            
            response = llm.invoke(prompt)
            content = response.content
            
            # 提取 JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            gh_code = json.loads(json_str)
            state["gh_code"] = gh_code
            state["components_used"] = [c["type"] for c in gh_code.get("components", [])]
            state["connections_defined"] = gh_code.get("connections", [])
            
        except Exception as e:
            state = _rule_based_gh_code_generation(state)
            state["warnings"] = state.get("warnings", []) + [f"LLM 失敗，使用規則式生成: {str(e)}"]
    else:
        state = _rule_based_gh_code_generation(state)
    
    return state


def _rule_based_gh_code_generation(state: GraphState) -> GraphState:
    """
    規則式 GH Code 生成（備用方案）

    支援的設計模式：
    1. 3D 螺旋曲線 (helix) - 包含 X, Y, Z 座標
    2. 2D 螺旋曲線 (spiral) - 僅 X, Y 座標
    3. 陣列分布 (array distribution)
    4. 圓形陣列 (radial array)
    """
    intent_type = state.get("intent_type", "unknown")
    core_ops = state.get("core_operations", [])
    params = state.get("parametric_requirements", [])

    # 檢查是否需要 3D (有高度參數)
    has_height = any(p.get("name") in ["height", "高度", "z"] for p in params)

    if intent_type == "curve_generation" and "spiral_movement" in core_ops:
        if has_height:
            # 3D 螺旋曲線 (Helix) - 帶有 Z 座標
            gh_code = _generate_3d_helix_template()
        else:
            # 2D 螺旋曲線 (Spiral)
            gh_code = _generate_2d_spiral_template()

    elif intent_type == "distribution":
        if "radial" in " ".join(core_ops).lower():
            # 圓形陣列
            gh_code = _generate_radial_array_template()
        else:
            # 線性陣列
            gh_code = _generate_linear_array_template()

    elif intent_type == "curve_generation":
        # 通用參數化曲線
        gh_code = _generate_parametric_curve_template()

    else:
        # 通用空模板
        gh_code = {
            "components": [],
            "connections": [],
            "sliders": []
        }

    state["gh_code"] = gh_code
    state["components_used"] = [c["type"] for c in gh_code.get("components", [])]
    state["connections_defined"] = gh_code.get("connections", [])

    return state


def _generate_3d_helix_template() -> Dict[str, Any]:
    """
    3D 螺旋曲線模板

    數學模型:
    - t = 0 to 2π × turns
    - x = radius × cos(t)
    - y = radius × sin(t)
    - z = t / (2π × turns) × height
    """
    return {
        "components": [
            # Sliders
            {"id": "slider_turns", "type": "Number Slider", "nickname": "Turns",
             "position": [50, 50], "properties": {"min": 1, "max": 10, "value": 3}},
            {"id": "slider_radius", "type": "Number Slider", "nickname": "Radius",
             "position": [50, 130], "properties": {"min": 5, "max": 100, "value": 30}},
            {"id": "slider_height", "type": "Number Slider", "nickname": "Height",
             "position": [50, 210], "properties": {"min": 10, "max": 200, "value": 50}},
            {"id": "slider_points", "type": "Number Slider", "nickname": "Points",
             "position": [50, 290], "properties": {"min": 20, "max": 200, "value": 60}},

            # 產生序列 t (0 到 2π×turns)
            {"id": "const_2pi", "type": "Number", "nickname": "TwoPi",
             "position": [200, 50], "properties": {"value": 6.28318}},
            {"id": "mul_angle", "type": "Multiplication", "nickname": "TotalAngle",
             "position": [350, 50], "properties": {}},
            {"id": "series", "type": "Series", "nickname": "T",
             "position": [500, 130], "properties": {}},

            # 計算 X = R × cos(t)
            {"id": "cos", "type": "Cosine", "nickname": "Cos",
             "position": [650, 80], "properties": {}},
            {"id": "mul_x", "type": "Multiplication", "nickname": "X",
             "position": [800, 80], "properties": {}},

            # 計算 Y = R × sin(t)
            {"id": "sin", "type": "Sine", "nickname": "Sin",
             "position": [650, 180], "properties": {}},
            {"id": "mul_y", "type": "Multiplication", "nickname": "Y",
             "position": [800, 180], "properties": {}},

            # 計算 Z = t / TotalAngle × Height
            {"id": "div_z", "type": "Division", "nickname": "ZRatio",
             "position": [650, 280], "properties": {}},
            {"id": "mul_z", "type": "Multiplication", "nickname": "Z",
             "position": [800, 280], "properties": {}},

            # 組合成點
            {"id": "pt", "type": "Construct Point", "nickname": "Pt",
             "position": [950, 180], "properties": {}},

            # 插值曲線
            {"id": "interp", "type": "Interpolate", "nickname": "Helix",
             "position": [1100, 180], "properties": {}},
        ],
        "connections": [
            # TotalAngle = 2π × Turns
            {"from": {"component": "const_2pi", "output": 0},
             "to": {"component": "mul_angle", "input": 0}},
            {"from": {"component": "slider_turns", "output": 0},
             "to": {"component": "mul_angle", "input": 1}},

            # Series: Step = TotalAngle/Points, Count = Points
            {"from": {"component": "mul_angle", "output": 0},
             "to": {"component": "series", "input": "N"}},  # Step
            {"from": {"component": "slider_points", "output": 0},
             "to": {"component": "series", "input": "C"}},  # Count

            # X = Radius × cos(t)
            {"from": {"component": "series", "output": 0},
             "to": {"component": "cos", "input": 0}},
            {"from": {"component": "cos", "output": 0},
             "to": {"component": "mul_x", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_x", "input": 1}},

            # Y = Radius × sin(t)
            {"from": {"component": "series", "output": 0},
             "to": {"component": "sin", "input": 0}},
            {"from": {"component": "sin", "output": 0},
             "to": {"component": "mul_y", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_y", "input": 1}},

            # Z = (t / TotalAngle) × Height
            {"from": {"component": "series", "output": 0},
             "to": {"component": "div_z", "input": 0}},
            {"from": {"component": "mul_angle", "output": 0},
             "to": {"component": "div_z", "input": 1}},
            {"from": {"component": "div_z", "output": 0},
             "to": {"component": "mul_z", "input": 0}},
            {"from": {"component": "slider_height", "output": 0},
             "to": {"component": "mul_z", "input": 1}},

            # Construct Point (X, Y, Z)
            {"from": {"component": "mul_x", "output": 0},
             "to": {"component": "pt", "input": "X"}},
            {"from": {"component": "mul_y", "output": 0},
             "to": {"component": "pt", "input": "Y"}},
            {"from": {"component": "mul_z", "output": 0},
             "to": {"component": "pt", "input": "Z"}},

            # Interpolate Curve
            {"from": {"component": "pt", "output": 0},
             "to": {"component": "interp", "input": 0}},
        ],
        "sliders": [
            {"id": "slider_turns", "name": "圈數", "min": 1, "max": 10, "default": 3},
            {"id": "slider_radius", "name": "半徑", "min": 5, "max": 100, "default": 30},
            {"id": "slider_height", "name": "高度", "min": 10, "max": 200, "default": 50},
            {"id": "slider_points", "name": "點數", "min": 20, "max": 200, "default": 60},
        ]
    }


def _generate_2d_spiral_template() -> Dict[str, Any]:
    """2D 螺旋曲線模板 (原有功能)"""
    return {
        "components": [
            {"id": "slider_turns", "type": "Number Slider", "nickname": "Turns",
             "position": [50, 100], "properties": {"min": 1, "max": 10, "value": 3}},
            {"id": "slider_radius", "type": "Number Slider", "nickname": "Radius",
             "position": [50, 150], "properties": {"min": 1, "max": 50, "value": 10}},
            {"id": "series", "type": "Series", "nickname": "Series",
             "position": [200, 100], "properties": {}},
            {"id": "sin", "type": "Sine", "nickname": "Sin",
             "position": [350, 80], "properties": {}},
            {"id": "cos", "type": "Cosine", "nickname": "Cos",
             "position": [350, 120], "properties": {}},
            {"id": "mul_x", "type": "Multiplication", "nickname": "MulX",
             "position": [450, 80], "properties": {}},
            {"id": "mul_y", "type": "Multiplication", "nickname": "MulY",
             "position": [450, 120], "properties": {}},
            {"id": "pt", "type": "Construct Point", "nickname": "Pt",
             "position": [550, 100], "properties": {}},
            {"id": "interp", "type": "Interpolate", "nickname": "IntCrv",
             "position": [700, 100], "properties": {}},
        ],
        "connections": [
            {"from": {"component": "slider_turns", "output": 0},
             "to": {"component": "series", "input": "C"}},
            {"from": {"component": "series", "output": 0},
             "to": {"component": "sin", "input": 0}},
            {"from": {"component": "series", "output": 0},
             "to": {"component": "cos", "input": 0}},
            {"from": {"component": "sin", "output": 0},
             "to": {"component": "mul_x", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_x", "input": 1}},
            {"from": {"component": "cos", "output": 0},
             "to": {"component": "mul_y", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_y", "input": 1}},
            {"from": {"component": "mul_x", "output": 0},
             "to": {"component": "pt", "input": "X"}},
            {"from": {"component": "mul_y", "output": 0},
             "to": {"component": "pt", "input": "Y"}},
            {"from": {"component": "pt", "output": 0},
             "to": {"component": "interp", "input": 0}},
        ],
        "sliders": [
            {"id": "slider_turns", "name": "圈數", "min": 1, "max": 10, "default": 3},
            {"id": "slider_radius", "name": "半徑", "min": 1, "max": 50, "default": 10},
        ]
    }


def _generate_linear_array_template() -> Dict[str, Any]:
    """線性陣列模板"""
    return {
        "components": [
            {"id": "slider_count", "type": "Number Slider", "nickname": "Count",
             "position": [50, 100], "properties": {"min": 2, "max": 20, "value": 5}},
            {"id": "slider_spacing", "type": "Number Slider", "nickname": "Spacing",
             "position": [50, 180], "properties": {"min": 10, "max": 100, "value": 30}},
            {"id": "series", "type": "Series", "nickname": "Series",
             "position": [200, 100], "properties": {}},
            {"id": "mul", "type": "Multiplication", "nickname": "Distances",
             "position": [350, 100], "properties": {}},
            {"id": "unit_x", "type": "Unit X", "nickname": "UnitX",
             "position": [350, 180], "properties": {}},
            {"id": "mul_vec", "type": "Multiplication", "nickname": "Vectors",
             "position": [500, 140], "properties": {}},
        ],
        "connections": [
            {"from": {"component": "slider_count", "output": 0},
             "to": {"component": "series", "input": "C"}},
            {"from": {"component": "series", "output": 0},
             "to": {"component": "mul", "input": 0}},
            {"from": {"component": "slider_spacing", "output": 0},
             "to": {"component": "mul", "input": 1}},
            {"from": {"component": "mul", "output": 0},
             "to": {"component": "mul_vec", "input": 0}},
            {"from": {"component": "unit_x", "output": 0},
             "to": {"component": "mul_vec", "input": 1}},
        ],
        "sliders": [
            {"id": "slider_count", "name": "數量", "min": 2, "max": 20, "default": 5},
            {"id": "slider_spacing", "name": "間距", "min": 10, "max": 100, "default": 30},
        ]
    }


def _generate_radial_array_template() -> Dict[str, Any]:
    """圓形陣列模板"""
    return {
        "components": [
            {"id": "slider_count", "type": "Number Slider", "nickname": "Count",
             "position": [50, 100], "properties": {"min": 3, "max": 36, "value": 8}},
            {"id": "slider_radius", "type": "Number Slider", "nickname": "Radius",
             "position": [50, 180], "properties": {"min": 10, "max": 100, "value": 50}},
            {"id": "const_360", "type": "Number", "nickname": "Num360",
             "position": [200, 50], "properties": {"value": 360}},
            {"id": "div", "type": "Division", "nickname": "AngleStep",
             "position": [350, 80], "properties": {}},
            {"id": "series", "type": "Series", "nickname": "Angles",
             "position": [500, 100], "properties": {}},
            {"id": "radians", "type": "Radians", "nickname": "Rads",
             "position": [650, 100], "properties": {}},
            {"id": "sin", "type": "Sine", "nickname": "Sin",
             "position": [800, 80], "properties": {}},
            {"id": "cos", "type": "Cosine", "nickname": "Cos",
             "position": [800, 160], "properties": {}},
            {"id": "mul_x", "type": "Multiplication", "nickname": "X",
             "position": [950, 80], "properties": {}},
            {"id": "mul_y", "type": "Multiplication", "nickname": "Y",
             "position": [950, 160], "properties": {}},
            {"id": "pt", "type": "Construct Point", "nickname": "Points",
             "position": [1100, 120], "properties": {}},
        ],
        "connections": [
            {"from": {"component": "const_360", "output": 0},
             "to": {"component": "div", "input": 0}},
            {"from": {"component": "slider_count", "output": 0},
             "to": {"component": "div", "input": 1}},
            {"from": {"component": "div", "output": 0},
             "to": {"component": "series", "input": "N"}},
            {"from": {"component": "slider_count", "output": 0},
             "to": {"component": "series", "input": "C"}},
            {"from": {"component": "series", "output": 0},
             "to": {"component": "radians", "input": 0}},
            {"from": {"component": "radians", "output": 0},
             "to": {"component": "sin", "input": 0}},
            {"from": {"component": "radians", "output": 0},
             "to": {"component": "cos", "input": 0}},
            {"from": {"component": "cos", "output": 0},
             "to": {"component": "mul_x", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_x", "input": 1}},
            {"from": {"component": "sin", "output": 0},
             "to": {"component": "mul_y", "input": 0}},
            {"from": {"component": "slider_radius", "output": 0},
             "to": {"component": "mul_y", "input": 1}},
            {"from": {"component": "mul_x", "output": 0},
             "to": {"component": "pt", "input": "X"}},
            {"from": {"component": "mul_y", "output": 0},
             "to": {"component": "pt", "input": "Y"}},
        ],
        "sliders": [
            {"id": "slider_count", "name": "數量", "min": 3, "max": 36, "default": 8},
            {"id": "slider_radius", "name": "半徑", "min": 10, "max": 100, "default": 50},
        ]
    }


def _generate_parametric_curve_template() -> Dict[str, Any]:
    """通用參數化曲線模板"""
    return {
        "components": [
            {"id": "slider_count", "type": "Number Slider", "nickname": "Count",
             "position": [50, 100], "properties": {"min": 10, "max": 100, "value": 30}},
            {"id": "series", "type": "Series", "nickname": "T",
             "position": [200, 100], "properties": {}},
            {"id": "pt", "type": "Construct Point", "nickname": "Pt",
             "position": [400, 100], "properties": {}},
            {"id": "interp", "type": "Interpolate", "nickname": "Curve",
             "position": [550, 100], "properties": {}},
        ],
        "connections": [
            {"from": {"component": "slider_count", "output": 0},
             "to": {"component": "series", "input": "C"}},
            {"from": {"component": "series", "output": 0},
             "to": {"component": "pt", "input": "X"}},
            {"from": {"component": "pt", "output": 0},
             "to": {"component": "interp", "input": 0}},
        ],
        "sliders": [
            {"id": "slider_count", "name": "點數", "min": 10, "max": 100, "default": 30},
        ]
    }


# ============================================================
# Node 4: Elegance Evaluator
# ============================================================

ELEGANCE_WEIGHTS = {
    "slider_count": 0.20,
    "data_tree_complexity": 0.15,
    "component_efficiency": 0.15,
    "pattern_match": 0.25,
    "geometric_coupling": 0.25,
}


def evaluate_elegance(state: GraphState) -> GraphState:
    """
    Node 4: 評估優雅度
    
    評估方案的優雅度，決定下一步動作
    """
    gh_code = state.get("gh_code", {})
    components = gh_code.get("components", [])
    sliders = gh_code.get("sliders", [])
    connections = gh_code.get("connections", [])
    
    state["modification_history"] = state.get("modification_history", []) + [
        f"[{datetime.now().isoformat()}] 評估優雅度"
    ]
    
    scores = {}
    issues = []
    suggestions = []
    
    # 1. Slider 數量評估
    slider_count = len(sliders)
    if slider_count <= 3:
        scores["slider_count"] = 1.0
    elif slider_count <= 5:
        scores["slider_count"] = 0.8
    elif slider_count <= 8:
        scores["slider_count"] = 0.5
        issues.append(f"Slider 數量較多 ({slider_count})")
        suggestions.append("考慮合併相關參數或使用 Expression 元件")
    else:
        scores["slider_count"] = 0.3
        issues.append(f"Slider 數量過多 ({slider_count})")
        suggestions.append("使用 Gene Pool 或 Expression 減少 Slider 數量")
    
    # 2. 元件效率評估
    component_count = len(components)
    if component_count == 0:
        scores["component_efficiency"] = 0.0
        issues.append("沒有生成任何元件")
    else:
        # 計算連接密度
        connection_density = len(connections) / max(1, component_count)
        if connection_density >= 0.8:
            scores["component_efficiency"] = 1.0
        elif connection_density >= 0.5:
            scores["component_efficiency"] = 0.7
        else:
            scores["component_efficiency"] = 0.4
            issues.append("元件連接密度較低，可能存在孤立元件")
    
    # 3. 模式匹配評估
    matched_patterns = state.get("matched_intent_patterns", [])
    if matched_patterns:
        scores["pattern_match"] = min(1.0, len(matched_patterns) * 0.3 + 0.4)
    else:
        scores["pattern_match"] = 0.5
        suggestions.append("考慮使用已知的優雅模式")
    
    # 4. 幾何耦合度評估 (簡化版)
    component_types = [c.get("type", "").lower() for c in components]
    elegant_components = ["graph mapper", "remap", "evaluate", "expression"]
    basic_components = ["number slider", "panel"]
    
    elegant_count = sum(1 for t in component_types 
                       if any(e in t for e in elegant_components))
    basic_count = sum(1 for t in component_types 
                     if any(b in t for b in basic_components))
    
    if component_count > 0:
        elegance_ratio = elegant_count / component_count
        scores["geometric_coupling"] = 0.5 + elegance_ratio * 0.5
    else:
        scores["geometric_coupling"] = 0.5
    
    # 5. DataTree 複雜度 (簡化 - 檢查是否有 Graft/Flatten)
    datatree_components = ["graft", "flatten", "partition", "path mapper"]
    datatree_count = sum(1 for t in component_types 
                        if any(d in t for d in datatree_components))
    
    if datatree_count == 0:
        scores["data_tree_complexity"] = 1.0
    elif datatree_count <= 2:
        scores["data_tree_complexity"] = 0.8
    else:
        scores["data_tree_complexity"] = 0.5
        issues.append("DataTree 操作較多，可能增加複雜度")
    
    # 計算總分
    total_score = sum(
        scores.get(metric, 0.5) * weight 
        for metric, weight in ELEGANCE_WEIGHTS.items()
    )
    
    state["elegance_score"] = round(total_score, 3)
    state["elegance_breakdown"] = scores
    state["issues"] = issues
    state["suggestions"] = suggestions
    
    # 記錄評估歷史
    critique = {
        "iteration": state.get("iteration_count", 0),
        "score": total_score,
        "breakdown": scores,
        "issues": issues,
        "suggestions": suggestions,
        "timestamp": datetime.now().isoformat()
    }
    state["critique_history"] = state.get("critique_history", []) + [critique]
    
    # 決定下一步動作
    threshold = state.get("acceptance_threshold", 0.8)
    max_iter = state.get("max_iterations", 5)
    current_iter = state.get("iteration_count", 0)
    
    if total_score >= threshold:
        state["next_action"] = "accept"
    elif current_iter >= max_iter:
        state["next_action"] = "accept"
        state["warnings"] = state.get("warnings", []) + [
            f"達到最大迭代次數 ({max_iter})，接受當前方案"
        ]
    elif not gh_code or not components:
        state["next_action"] = "refine_intent"
    elif "slider" in " ".join(issues).lower():
        state["next_action"] = "refine_gh"
    else:
        state["next_action"] = "refine_gh"
    
    return state


# ============================================================
# 輔助節點
# ============================================================

def error_handler(state: GraphState) -> GraphState:
    """錯誤處理節點"""
    state["has_error"] = True
    state["next_action"] = "accept"  # 發生錯誤時停止迭代
    return state


def human_review_checkpoint(state: GraphState) -> GraphState:
    """
    人工審核檢查點 (可選)
    
    在關鍵決策點暫停，等待使用者確認
    """
    # 這個節點在實際應用中會暫停執行，等待外部輸入
    # 這裡只是標記需要人工審核
    state["warnings"] = state.get("warnings", []) + ["等待人工審核"]
    return state
