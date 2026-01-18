#!/usr/bin/env python3
"""
Test Superpower Integration

驗證 Superpowers + Claudesidian + Baoyu-skills 整合
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_intent_router():
    """Test IntentRouter classification"""
    print("\n=== Test: Intent Router ===")

    from grasshopper_mcp.langgraph.core.intent_router import IntentRouter, IntentType

    router = IntentRouter()

    test_cases = [
        ("brainstorm ideas for a parametric chair", IntentType.BRAINSTORM),
        ("/think what makes a good table design", IntentType.THINK_PARTNER),
        ("/brainstorm creative furniture concepts", IntentType.BRAINSTORM),
        ("create a simple box", IntentType.WORKFLOW),
        ("create a custom tool for spiral patterns", IntentType.META_AGENT),
        ("build a parametric table with sliders", IntentType.WORKFLOW),
    ]

    for task, expected in test_cases:
        result = router.classify(task, {})
        status = "✓" if result.intent_type == expected else "✗"
        print(f"{status} '{task[:40]}...' -> {result.intent_type.value} (expected: {expected.value})")
        print(f"   Confidence: {result.confidence:.2f}, Keywords: {result.matched_keywords}")


def test_mode_selector():
    """Test ModeSelector"""
    print("\n=== Test: Mode Selector ===")

    from grasshopper_mcp.langgraph.core.mode_selector import ModeSelector, select_mode

    selector = ModeSelector()

    test_cases = [
        "brainstorm ideas for a modern seesaw",
        "create a parametric cup with handles",
        "explore what makes furniture ergonomic",
    ]

    for task in test_cases:
        result = selector.select(task, {})
        print(f"Task: '{task[:40]}...'")
        print(f"  Mode: {result.intent_type.value}")
        print(f"  Strategy: {result.strategy.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Ask clarification: {result.should_ask_clarification}")
        if result.clarification_question:
            print(f"  Question: {result.clarification_question[:60]}...")
        print()


def test_think_partner():
    """Test Think-Partner node"""
    print("\n=== Test: Think-Partner Node ===")

    from grasshopper_mcp.langgraph.state import create_initial_state
    from grasshopper_mcp.langgraph.nodes.think_partner import (
        think_partner_node,
        enter_think_partner_mode,
    )

    state = create_initial_state("ergonomic chair")
    state = {**state, **enter_think_partner_mode(state)}

    print(f"Thinking mode: {state.get('thinking_mode')}")

    result = think_partner_node(state)

    print(f"Questions generated: {len(result.get('thinking_log', []))}")
    if result.get('pending_decisions'):
        decision = result['pending_decisions'][-1]
        print(f"Question: {decision['question'][:100]}...")
        print(f"Options: {decision['options']}")


def test_brainstorm():
    """Test Brainstorm node"""
    print("\n=== Test: Brainstorm Node ===")

    from grasshopper_mcp.langgraph.state import create_initial_state
    from grasshopper_mcp.langgraph.nodes.brainstorm import (
        brainstorm_node,
        enter_brainstorm_mode,
    )

    state = create_initial_state("parametric table")
    state = {**state, **enter_brainstorm_mode(state)}

    print(f"Brainstorm phase: {state.get('brainstorm_phase')}")

    # Phase 1: Understanding
    result = brainstorm_node(state)
    print(f"After Understanding phase:")
    print(f"  Awaiting confirmation: {result.get('awaiting_confirmation')}")
    if result.get('pending_decisions'):
        decision = result['pending_decisions'][-1]
        print(f"  Question: {decision['question'][:80]}...")


def test_meta_agent():
    """Test Meta-Agent node"""
    print("\n=== Test: Meta-Agent Node ===")

    from grasshopper_mcp.langgraph.state import create_initial_state
    from grasshopper_mcp.langgraph.nodes.meta_agent import (
        meta_agent_node,
        enter_meta_agent_mode,
    )

    state = create_initial_state("spiral pattern tool")
    state = {**state, **enter_meta_agent_mode(state)}

    print(f"Meta-Agent active: {state.get('meta_agent_active')}")
    print(f"Operation: {state.get('meta_agent_operation')}")

    result = meta_agent_node(state)
    print(f"Retrieved tools: {len(result.get('retrieved_tools', []))}")
    if result.get('pending_decisions'):
        decision = result['pending_decisions'][-1]
        print(f"Question: {decision['question'][:80]}...")


def test_workflow_pipeline():
    """Test Workflow Pipeline nodes"""
    print("\n=== Test: Workflow Pipeline ===")

    from grasshopper_mcp.langgraph.state import create_initial_state
    from grasshopper_mcp.langgraph.nodes.workflow_pipeline import (
        intent_decomposition_node,
        tool_retrieval_node,
        prompt_generation_node,
        config_assembly_node,
        enter_workflow_mode,
    )

    state = create_initial_state("simple table")
    state = {**state, **enter_workflow_mode(state)}

    print(f"Current stage: {state.get('current_stage')}")

    # Stage 1: Decomposition
    result = intent_decomposition_node(state)
    state = {**state, **result}
    print(f"Stage 1 - Subtasks: {len(state.get('subtasks', []))}")

    # Stage 2: Tool Retrieval
    result = tool_retrieval_node(state)
    state = {**state, **result}
    print(f"Stage 2 - Tools: {len(state.get('retrieved_tools', []))}")
    print(f"Stage 2 - Joseki: {len(state.get('joseki_patterns', []))}")

    # Stage 3: Prompt Generation
    result = prompt_generation_node(state)
    state = {**state, **result}
    print(f"Stage 3 - Prompts: {len(state.get('execution_prompts', []))}")

    # Stage 4: Config Assembly
    result = config_assembly_node(state)
    state = {**state, **result}
    placement = state.get('placement_info', {})
    print(f"Stage 4 - Components: {len(placement.get('components', []))}")
    print(f"Stage 4 - Connections: {len(placement.get('connections', []))}")


def test_multi_mode_workflow():
    """Test Multi-Mode Workflow"""
    print("\n=== Test: Multi-Mode Workflow ===")

    from grasshopper_mcp.langgraph.graphs.multi_mode_workflow import (
        run_multi_mode_workflow,
    )

    # Test with a brainstorm request
    state = run_multi_mode_workflow(
        topic="parametric seesaw",
        requirements="should have adjustable balance point"
    )

    print(f"Intent type: {state.get('intent_type')}")
    final_proposal = state.get('final_proposal') or ''
    print(f"Final proposal length: {len(final_proposal)}")
    print(f"Errors/log entries: {len(state.get('errors', []))}")

    # Print last few log entries
    errors = state.get('errors', [])
    print("\nLast 3 log entries:")
    for e in errors[-3:]:
        print(f"  - {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Superpower Integration Tests")
    print("=" * 60)

    try:
        test_intent_router()
        test_mode_selector()
        test_think_partner()
        test_brainstorm()
        test_meta_agent()
        test_workflow_pipeline()
        test_multi_mode_workflow()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
