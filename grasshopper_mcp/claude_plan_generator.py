#!/usr/bin/env python3
"""
Claude Plan Generator - Layer 2 計畫生成器
==========================================

當 Golden Knowledge 不完全匹配時，用單次 Claude 調用生成執行計畫。

關鍵設計:
- 知識注入: 將 triplets + patterns + GUIDs 注入 prompt
- 結構化輸出: 要求 Claude 輸出 JSON 格式的 placement_info
- 一次完成: 不做多輪對話，一次生成完整計畫

Usage:
    from grasshopper_mcp import ClaudePlanGenerator

    generator = ClaudePlanGenerator()
    plan = generator.generate(
        user_input="做一個 10x10 的網格結構",
        partial_knowledge=knowledge
    )
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


@dataclass
class ExecutionPlan:
    """執行計畫"""
    success: bool
    placement_info: Optional[Dict] = None
    components: List[Dict] = field(default_factory=list)
    connections: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generation_context: Dict = field(default_factory=dict)

    # Mermaid 相關屬性
    description: str = ""
    patterns_used: List[str] = field(default_factory=list)
    user_inputs: List[str] = field(default_factory=list)
    component_groups: Dict[str, List[Dict]] = field(default_factory=dict)

    def to_placement_info(self) -> Dict:
        """轉換為 placement_info 格式"""
        return self.placement_info or {
            "components": self.components,
            "connections": self.connections,
            "layout": {},
            "_meta": {
                "source": "claude_plan_generator",
                "generated_at": datetime.now().isoformat(),
                **self.generation_context
            }
        }


class ClaudePlanGenerator:
    """
    一次性生成執行計畫

    知識注入策略:
    1. 連接三元組 (統計頻率) - 告訴 Claude 哪些連接最常見
    2. 連接模式 (預定義 wiring) - 告訴 Claude 標準連接方式
    3. 組件 GUID (避免衝突) - 確保使用正確的組件版本
    4. 標準工作流程模板 - 確保生成完整流程
    """

    # 標準工作流程模板 (從 39 個 GHX 範例學習)
    STANDARD_WORKFLOWS = {
        "wasp": {
            "name": "WASP Aggregation",
            "description": "標準 WASP 聚集工作流程 (從 0_01_Basic_Aggregation.ghx 學習)",
            "stages": [
                {"stage": "幾何生成", "components": ["Box", "Center Box", "Sphere", "Mesh"]},
                {"stage": "Mesh轉換", "components": ["Mesh Brep"], "required": True, "reason": "WASP 需要 Mesh!"},
                {"stage": "連接點設定", "components": ["Wasp_Connection From Direction", "Line SDL", "Area"]},
                {"stage": "Part建立", "components": ["Wasp_Basic Part"], "required": True},
                {"stage": "規則生成", "components": ["Wasp_Rules Generator"], "required": True},
                {"stage": "聚集執行", "components": ["Wasp_Stochastic Aggregation"], "required": True},
                {"stage": "輸出", "components": ["Wasp_Get Part Geometry", "Custom Preview"], "required": True},
            ],
            "key_connections": [
                {"from": "Wasp_Connection From Direction", "fromParam": "CONN", "to": "Wasp_Basic Part", "toParam": "CONN", "frequency": 33},
                {"from": "Wasp_Basic Part", "fromParam": "PART", "to": "Wasp_Rules Generator", "toParam": "PART", "frequency": 14},
                {"from": "Wasp_Rules Generator", "fromParam": "R", "to": "Wasp_Stochastic Aggregation", "toParam": "RULES", "frequency": 21},
                {"from": "Wasp_Basic Part", "fromParam": "PART", "to": "Wasp_Stochastic Aggregation", "toParam": "PART", "frequency": 11},
                {"from": "Wasp_Stochastic Aggregation", "fromParam": "PART_OUT", "to": "Wasp_Get Part Geometry", "toParam": "PART", "frequency": 11},
                {"from": "Wasp_Get Part Geometry", "fromParam": "GEO", "to": "Custom Preview", "toParam": "G", "frequency": 38},
                {"from": "Line SDL", "fromParam": "L", "to": "Wasp_Connection From Direction", "toParam": "UP", "frequency": 6},
            ]
        },
        "karamba": {
            "name": "Karamba Structural Analysis",
            "description": "標準 Karamba 結構分析流程",
            "stages": [
                {"stage": "幾何生成", "components": ["Line", "Curve"]},
                {"stage": "Beam定義", "components": ["LineToBeam"], "required": True},
                {"stage": "模型組裝", "components": ["Assemble"], "required": True},
                {"stage": "分析", "components": ["Analyze"], "required": True},
                {"stage": "輸出", "components": ["ModelView", "BeamView"]},
            ]
        },
        "kangaroo": {
            "name": "Kangaroo Form Finding",
            "description": "標準 Kangaroo 找形流程",
            "stages": [
                {"stage": "幾何輸入", "components": ["Mesh", "Points"]},
                {"stage": "Goals定義", "components": ["Anchor", "Length", "SoapFilm"]},
                {"stage": "Solver", "components": ["Solver", "Zombie Solver"], "required": True},
                {"stage": "輸出", "components": ["Custom Preview"]},
            ]
        }
    }

    # 系統 prompt 模板
    SYSTEM_PROMPT = """你是 Grasshopper 參數化設計專家。

你的任務是根據用戶需求生成 Grasshopper 組件配置。

## 核心原則：基於範例學習，不要自己亂想！

你必須參考提供的「學習資料」和「標準工作流程」來生成配置：
1. 使用學習資料中**高頻率**的連接模式 (frequency >= 10)
2. 確保工作流程**完整**，不要漏掉關鍵階段
3. 組件名稱必須與學習資料**完全一致** (如 "Wasp_Basic Part" 不是 "WASP Part")

## 輸出格式

你必須輸出 JSON 格式的配置，包含:
- components: 組件列表
- connections: 連接列表

每個組件格式:
```json
{
  "id": "唯一ID",
  "type": "組件類型 (必須與學習資料一致)",
  "nickname": "組件暱稱",
  "guid": "可選，當有衝突時使用 trusted GUID",
  "value": "初始值 (Slider/Panel 使用)",
  "min": "最小值 (Slider 使用)",
  "max": "最大值 (Slider 使用)",
  "col": "列位置 (0-based)",
  "row": "行位置 (0-based)"
}
```

每個連接格式:
```json
{
  "from": "來源組件ID",
  "fromParam": "來源參數名 (必須與學習資料一致)",
  "fromParamIndex": 0,
  "to": "目標組件ID",
  "toParam": "目標參數名 (必須與學習資料一致)",
  "toParamIndex": 0
}
```

## 重要規則

1. **完整流程**: 必須包含從輸入到輸出的完整工作流程，不能只做一半
2. **學習資料優先**: 使用學習資料中出現過的連接模式
3. **Slider 設定順序**: 先設 min/max，再設 value (避免 clamping)
4. **GUID 衝突組件**: Rotate, Pipe, Series 等需使用 trusted GUID
5. **Panel 不能作數值輸入**: 改用 Number Slider
6. **WASP 需要 Mesh**: Wasp_Basic Part 的 GEO 必須接 Mesh，不能接 Brep

## 回應格式

只輸出 JSON，不要包含其他說明文字:

```json
{
  "components": [...],
  "connections": [],
  "_meta": {
    "description": "配置說明",
    "workflow_stages": ["階段1", "階段2", ...],
    "generated_at": "timestamp"
  }
}
```
"""

    def __init__(
        self,
        config_dir: str = "config",
        claude_client: Optional[Any] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        初始化計畫生成器

        Args:
            config_dir: 配置目錄路徑
            claude_client: Claude API 客戶端 (可選)
            model: 使用的模型
        """
        self.config_dir = Path(config_dir)
        self.claude_client = claude_client
        self.model = model

        # 載入知識庫
        self._trusted_guids = self._load_json("trusted_guids.json")
        self._connection_patterns = self._load_json("connection_patterns.json")
        self._mcp_commands = self._load_json("mcp_commands.json")

        # 載入學習資料 (從 GHX 分析得來)
        self._connection_triplets = self._load_json("connection_triplets.json")
        self._component_params = self._load_json("wasp_component_params.json")

    def _load_json(self, filename: str) -> Dict:
        """載入 JSON 配置文件"""
        path = self.config_dir / filename
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def generate(
        self,
        user_input: str,
        partial_knowledge: Dict,
        context: Optional[Dict] = None,
        auto_complete: bool = True
    ) -> ExecutionPlan:
        """
        一次 Claude 調用，生成完整計畫

        Args:
            user_input: 用戶請求
            partial_knowledge: 部分匹配的知識 (from IntegrationBridge.search)
            context: 額外上下文
            auto_complete: 是否自動補全缺失的工作流程階段

        Returns:
            ExecutionPlan
        """
        context = context or {}

        # 檢測工作流程類型
        workflow_type = self.detect_workflow_type(user_input)

        # 如果有對應的標準工作流程，將模板注入 context
        if workflow_type:
            template = self.get_workflow_template(workflow_type)
            if template:
                context["standard_workflow"] = template

        # 建立 prompt
        prompt = self._build_prompt(user_input, partial_knowledge, context)

        # 如果沒有 Claude client，返回錯誤
        if self.claude_client is None:
            return ExecutionPlan(
                success=False,
                errors=["No Claude client configured"],
                generation_context={
                    "prompt_length": len(prompt),
                    "workflow_type": workflow_type,
                    "knowledge_injected": {
                        "triplets": len(partial_knowledge.get("triplets", [])),
                        "patterns": len(partial_knowledge.get("patterns", [])),
                    }
                }
            )

        # 調用 Claude
        try:
            response = self._call_claude(prompt)
            plan = self._parse_response(response)

            plan.generation_context = {
                "model": self.model,
                "prompt_length": len(prompt),
                "workflow_type": workflow_type,
                "knowledge_injected": {
                    "triplets": len(partial_knowledge.get("triplets", [])),
                    "patterns": len(partial_knowledge.get("patterns", [])),
                }
            }

            # 驗證工作流程完整性
            if workflow_type and plan.success:
                validation = self.validate_workflow_completeness(plan, workflow_type)
                plan.generation_context["workflow_validation"] = validation

                # 如果不完整且啟用自動補全
                if not validation["complete"] and auto_complete:
                    plan = self.auto_complete_workflow(plan, workflow_type)
                    plan.warnings.extend(validation["suggestions"])
                elif not validation["complete"]:
                    # 不自動補全，但添加警告
                    plan.warnings.extend(validation["suggestions"])

            return plan

        except Exception as e:
            return ExecutionPlan(
                success=False,
                errors=[f"Claude API error: {str(e)}"],
                generation_context={
                    "prompt_length": len(prompt),
                    "workflow_type": workflow_type
                }
            )

    def generate_with_mermaid(
        self,
        user_input: str,
        partial_knowledge: Dict,
        wip_dir: Path = Path("GH_WIP"),
        context: Optional[Dict] = None
    ) -> Tuple[ExecutionPlan, Path]:
        """
        生成執行計畫 + Mermaid 可視化

        Args:
            user_input: 用戶請求
            partial_knowledge: 部分匹配的知識
            wip_dir: 工作目錄路徑
            context: 額外上下文

        Returns:
            (plan, mermaid_path)
        """
        # 確保目錄存在
        wip_dir = Path(wip_dir)
        wip_dir.mkdir(exist_ok=True)

        # 1. 生成計畫
        plan = self.generate(user_input, partial_knowledge, context)

        # 2. 生成 Mermaid 流程圖
        mermaid_content = self._plan_to_mermaid(plan, user_input)
        mermaid_path = wip_dir / "component_info.mmd"
        mermaid_path.write_text(mermaid_content, encoding="utf-8")

        # 3. 更新 generation_context
        plan.generation_context["mermaid_path"] = str(mermaid_path)
        plan.generation_context["description"] = user_input

        return plan, mermaid_path

    def _plan_to_mermaid(self, plan: ExecutionPlan, description: str = "") -> str:
        """
        將計畫轉換為 Mermaid flowchart

        Args:
            plan: 執行計畫
            description: 計畫描述

        Returns:
            Mermaid flowchart 字符串
        """
        lines = [
            "flowchart LR",
            f"    %% 自動生成 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"    %% 描述: {description}",
            "    %% 請在 VSCode 中預覽並確認",
            "",
        ]

        if not plan.success or not plan.components:
            lines.append("    %% 計畫生成失敗或無組件")
            if plan.errors:
                for err in plan.errors[:3]:
                    lines.append(f"    %% Error: {err}")
            return "\n".join(lines)

        # 將組件按類型分組
        groups = self._group_components(plan.components)

        # 組件子圖
        for group_name, components in groups.items():
            # 清理 group_name，移除特殊字符
            safe_group_name = group_name.replace(" ", "_").replace("-", "_")
            lines.append(f'    subgraph {safe_group_name}["{group_name}"]')
            for comp in components:
                comp_id = comp.get("id", "unknown")
                comp_type = comp.get("type", "Unknown")
                nickname = comp.get("nickname", comp_id)
                # 處理 Slider 的額外信息
                if "Slider" in comp_type or "slider" in comp_type.lower():
                    value = comp.get("value", "")
                    min_val = comp.get("min", "")
                    max_val = comp.get("max", "")
                    if value:
                        lines.append(
                            f'        {comp_id}["{comp_type}<br/>'
                            f'nickname: {nickname}<br/>'
                            f'value: {value} ({min_val}-{max_val})"]'
                        )
                    else:
                        lines.append(
                            f'        {comp_id}["{comp_type}<br/>'
                            f'nickname: {nickname}"]'
                        )
                else:
                    lines.append(
                        f'        {comp_id}["{comp_type}<br/>'
                        f'nickname: {nickname}"]'
                    )
            lines.append("    end")
            lines.append("")

        # 連接 (含學習資料驗證)
        if plan.connections:
            lines.append("    %% 連接")

            # 建立組件 ID 到類型的映射
            id_to_type = {c.get("id", ""): c.get("type", "") for c in plan.components}

            for conn in plan.connections:
                from_id = conn.get("from", "")
                to_id = conn.get("to", "")
                from_param = conn.get("fromParam", conn.get("from_param", ""))
                to_param = conn.get("toParam", conn.get("to_param", ""))

                # 驗證連接是否在學習資料中
                from_type = id_to_type.get(from_id, "")
                to_type = id_to_type.get(to_id, "")

                # 嘗試獲取標準組件名稱
                canonical_from = self.get_canonical_component_name(from_type) or from_type
                canonical_to = self.get_canonical_component_name(to_type) or to_type

                validation = self.validate_connection(
                    canonical_from, from_param, canonical_to, to_param
                )

                # 根據驗證結果調整連接標籤
                confidence_icon = ""
                if validation["valid"]:
                    freq = validation["frequency"]
                    if freq >= 10:
                        confidence_icon = "✅"  # 高頻連接
                    elif freq >= 5:
                        confidence_icon = "🟡"  # 中頻連接
                    else:
                        confidence_icon = "🔵"  # 低頻但有記錄

                if from_id and to_id:
                    if from_param or to_param:
                        label = f"{from_param} → {to_param}"
                        if confidence_icon:
                            label = f"{confidence_icon} {label}"
                        lines.append(f'    {from_id} -->|"{label}"| {to_id}')
                    else:
                        lines.append(f'    {from_id} --> {to_id}')

        return "\n".join(lines)

    def _group_components(self, components: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按類型分組組件

        分組規則 (按照 WASP 工作流程階段):
        - Slider/Number → "參數 Parameters"
        - Box/Brep 幾何 → "幾何生成 Geometry"
        - Mesh Brep → "Mesh轉換 Mesh_Convert"
        - Wasp_Connection → "連接點設定 Connection"
        - Wasp_Part → "Part建立 Part_Build"
        - Wasp_Rules → "規則生成 Rules"
        - Wasp_Aggregation → "聚集執行 Aggregation"
        - Preview/Get Geometry → "輸出 Output"
        """
        groups: Dict[str, List[Dict]] = {}

        for comp in components:
            comp_type = comp.get("type", "").lower()
            comp_type_original = comp.get("type", "")

            # WASP 特定分組 (按工作流程階段)
            if "wasp_connection" in comp_type:
                group = "連接點設定 Connection"
            elif "wasp_basic part" in comp_type or "wasp_part" in comp_type:
                group = "Part建立 Part_Build"
            elif "wasp_rules" in comp_type:
                group = "規則生成 Rules"
            elif "wasp_aggregation" in comp_type or "wasp_stochastic" in comp_type or "wasp_field" in comp_type:
                group = "聚集執行 Aggregation"
            elif "wasp_get" in comp_type:
                group = "輸出 Output"
            # Karamba 分組
            elif "karamba" in comp_type or "linetobeam" in comp_type or "assemble" in comp_type or "analyze" in comp_type:
                group = "結構分析 Structural"
            # Kangaroo 分組
            elif "kangaroo" in comp_type or "solver" in comp_type or "anchor" in comp_type or "goal" in comp_type:
                group = "找形 FormFinding"
            # 通用分組
            elif any(kw in comp_type for kw in ["slider", "number", "panel", "param"]):
                group = "參數 Parameters"
            elif any(kw in comp_type for kw in ["mesh brep", "mesh"]) and "wasp" not in comp_type:
                group = "Mesh轉換 Mesh_Convert"
            elif any(kw in comp_type for kw in ["box", "center box", "sphere", "cylinder"]):
                group = "幾何生成 Geometry"
            elif any(kw in comp_type for kw in ["point", "vector", "plane", "xyz"]):
                group = "幾何基元 Primitives"
            elif any(kw in comp_type for kw in ["line", "circle", "curve", "arc", "polyline", "line sdl"]):
                group = "曲線 Curves"
            elif any(kw in comp_type for kw in ["surface", "brep", "extrude", "loft"]):
                group = "曲面 Surfaces"
            elif any(kw in comp_type for kw in ["area", "face", "deconstruct"]):
                group = "幾何分析 Analysis"
            elif any(kw in comp_type for kw in ["division", "series", "multiply", "add", "subtract", "math", "sin", "cos", "radian"]):
                group = "計算邏輯 Calculations"
            elif any(kw in comp_type for kw in ["rotate", "move", "scale", "transform", "orient"]):
                group = "變換 Transforms"
            elif any(kw in comp_type for kw in ["preview", "custom preview"]):
                group = "輸出 Output"
            else:
                group = "處理 Processing"

            if group not in groups:
                groups[group] = []
            groups[group].append(comp)

        # 按工作流程順序排序組別
        workflow_order = [
            "參數 Parameters",
            "幾何生成 Geometry",
            "幾何基元 Primitives",
            "曲線 Curves",
            "曲面 Surfaces",
            "Mesh轉換 Mesh_Convert",
            "幾何分析 Analysis",
            "連接點設定 Connection",
            "Part建立 Part_Build",
            "規則生成 Rules",
            "聚集執行 Aggregation",
            "計算邏輯 Calculations",
            "變換 Transforms",
            "結構分析 Structural",
            "找形 FormFinding",
            "處理 Processing",
            "輸出 Output",
        ]

        ordered_groups: Dict[str, List[Dict]] = {}
        for group_name in workflow_order:
            if group_name in groups:
                ordered_groups[group_name] = groups[group_name]

        # 添加任何未在順序中的組別
        for group_name, comps in groups.items():
            if group_name not in ordered_groups:
                ordered_groups[group_name] = comps

        return ordered_groups

    def _build_prompt(
        self,
        user_input: str,
        partial_knowledge: Dict,
        context: Dict
    ) -> str:
        """
        建立注入知識的 prompt

        知識注入:
        1. 相關連接三元組 (統計頻率) - 從 GHX 學習
        2. 組件參數資訊 - 從 GHX 學習
        3. 匹配的連接模式
        4. 衝突組件的 trusted GUID
        """
        sections = []

        # 用戶請求
        sections.append(f"## 用戶請求\n\n{user_input}")

        # 注入連接三元組 (優先使用 partial_knowledge，否則從本地學習資料查詢)
        triplets = partial_knowledge.get("triplets", [])
        if not triplets:
            # 從用戶輸入提取關鍵字並查詢學習資料
            keywords = self._extract_keywords_from_input(user_input)
            triplets = self.get_learned_triplets(keywords, limit=15)

        if triplets:
            triplet_text = self._format_triplets(triplets[:15])
            sections.append(
                f"## 學習到的連接模式 (從 {self._connection_triplets.get('metadata', {}).get('analyzed_files', '?')} 個 GHX 文件)\n\n"
                f"{triplet_text}"
            )

        # 注入組件參數資訊 (新增：從學習資料)
        relevant_components = self._get_relevant_component_params(user_input)
        if relevant_components:
            params_text = self._format_component_params(relevant_components)
            sections.append(f"## 組件參數參考 (從 GHX 學習)\n\n{params_text}")

        # 注入連接模式
        patterns = partial_knowledge.get("patterns", [])
        if patterns:
            pattern_text = self._format_patterns(patterns[:5])
            sections.append(f"## 預定義連接模式\n\n{pattern_text}")

        # 注入 trusted GUIDs
        guid_text = self._format_trusted_guids()
        if guid_text:
            sections.append(f"## 衝突組件 GUID\n\n{guid_text}")

        # 注入標準工作流程模板 (如果有)
        standard_workflow = context.pop("standard_workflow", None)
        if standard_workflow:
            workflow_text = self._format_standard_workflow(standard_workflow)
            sections.append(f"## 標準工作流程 (必須遵循！)\n\n{workflow_text}")

        # 注入額外上下文
        if context:
            context_text = json.dumps(context, indent=2, ensure_ascii=False)
            sections.append(f"## 額外上下文\n\n```json\n{context_text}\n```")

        return "\n\n---\n\n".join(sections)

    def _format_standard_workflow(self, workflow: Dict) -> str:
        """格式化標準工作流程模板"""
        lines = [
            f"### {workflow.get('name', 'Unknown Workflow')}",
            "",
            f"{workflow.get('description', '')}",
            "",
            "**必要階段 (不可省略！):**",
            ""
        ]

        for stage_info in workflow.get("stages", []):
            stage_name = stage_info.get("stage", "")
            components = stage_info.get("components", [])
            required = stage_info.get("required", False)
            reason = stage_info.get("reason", "")

            marker = "⚠️ **必要**" if required else ""
            lines.append(f"- **{stage_name}**: {', '.join(components)} {marker}")
            if reason:
                lines.append(f"  - 原因: {reason}")

        # 添加關鍵連接
        key_connections = workflow.get("key_connections", [])
        if key_connections:
            lines.extend([
                "",
                "**關鍵連接模式 (從 GHX 範例學習):**",
                "",
                "| 來源 | 參數 | 目標 | 參數 | 頻率 |",
                "|------|------|------|------|------|"
            ])
            for conn in key_connections:
                lines.append(
                    f"| {conn['from']} | {conn['fromParam']} | "
                    f"{conn['to']} | {conn['toParam']} | {conn['frequency']}x |"
                )

        return "\n".join(lines)

    def _extract_keywords_from_input(self, text: str) -> List[str]:
        """從用戶輸入提取關鍵字"""
        domain_keywords = {
            'wasp': ['wasp', '聚集', 'aggregation', 'part', '零件'],
            'karamba': ['karamba', '結構', 'structural', 'beam', '梁'],
            'kangaroo': ['kangaroo', '找形', 'tensile', 'membrane', '張力'],
            'ladybug': ['ladybug', '日照', 'solar', 'shadow', '陰影'],
            'mesh': ['mesh', '網格', 'subdivision', '細分'],
        }

        text_lower = text.lower()
        extracted = []

        for category, kws in domain_keywords.items():
            for kw in kws:
                if kw in text_lower:
                    extracted.append(category)
                    break

        return extracted if extracted else ['wasp']  # 預設 wasp

    def _get_relevant_component_params(self, user_input: str) -> Dict[str, Dict]:
        """根據用戶輸入獲取相關的組件參數"""
        components = self._component_params.get("components", {})
        if not components:
            return {}

        user_lower = user_input.lower()
        relevant = {}

        # 關鍵字到組件的映射
        keyword_to_components = {
            'wasp': ['Wasp_Basic Part', 'Wasp_Connection From Direction', 'Wasp_Rules Generator', 'Wasp_Stochastic Aggregation'],
            'part': ['Wasp_Basic Part', 'Wasp_Connection From Direction'],
            'connection': ['Wasp_Connection From Direction'],
            'rule': ['Wasp_Rules Generator'],
            'aggregation': ['Wasp_Stochastic Aggregation', 'Wasp_Field-driven Aggregation'],
        }

        for kw, comp_names in keyword_to_components.items():
            if kw in user_lower:
                for name in comp_names:
                    if name in components and name not in relevant:
                        relevant[name] = components[name]

        return relevant

    def _format_component_params(self, components: Dict[str, Dict]) -> str:
        """格式化組件參數資訊"""
        lines = []

        for name, info in components.items():
            lines.append(f"### {name}")

            inputs = info.get("inputs", [])
            if inputs:
                lines.append("\n**輸入參數:**")
                for inp in inputs:
                    nick = inp.get("nickname", "")
                    desc = inp.get("description", "")[:80]
                    lines.append(f"- `{nick}`: {desc}")

            outputs = info.get("outputs", [])
            if outputs:
                lines.append("\n**輸出參數:**")
                for out in outputs:
                    nick = out.get("nickname", "")
                    desc = out.get("description", "")[:80]
                    lines.append(f"- `{nick}`: {desc}")

            lines.append("")

        return "\n".join(lines)

    def _format_triplets(self, triplets: List[Dict]) -> str:
        """格式化連接三元組"""
        lines = ["| 來源 | 來源參數 | 目標 | 目標參數 | 頻率 |",
                 "|------|----------|------|----------|------|"]

        for t in triplets:
            lines.append(
                f"| {t.get('source_component', '')} | "
                f"{t.get('source_param', '')} | "
                f"{t.get('target_component', '')} | "
                f"{t.get('target_param', '')} | "
                f"{t.get('frequency', 0)} |"
            )

        return "\n".join(lines)

    def _format_patterns(self, patterns: List[Dict]) -> str:
        """格式化連接模式"""
        lines = []

        for p in patterns:
            name = p.get("name", "Unknown")
            desc = p.get("description", "")
            wiring = p.get("wiring", [])

            lines.append(f"### {name}")
            if desc:
                lines.append(f"\n{desc}")
            if wiring:
                lines.append("\n連接:")
                for w in wiring[:5]:  # 限制數量
                    lines.append(f"- {w.get('from', '')} → {w.get('to', '')}")
            lines.append("")

        return "\n".join(lines)

    def _format_trusted_guids(self) -> str:
        """格式化 trusted GUIDs"""
        components = self._trusted_guids.get("components", {})
        conflict_components = ["Rotate", "Pipe", "Series", "Line", "Point", "Circle"]

        lines = ["| 組件 | GUID | 衝突說明 |",
                 "|------|------|----------|"]

        for name in conflict_components:
            info = components.get(name, {})
            if info:
                guid = info.get("guid", "")[:36]  # 限制長度
                conflicts = ", ".join(info.get("known_conflicts", []))
                lines.append(f"| {name} | `{guid}...` | {conflicts} |")

        return "\n".join(lines) if len(lines) > 2 else ""

    # =========================================================================
    # 學習資料查詢 (從 GHX 分析得來)
    # =========================================================================

    def get_learned_triplets(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """
        根據關鍵字查詢學習到的連接三元組

        Args:
            keywords: 關鍵字列表 (如 ["wasp", "part"])
            limit: 返回數量上限

        Returns:
            匹配的三元組列表，按頻率排序
        """
        triplets = self._connection_triplets.get("triplets", [])
        if not triplets:
            return []

        keywords_lower = {k.lower() for k in keywords}
        matched = []

        for t in triplets:
            source = t.get("source_component", "").lower()
            target = t.get("target_component", "").lower()

            if any(kw in source or kw in target for kw in keywords_lower):
                matched.append(t)

        # 按頻率排序
        matched.sort(key=lambda x: x.get("frequency", 0), reverse=True)
        return matched[:limit]

    def get_component_params(self, component_name: str) -> Optional[Dict]:
        """
        獲取組件的參數資訊 (從 wasp_component_params.json)

        Args:
            component_name: 組件名稱 (如 "Wasp_Basic Part")

        Returns:
            組件參數資訊，包含 inputs 和 outputs
        """
        components = self._component_params.get("components", {})
        return components.get(component_name)

    def validate_connection(
        self,
        source_component: str,
        source_param: str,
        target_component: str,
        target_param: str
    ) -> Dict:
        """
        驗證連接是否在學習資料中有記錄

        Returns:
            {
                "valid": bool,
                "frequency": int,      # 0 表示未見過
                "confidence": float,   # 0.0-1.0
                "examples": List[str]  # 出現在哪些 GHX 文件
            }
        """
        triplets = self._connection_triplets.get("triplets", [])

        for t in triplets:
            if (t.get("source_component", "") == source_component and
                t.get("source_param", "") == source_param and
                t.get("target_component", "") == target_component and
                t.get("target_param", "") == target_param):

                freq = t.get("frequency", 0)
                confidence = min(1.0, freq / 10.0)  # 10+ 次視為高置信

                return {
                    "valid": True,
                    "frequency": freq,
                    "confidence": confidence,
                    "examples": t.get("examples", [])[:5]
                }

        return {
            "valid": False,
            "frequency": 0,
            "confidence": 0.0,
            "examples": []
        }

    def get_canonical_component_name(self, nickname: str) -> Optional[str]:
        """
        從暱稱獲取標準組件名稱

        例如: "WASP Part" -> "Wasp_Basic Part"
        """
        components = self._component_params.get("components", {})

        # 直接匹配
        if nickname in components:
            return nickname

        # 模糊匹配
        nickname_lower = nickname.lower().replace(" ", "_").replace("-", "_")
        for name in components:
            name_normalized = name.lower().replace(" ", "_")
            if nickname_lower in name_normalized or name_normalized in nickname_lower:
                return name

        return None

    # =========================================================================
    # 工作流程完整性驗證 (防止漏掉關鍵階段)
    # =========================================================================

    def detect_workflow_type(self, user_input: str) -> Optional[str]:
        """
        根據用戶輸入檢測工作流程類型

        Returns:
            工作流程類型 ("wasp", "karamba", "kangaroo") 或 None

        Note:
            檢測順序很重要！更特定的關鍵字應該先檢測。
            例如 "張力膜結構" 應該優先匹配 kangaroo 而非 karamba。
        """
        user_lower = user_input.lower()

        # 按優先順序排列的關鍵字 (更特定的先檢測)
        # 例如: kangaroo 的 "張力" 比 karamba 的 "結構" 更特定
        workflow_keywords = [
            # Kangaroo 先檢測 (因為 "張力膜結構" 包含 "結構")
            ("kangaroo", ["kangaroo", "找形", "tensile", "membrane", "張力", "physics", "袋鼠"]),
            # WASP 次之
            ("wasp", ["wasp", "聚集", "aggregation", "part", "零件", "assembly"]),
            # Karamba 最後 (因為 "結構" 太通用)
            ("karamba", ["karamba", "結構分析", "structural", "beam", "梁", "力學", "桿件"]),
        ]

        for workflow_type, keywords in workflow_keywords:
            if any(kw in user_lower for kw in keywords):
                return workflow_type

        return None

    def get_workflow_template(self, workflow_type: str) -> Optional[Dict]:
        """
        獲取標準工作流程模板

        Args:
            workflow_type: 工作流程類型

        Returns:
            工作流程模板字典
        """
        return self.STANDARD_WORKFLOWS.get(workflow_type)

    def validate_workflow_completeness(
        self,
        plan: ExecutionPlan,
        workflow_type: str
    ) -> Dict[str, Any]:
        """
        驗證計畫是否包含工作流程的所有必要階段

        這是防止漏掉關鍵組件的核心方法！
        例如: WASP 工作流程必須有 Aggregation → Get Geometry → Preview

        Args:
            plan: 生成的執行計畫
            workflow_type: 工作流程類型

        Returns:
            {
                "complete": bool,
                "missing_stages": List[str],
                "missing_components": List[str],
                "missing_connections": List[Dict],
                "warnings": List[str],
                "suggestions": List[str]
            }
        """
        template = self.STANDARD_WORKFLOWS.get(workflow_type)
        if not template:
            return {
                "complete": True,  # 沒有模板就不驗證
                "missing_stages": [],
                "missing_components": [],
                "missing_connections": [],
                "warnings": [f"No template found for workflow type: {workflow_type}"],
                "suggestions": []
            }

        # 獲取計畫中的組件類型
        plan_component_types = set()
        for comp in plan.components:
            comp_type = comp.get("type", "")
            plan_component_types.add(comp_type)
            # 也加入標準化名稱
            canonical = self.get_canonical_component_name(comp_type)
            if canonical:
                plan_component_types.add(canonical)

        # 檢查必要階段
        missing_stages = []
        missing_components = []

        for stage_info in template.get("stages", []):
            stage_name = stage_info.get("stage", "")
            required = stage_info.get("required", False)
            stage_components = stage_info.get("components", [])

            # 檢查階段中是否有任何組件存在
            stage_has_component = any(
                comp in plan_component_types or
                self.get_canonical_component_name(comp) in plan_component_types
                for comp in stage_components
            )

            if required and not stage_has_component:
                missing_stages.append(stage_name)
                reason = stage_info.get("reason", "")
                if reason:
                    missing_components.append(f"{stage_components[0]} ({reason})")
                else:
                    missing_components.append(stage_components[0])

        # 檢查關鍵連接
        missing_connections = []
        plan_connections_set = set()

        for conn in plan.connections:
            key = (
                conn.get("from", ""),
                conn.get("fromParam", conn.get("from_param", "")),
                conn.get("to", ""),
                conn.get("toParam", conn.get("to_param", ""))
            )
            plan_connections_set.add(key)

        # 建立 ID 到 Type 的映射
        id_to_type = {c.get("id", ""): c.get("type", "") for c in plan.components}

        for key_conn in template.get("key_connections", []):
            from_type = key_conn.get("from", "")
            from_param = key_conn.get("fromParam", "")
            to_type = key_conn.get("to", "")
            to_param = key_conn.get("toParam", "")
            freq = key_conn.get("frequency", 0)

            # 檢查是否有類似的連接
            has_connection = False
            for plan_conn in plan.connections:
                plan_from_id = plan_conn.get("from", "")
                plan_to_id = plan_conn.get("to", "")
                plan_from_type = id_to_type.get(plan_from_id, "")
                plan_to_type = id_to_type.get(plan_to_id, "")

                # 標準化組件名稱
                plan_from_canonical = self.get_canonical_component_name(plan_from_type) or plan_from_type
                plan_to_canonical = self.get_canonical_component_name(plan_to_type) or plan_to_type

                if (plan_from_canonical == from_type and
                    plan_to_canonical == to_type and
                    plan_conn.get("fromParam", plan_conn.get("from_param", "")) == from_param and
                    plan_conn.get("toParam", plan_conn.get("to_param", "")) == to_param):
                    has_connection = True
                    break

            if not has_connection and freq >= 10:  # 只報告高頻連接
                missing_connections.append({
                    "from": from_type,
                    "fromParam": from_param,
                    "to": to_type,
                    "toParam": to_param,
                    "frequency": freq
                })

        # 生成建議
        suggestions = []
        if missing_stages:
            suggestions.append(
                f"缺少必要階段: {', '.join(missing_stages)}。"
                f"請參考 {template['name']} 標準流程。"
            )
        if missing_components:
            suggestions.append(
                f"請添加以下組件: {', '.join(missing_components)}"
            )
        if missing_connections:
            conn_strs = [
                f"{c['from']}.{c['fromParam']} → {c['to']}.{c['toParam']} (freq={c['frequency']})"
                for c in missing_connections[:3]
            ]
            suggestions.append(
                f"建議添加以下連接: {'; '.join(conn_strs)}"
            )

        return {
            "complete": len(missing_stages) == 0,
            "missing_stages": missing_stages,
            "missing_components": missing_components,
            "missing_connections": missing_connections,
            "warnings": [],
            "suggestions": suggestions
        }

    def auto_complete_workflow(
        self,
        plan: ExecutionPlan,
        workflow_type: str
    ) -> ExecutionPlan:
        """
        自動補全缺失的工作流程階段

        這是一個增強功能：當檢測到缺失階段時，
        自動從標準模板補充組件和連接。

        Args:
            plan: 原始計畫
            workflow_type: 工作流程類型

        Returns:
            補全後的 ExecutionPlan
        """
        validation = self.validate_workflow_completeness(plan, workflow_type)

        if validation["complete"]:
            return plan  # 已完整，無需補全

        template = self.STANDARD_WORKFLOWS.get(workflow_type)
        if not template:
            return plan

        # 複製組件和連接列表
        new_components = list(plan.components)
        new_connections = list(plan.connections)

        # 根據缺失階段補充組件
        existing_types = {c.get("type", "") for c in new_components}
        max_col = max((c.get("col", 0) for c in new_components), default=0)
        current_row = 0

        for stage_info in template.get("stages", []):
            stage_name = stage_info.get("stage", "")
            if stage_name not in validation["missing_stages"]:
                continue

            stage_components = stage_info.get("components", [])
            for comp_type in stage_components:
                if comp_type in existing_types:
                    continue

                # 添加缺失的組件
                comp_id = comp_type.lower().replace(" ", "_").replace("-", "_")
                new_comp = {
                    "id": f"{comp_id}_auto",
                    "type": comp_type,
                    "nickname": comp_type.split("_")[-1] if "_" in comp_type else comp_type,
                    "col": max_col + 1,
                    "row": current_row,
                    "_auto_added": True,
                    "_reason": f"補全 {stage_name} 階段"
                }
                new_components.append(new_comp)
                existing_types.add(comp_type)
                current_row += 1

                # 只添加第一個建議組件
                break

            max_col += 1

        # 根據缺失連接補充
        for missing_conn in validation["missing_connections"][:5]:  # 最多補 5 個
            # 找到對應的組件 ID
            from_id = None
            to_id = None

            for comp in new_components:
                comp_type = comp.get("type", "")
                canonical = self.get_canonical_component_name(comp_type) or comp_type

                if canonical == missing_conn["from"]:
                    from_id = comp.get("id")
                elif canonical == missing_conn["to"]:
                    to_id = comp.get("id")

            if from_id and to_id:
                new_conn = {
                    "from": from_id,
                    "fromParam": missing_conn["fromParam"],
                    "fromParamIndex": 0,
                    "to": to_id,
                    "toParam": missing_conn["toParam"],
                    "toParamIndex": 0,
                    "_auto_added": True
                }
                new_connections.append(new_conn)

        # 更新 warnings
        warnings = list(plan.warnings)
        if validation["missing_stages"]:
            warnings.append(
                f"已自動補全缺失階段: {', '.join(validation['missing_stages'])}"
            )

        # 建立新的 placement_info
        new_placement_info = {
            "components": new_components,
            "connections": new_connections,
            "layout": plan.placement_info.get("layout", {}) if plan.placement_info else {},
            "_meta": {
                **(plan.placement_info.get("_meta", {}) if plan.placement_info else {}),
                "auto_completed": True,
                "auto_completed_stages": validation["missing_stages"]
            }
        }

        return ExecutionPlan(
            success=plan.success,
            placement_info=new_placement_info,
            components=new_components,
            connections=new_connections,
            errors=plan.errors,
            warnings=warnings,
            generation_context={
                **plan.generation_context,
                "workflow_validation": validation
            },
            description=plan.description,
            patterns_used=plan.patterns_used,
            user_inputs=plan.user_inputs,
            component_groups=plan.component_groups
        )

    def _call_claude(self, prompt: str) -> str:
        """調用 Claude API"""
        # 使用 Anthropic Python SDK
        if hasattr(self.claude_client, 'messages'):
            # anthropic.Anthropic client
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        # 假設是其他 client 類型
        raise ValueError("Unsupported Claude client type")

    def _parse_response(self, response: str) -> ExecutionPlan:
        """解析 Claude 回應"""
        try:
            # 嘗試提取 JSON
            json_str = response

            # 處理 markdown 代碼塊
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()

            data = json.loads(json_str)

            components = data.get("components", [])
            connections = data.get("connections", [])
            meta = data.get("_meta", {})

            # 驗證基本結構
            if not components:
                return ExecutionPlan(
                    success=False,
                    errors=["Generated plan has no components"]
                )

            # 建立 placement_info
            placement_info = {
                "components": components,
                "connections": connections,
                "layout": {},
                "_meta": {
                    "source": "claude_plan_generator",
                    "generated_at": datetime.now().isoformat(),
                    **meta
                }
            }

            return ExecutionPlan(
                success=True,
                placement_info=placement_info,
                components=components,
                connections=connections
            )

        except json.JSONDecodeError as e:
            return ExecutionPlan(
                success=False,
                errors=[f"Failed to parse JSON: {str(e)}"],
                generation_context={"raw_response": response[:500]}
            )
        except Exception as e:
            return ExecutionPlan(
                success=False,
                errors=[f"Failed to parse response: {str(e)}"]
            )

    def generate_from_template(
        self,
        template_name: str,
        parameters: Dict
    ) -> ExecutionPlan:
        """
        從模板生成計畫 (不需要 Claude)

        用於已知模式的快速生成
        """
        patterns = self._connection_patterns.get("patterns", {})
        template = patterns.get(template_name)

        if not template:
            return ExecutionPlan(
                success=False,
                errors=[f"Template '{template_name}' not found"]
            )

        # TODO: 實作模板展開邏輯
        return ExecutionPlan(
            success=False,
            errors=["Template expansion not yet implemented"]
        )


# =============================================================================
# 便捷函數
# =============================================================================

def generate_plan(
    user_input: str,
    knowledge: Dict,
    claude_client: Optional[Any] = None
) -> ExecutionPlan:
    """
    快速生成執行計畫

    Args:
        user_input: 用戶請求
        knowledge: 知識庫搜尋結果
        claude_client: Claude 客戶端

    Returns:
        ExecutionPlan
    """
    generator = ClaudePlanGenerator(claude_client=claude_client)
    return generator.generate(user_input, knowledge)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    print("ClaudePlanGenerator - Layer 2 計畫生成器")
    print("=" * 50)
    print("\n注意: 需要配置 Claude API 客戶端才能實際生成")
    print("\nUsage:")
    print("  from grasshopper_mcp import ClaudePlanGenerator")
    print("  generator = ClaudePlanGenerator(claude_client=client)")
    print("  plan = generator.generate(user_input, knowledge)")
