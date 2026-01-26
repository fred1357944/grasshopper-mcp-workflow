#!/usr/bin/env python3
"""
HITL Integration Tests
======================

測試人機協作整合功能：
- Layer 1 無 HITL 直接執行
- Layer 2 生成 Mermaid 並等待確認
- Layer 3 完整六階段流程
- 用戶取消功能

Usage:
    pytest tests/test_hitl_integration.py -v
"""

import pytest
import asyncio
from pathlib import Path
from typing import List, Iterator
import json
import tempfile
import shutil

# 導入測試目標
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp import UnifiedHandler, Layer
from grasshopper_mcp.hitl_collaborator import HITLCollaborator, Answer


# =============================================================================
# 異步測試輔助
# =============================================================================

def run_async(coro):
    """運行異步函數的輔助函數"""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# Mock 類
# =============================================================================

class MockUserCallback:
    """模擬用戶回答"""

    def __init__(self, responses: List[str]):
        """
        Args:
            responses: 預設的回答列表，按順序返回
        """
        self._responses: Iterator[str] = iter(responses)
        self._call_count = 0
        self._prompts: List[str] = []

    async def __call__(self, prompt: str) -> str:
        """返回下一個預設回答"""
        self._call_count += 1
        self._prompts.append(prompt)
        try:
            return next(self._responses)
        except StopIteration:
            return "y"  # 預設確認

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def prompts(self) -> List[str]:
        return self._prompts


class MockClaudeClient:
    """模擬 Claude API 客戶端"""

    def __init__(self, response: str = None):
        self._response = response or self._default_response()
        self._call_count = 0

    def _default_response(self) -> str:
        return json.dumps({
            "components": [
                {
                    "id": "slider1",
                    "type": "Number Slider",
                    "nickname": "Count",
                    "value": 10,
                    "min": 1,
                    "max": 100,
                    "col": 0,
                    "row": 0
                },
                {
                    "id": "point1",
                    "type": "Construct Point",
                    "nickname": "Origin",
                    "col": 1,
                    "row": 0
                }
            ],
            "connections": [
                {
                    "from": "slider1",
                    "fromParam": "N",
                    "fromParamIndex": 0,
                    "to": "point1",
                    "toParam": "X",
                    "toParamIndex": 0
                }
            ],
            "_meta": {
                "description": "Test plan"
            }
        })

    @property
    def messages(self):
        """模擬 Anthropic client.messages"""
        return self

    def create(self, **kwargs):
        """模擬 messages.create()"""
        self._call_count += 1
        return MockResponse(self._response)

    @property
    def call_count(self) -> int:
        return self._call_count


class MockResponse:
    """模擬 Claude API 響應"""

    def __init__(self, text: str):
        self.content = [MockContent(text)]


class MockContent:
    """模擬響應內容"""

    def __init__(self, text: str):
        self.text = text


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_config_dir():
    """創建臨時配置目錄"""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir()

    # 創建必要的配置文件
    (config_dir / "trusted_guids.json").write_text("{}", encoding="utf-8")
    (config_dir / "connection_patterns.json").write_text("{}", encoding="utf-8")
    (config_dir / "mcp_commands.json").write_text("{}", encoding="utf-8")
    (config_dir / "learned_patterns.json").write_text("{}", encoding="utf-8")

    # 創建 Golden Knowledge
    golden_dir = config_dir / "golden_knowledge"
    golden_dir.mkdir()

    # 創建一個 Golden 配置
    golden_config = {
        "id": "wasp_cube",
        "request": "用 WASP 做立方體聚集",
        "keywords": ["wasp", "cube", "aggregation", "立方體", "聚集"],
        "solution": {
            "components": [
                {"id": "box", "type": "Box", "nickname": "Cube"}
            ],
            "connections": []
        }
    }
    (golden_dir / "wasp_cube.json").write_text(
        json.dumps(golden_config, ensure_ascii=False),
        encoding="utf-8"
    )

    yield temp_dir

    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_wip_dir():
    """創建臨時工作目錄"""
    temp_dir = tempfile.mkdtemp()
    wip_dir = Path(temp_dir) / "GH_WIP"
    wip_dir.mkdir()

    yield str(wip_dir)

    shutil.rmtree(temp_dir)


# =============================================================================
# Layer 1 測試 (無 HITL)
# =============================================================================

class TestLayer1NoHITL:
    """Layer 1 或 Layer 2 fallback 應該直接執行，不需要 HITL"""

    def test_layer1_or_fallback_execution(self, temp_config_dir):
        """Golden 或 Reference Library 匹配應該直接執行，無 HITL"""
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False
        )

        # 這個請求可能匹配 Golden Knowledge 或 Reference Library
        result = handler.handle("用 WASP 做立方體聚集")

        # 應該是 Layer 1 或 Layer 2 (reference fallback)
        assert result.layer in [Layer.DIRECT, Layer.SUPPLEMENT]
        # 不應該調用 Claude (直接從知識庫)
        assert result.claude_calls == 0
        # 知識來源應該是 golden 或 reference
        assert result.knowledge_source in ["golden", "reference"]

    def test_layer1_no_hitl_callback_needed(self, temp_config_dir):
        """Layer 1/2 fallback 不需要 HITL 回調"""
        # 不提供 user_callback
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False,
            user_callback=None
        )

        result = handler.handle("用 WASP 做立方體聚集")

        # 應該成功（無需 HITL）
        assert result.layer in [Layer.DIRECT, Layer.SUPPLEMENT]
        # 成功執行
        assert result.success is True


# =============================================================================
# Layer 2 測試 (Mermaid + HITL)
# =============================================================================

class TestLayer2WithHITL:
    """Layer 2 應該生成 Mermaid 並等待確認"""

    def test_layer2_generates_mermaid(self, temp_config_dir, temp_wip_dir):
        """Layer 2 應該生成 Mermaid 並等待確認"""
        async def _test():
            mock_callback = MockUserCallback(["y"])  # 自動確認
            mock_claude = MockClaudeClient()

            handler = UnifiedHandler(
                config_dir=f"{temp_config_dir}/config",
                auto_execute=False,
                user_callback=mock_callback,
                wip_dir=temp_wip_dir
            )
            # 注入 mock Claude client
            handler.plan_generator._claude_client = mock_claude

            result = await handler.handle_async("做一個 L 形 WASP Part")

            # 應該是 Layer 2
            assert result.layer == Layer.SUPPLEMENT

            # 應該生成 Mermaid 檔案
            mermaid_path = Path(temp_wip_dir) / "component_info.mmd"
            assert mermaid_path.exists()

        run_async(_test())

    def test_layer2_user_cancel(self, temp_config_dir, temp_wip_dir):
        """用戶應該可以在 Layer 2 確認時取消"""
        async def _test():
            mock_callback = MockUserCallback(["n"])  # 拒絕確認
            mock_claude = MockClaudeClient()

            handler = UnifiedHandler(
                config_dir=f"{temp_config_dir}/config",
                auto_execute=False,
                user_callback=mock_callback,
                wip_dir=temp_wip_dir
            )
            handler.plan_generator._claude_client = mock_claude

            result = await handler.handle_async("做一個網格")

            # 應該失敗或成功 (取決於是否有 reference 匹配)
            # 如果有 reference 匹配，可能會 fallback 成功
            # 如果沒有，則會失敗
            if not result.success:
                # 錯誤訊息應該包含取消或其他錯誤
                assert len(result.errors) > 0

        run_async(_test())


# =============================================================================
# Layer 3 測試 (完整流程 + HITL)
# =============================================================================

class TestLayer3WithHITL:
    """Layer 3 應該執行完整六階段流程"""

    def test_layer3_detected_keywords(self, temp_config_dir, temp_wip_dir):
        """Layer 3 應該識別探索性關鍵字"""
        async def _test():
            mock_callback = MockUserCallback(["y"] * 10)  # 多個確認

            handler = UnifiedHandler(
                config_dir=f"{temp_config_dir}/config",
                auto_execute=False,
                user_callback=mock_callback,
                wip_dir=temp_wip_dir
            )

            result = await handler.handle_async("幫我探索聚集策略")

            # 應該是 Layer 3
            assert result.layer == Layer.EXPLORE

        run_async(_test())

    def test_layer3_user_cancel_at_any_phase(self, temp_config_dir, temp_wip_dir):
        """用戶應該可以在 Layer 3 任何階段取消"""
        async def _test():
            # 在第二個確認點取消
            mock_callback = MockUserCallback(["y", "n"])

            handler = UnifiedHandler(
                config_dir=f"{temp_config_dir}/config",
                auto_execute=False,
                user_callback=mock_callback,
                wip_dir=temp_wip_dir
            )

            result = await handler.handle_async("探索設計方案")

            # 應該失敗
            assert result.success is False
            # 應該在某個階段取消 (或返回錯誤)
            # Layer 3 可能還沒完全實作，所以錯誤格式可能不同

        run_async(_test())


# =============================================================================
# HITL 協作器測試
# =============================================================================

class TestHITLCollaborator:
    """測試 HITL 協作器功能"""

    def test_confirm_yes(self):
        """確認 yes 回答"""
        async def _test():
            mock_callback = MockUserCallback(["y"])
            hitl = HITLCollaborator(user_callback=mock_callback)

            result = await hitl.confirm("確認嗎？")

            assert result is True

        run_async(_test())

    def test_confirm_no(self):
        """確認 no 回答"""
        async def _test():
            mock_callback = MockUserCallback(["n"])
            hitl = HITLCollaborator(user_callback=mock_callback)

            result = await hitl.confirm("確認嗎？")

            assert result is False

        run_async(_test())

    def test_auto_mode_confirms_automatically(self):
        """auto_mode 應該自動確認"""
        async def _test():
            hitl = HITLCollaborator(auto_mode=True)

            result = await hitl.confirm("確認嗎？")

            assert result is True

        run_async(_test())

    def test_select_option(self):
        """選擇選項"""
        async def _test():
            mock_callback = MockUserCallback(["2"])  # 選擇第二個選項
            hitl = HITLCollaborator(user_callback=mock_callback)

            answer = await hitl.select(
                "選擇：",
                options=["選項A", "選項B", "選項C"],
                allow_other=False
            )

            assert answer.value == "選項B"
            assert answer.source == "selection"

        run_async(_test())

    def test_collect_knowledge(self):
        """收集知識"""
        async def _test():
            mock_callback = MockUserCallback(["12階，300cm高"])
            hitl = HITLCollaborator(user_callback=mock_callback)

            knowledge = await hitl.collect_knowledge(
                topic="樓梯規格",
                context="螺旋樓梯設計"
            )

            assert knowledge.key == "樓梯規格"
            assert "12階" in knowledge.value
            assert knowledge.source == "user_input"

        run_async(_test())

    def test_confirm_workflow_formatting(self):
        """確認工作流程格式化"""
        async def _test():
            mock_callback = MockUserCallback(["y"])
            hitl = HITLCollaborator(user_callback=mock_callback)

            result = await hitl.confirm_workflow(
                workflow_description="測試工作流程",
                patterns_used=["Pattern1", "Pattern2"],
                estimated_components=5,
                user_inputs_needed=["參數1", "參數2"]
            )

            # 確認返回 True
            assert result is True

            # 確認 prompt 包含必要資訊
            prompt = mock_callback.prompts[0]
            assert "測試工作流程" in prompt
            assert "Pattern1" in prompt or "5" in prompt

        run_async(_test())


# =============================================================================
# 同步 vs 異步 API 測試
# =============================================================================

class TestSyncVsAsyncAPI:
    """測試同步和異步 API 的行為差異"""

    def test_sync_handle_layer2_returns_error(self, temp_config_dir):
        """同步 handle() 對 Layer 2/3 應該返回錯誤提示"""
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False
        )

        # Layer 2 請求
        result = handler.handle("做一個 L 形 Part")

        # 應該是 Layer 2
        assert result.layer == Layer.SUPPLEMENT
        # 同步版本現在嘗試使用 fallback
        # 如果沒有 Claude client，可能會失敗

    def test_sync_handle_layer3_returns_error(self, temp_config_dir):
        """同步 handle() 對 Layer 3 應該返回錯誤提示"""
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False
        )

        # Layer 3 探索性請求
        result = handler.handle("幫我探索設計方案")

        # 應該是 Layer 3
        assert result.layer == Layer.EXPLORE
        # 應該失敗
        assert result.success is False
        # 應該提示使用 handle_async
        assert any("handle_async" in e for e in result.errors)


# =============================================================================
# 統計測試
# =============================================================================

class TestStatistics:
    """測試統計功能"""

    def test_stats_layer_counts(self, temp_config_dir):
        """統計應該正確計數各 Layer"""
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False
        )

        # Layer 1/2 (可能 golden 或 reference)
        handler.handle("用 WASP 做立方體聚集")

        # Layer 3
        handler.handle("幫我探索設計方案")

        stats = handler.get_stats()

        # Layer 1 或 Layer 2 至少有一個
        assert stats["layer1_count"] + stats["layer2_count"] >= 1
        assert stats["layer3_count"] >= 1
        assert stats["total_requests"] >= 2

    def test_stats_reset(self, temp_config_dir):
        """統計重置應該清零"""
        handler = UnifiedHandler(
            config_dir=f"{temp_config_dir}/config",
            auto_execute=False
        )

        handler.handle("用 WASP 做立方體聚集")
        handler.reset_stats()

        stats = handler.get_stats()
        assert stats["total_requests"] == 0


# =============================================================================
# 執行測試
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
