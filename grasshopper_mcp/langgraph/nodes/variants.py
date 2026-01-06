"""
Multi-Variant Exploration Nodes

Implements Option B: Multi-Variant Design Exploration
"""

from typing import Any
from ..state import DesignState, DesignVariant
import uuid
import copy


def generate_variants_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Generate multiple design variants

    This node:
    1. Analyzes base design
    2. Identifies variable parameters
    3. Generates N variants with different parameter combinations
    4. Prepares variants for parallel evaluation

    Returns list of DesignVariant objects
    """
    component_info = state.get("component_info_mmd", "")
    placement_info = state.get("placement_info", {})
    max_variants = state.get("max_iterations", 5)  # Reuse max_iterations for variant count

    # Generate variants
    variants = _generate_design_variants(
        component_info,
        placement_info,
        num_variants=max_variants
    )

    return {
        "variants": variants,
        "current_stage": "execution",  # Move to evaluate variants
    }


def evaluate_variants_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Evaluate all design variants

    This node:
    1. Executes each variant (or simulates)
    2. Collects errors and results
    3. Calculates quality scores
    4. Updates variant records

    Can be parallelized for efficiency
    """
    variants = state.get("variants", [])

    if not variants:
        return {
            "errors": ["No variants to evaluate"],
            "current_stage": "connectivity",
        }

    # Evaluate each variant
    evaluated_variants = []
    all_errors = []

    for variant in variants:
        result = _evaluate_variant(variant)
        evaluated_variant = DesignVariant(
            variant_id=variant["variant_id"],
            parameters=variant["parameters"],
            placement_info=variant.get("placement_info"),
            execution_result=result,
            quality_score=result.get("quality_score", 0.0),
            errors=result.get("errors", [])
        )
        evaluated_variants.append(evaluated_variant)

        if result.get("errors"):
            all_errors.extend([
                f"Variant {variant['variant_id']}: {e}"
                for e in result["errors"]
            ])

    return {
        "variants": evaluated_variants,
        "errors": all_errors,
        "current_stage": "evaluation",
    }


def select_best_variant_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Select the best variant

    This node:
    1. Compares quality scores
    2. Considers error counts
    3. Selects best variant
    4. Optionally triggers further optimization of selected variant

    Returns selected variant and recommendation
    """
    variants = state.get("variants", [])

    if not variants:
        return {
            "errors": ["No variants to select from"],
            "current_stage": "connectivity",
        }

    # Filter out failed variants
    valid_variants = [v for v in variants if v["quality_score"] > 0]

    if not valid_variants:
        return {
            "errors": ["All variants failed evaluation"],
            "awaiting_confirmation": True,
            "confirmation_reason": "all_variants_failed",
            "current_stage": "connectivity",
        }

    # Select best by quality score
    best_variant = max(valid_variants, key=lambda v: v["quality_score"])

    # Generate comparison report
    comparison_report = _generate_comparison_report(variants, best_variant)

    return {
        "selected_variant_id": best_variant["variant_id"],
        "final_proposal": comparison_report,
        "awaiting_confirmation": True,
        "confirmation_reason": "variant_selected",
        "current_stage": "evaluation",
    }


def _generate_design_variants(
    component_info: str,
    placement_info: dict,
    num_variants: int = 5
) -> list[DesignVariant]:
    """
    Generate design variants with different parameter combinations

    Strategies:
    1. Random variation within bounds
    2. Grid sampling of parameter space
    3. Evolutionary/genetic variation
    4. Targeted variation based on objectives
    """
    variants = []

    # Identify variable parameters from component_info
    variable_params = _extract_variable_parameters(component_info)

    for i in range(num_variants):
        # Generate parameter variation
        varied_params = _vary_parameters(variable_params, strategy="random", seed=i)

        # Create variant
        variant = DesignVariant(
            variant_id=f"variant_{i+1}_{uuid.uuid4().hex[:8]}",
            parameters=varied_params,
            placement_info=_apply_parameters_to_placement(placement_info, varied_params),
            execution_result=None,
            quality_score=0.0,
            errors=[]
        )
        variants.append(variant)

    return variants


def _extract_variable_parameters(component_info: str) -> dict:
    """
    Extract variable parameters from component_info.mmd

    Looks for:
    - Number Slider components
    - Parameters marked as "variable"
    - Configurable values
    """
    # Placeholder: Parse component_info for sliders
    # In production, use proper MMD parsing

    default_params = {
        "width": {"value": 100, "min": 50, "max": 200},
        "length": {"value": 100, "min": 50, "max": 200},
        "height": {"value": 75, "min": 40, "max": 120},
        "leg_radius": {"value": 5, "min": 2, "max": 10},
    }

    return default_params


def _vary_parameters(
    base_params: dict,
    strategy: str = "random",
    seed: int = 0
) -> dict:
    """
    Create a variation of parameters

    Strategies:
    - random: Random values within bounds
    - grid: Systematic grid sampling
    - extreme: Test boundary conditions
    """
    import random
    random.seed(seed)

    varied = {}

    for name, param in base_params.items():
        min_val = param.get("min", param["value"] * 0.5)
        max_val = param.get("max", param["value"] * 1.5)

        if strategy == "random":
            varied[name] = random.uniform(min_val, max_val)
        elif strategy == "extreme":
            # Alternate between min and max
            varied[name] = min_val if seed % 2 == 0 else max_val
        else:  # grid
            # Divide range into num_variants steps
            step = (max_val - min_val) / 5
            varied[name] = min_val + step * (seed % 5)

    return varied


def _apply_parameters_to_placement(
    placement_info: dict,
    parameters: dict
) -> dict:
    """
    Apply parameter variations to placement_info

    Updates slider values and other configurable components
    """
    if not placement_info:
        return {}

    # Deep copy to avoid modifying original
    varied_placement = copy.deepcopy(placement_info)

    # Update commands that reference parameters
    commands = varied_placement.get("commands", [])
    for cmd in commands:
        if cmd.get("type") == "set_slider":
            param_name = cmd.get("component_id", "").lower()
            for key, value in parameters.items():
                if key in param_name:
                    cmd["value"] = value
                    break

    return varied_placement


def _evaluate_variant(variant: DesignVariant) -> dict:
    """
    Evaluate a single design variant

    In production, this would:
    1. Execute the variant's placement_info
    2. Check for errors
    3. Evaluate quality metrics (geometry validity, aesthetics, etc.)
    4. Return comprehensive result

    Returns:
    {
        "success": bool,
        "quality_score": float,  # 0.0 to 1.0
        "errors": list[str],
        "metrics": dict
    }
    """
    # Placeholder evaluation
    # In production, integrate with actual executor and evaluator

    import random
    random.seed(hash(variant["variant_id"]))

    # Simulate evaluation
    success = random.random() > 0.2  # 80% success rate
    quality = random.uniform(0.5, 1.0) if success else 0.0

    errors = []
    if not success:
        errors.append("Simulated execution failure")

    return {
        "success": success,
        "quality_score": quality,
        "errors": errors,
        "metrics": {
            "geometry_valid": success,
            "connections_valid": success,
            "aesthetic_score": quality * 0.9,
            "efficiency_score": quality * 0.85,
        }
    }


def _generate_comparison_report(
    variants: list[DesignVariant],
    best_variant: DesignVariant
) -> str:
    """
    Generate a comparison report of all variants

    Includes:
    - Summary of each variant
    - Quality scores
    - Recommendation
    """
    report_lines = [
        "# Multi-Variant Comparison Report\n",
        f"## Evaluated {len(variants)} variants\n",
        "| Variant | Quality Score | Status | Parameters |",
        "|---------|--------------|--------|------------|",
    ]

    for v in sorted(variants, key=lambda x: x["quality_score"], reverse=True):
        status = "✅ Best" if v["variant_id"] == best_variant["variant_id"] else (
            "✓ Valid" if v["quality_score"] > 0 else "❌ Failed"
        )
        params_str = ", ".join([
            f"{k}={v:.1f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in list(v["parameters"].items())[:3]
        ])
        report_lines.append(
            f"| {v['variant_id'][:20]} | {v['quality_score']:.2f} | {status} | {params_str} |"
        )

    report_lines.extend([
        "\n## Recommendation\n",
        f"**Selected Variant**: {best_variant['variant_id']}",
        f"**Quality Score**: {best_variant['quality_score']:.2f}",
        "\n### Parameters",
    ])

    for k, v in best_variant["parameters"].items():
        report_lines.append(f"- {k}: {v:.2f}" if isinstance(v, float) else f"- {k}: {v}")

    report_lines.extend([
        "\n### Next Steps",
        "1. Review the selected variant",
        "2. Optionally run additional optimization on selected variant",
        "3. Execute final placement with approved parameters",
    ])

    return "\n".join(report_lines)
