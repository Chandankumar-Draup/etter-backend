"""
Central automation score computation utilities.

All automation-related scores in the Digital Twin graph are stored on a
0–100 scale (0 = fully manual, 100 = fully automated).  This module
provides the single source-of-truth helpers that every layer — API,
chat engine, aggregation — should use to compute, normalise, and format
these values.

Usage:
    from draup_world_model.digital_twin.automation import (
        weighted_automation_score,
        normalize_automation_value,
        format_automation_pct,
    )
"""

from typing import Any, Dict, List, Optional, Sequence

# ── Scale constants ─────────────────────────────────────────────────
#
# Automation scores are stored as floats on a 0–100 scale everywhere:
#   - DTTask.automation_potential       (0–100)
#   - DTWorkload.computed_automation_score (0–100)
#   - DTRole.automation_score / computed_automation_score (0–100)
#   - DTJobFamily / Group / SubFunction / Function / Organization (0–100)
#
# The only exception is raw LLM-generated Cypher — which may produce
# values outside the expected range if it multiplies by 100 again.

AUTOMATION_MIN = 0.0
AUTOMATION_MAX = 100.0


def weighted_automation_score(
    children: Sequence[Dict[str, Any]],
    score_key: str = "automation_score",
    weight_key: str = "headcount",
) -> float:
    """
    Compute a headcount-weighted automation score from child entities.

    This is the standard roll-up formula used at every taxonomy level:
        Function ← SubFunction ← JobFamilyGroup ← JobFamily ← Role

    Args:
        children: Sequence of dicts, each with ``score_key`` and ``weight_key``.
        score_key: Dict key for the automation score (0–100).
        weight_key: Dict key for the weighting factor (typically headcount).

    Returns:
        Weighted average rounded to 1 decimal place, or 0.0 if
        total weight is zero.
    """
    total_weight = sum(c.get(weight_key, 0) or 0 for c in children)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(
        (c.get(score_key, 0) or 0) * (c.get(weight_key, 0) or 0)
        for c in children
    )
    return round(weighted_sum / total_weight, 1)


def normalize_automation_value(value: Any) -> Optional[float]:
    """
    Normalise an automation score to the canonical 0–100 scale.

    Handles the two representations that may appear in Cypher results:
        - 0–100 scale  → returned as-is (rounded to 1 dp)
        - 0.0–1.0 scale → multiplied by 100

    Values above 100 (e.g. 7200 from an erroneous ``* 100`` in Cypher)
    are divided by 100 to recover the intended percentage.

    Returns ``None`` for non-numeric input.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None

    if v > AUTOMATION_MAX:
        # Likely a double-multiplication artefact (e.g. 7200 → 72)
        v = v / 100.0
        # If still above 100, keep dividing (e.g. 720000 → 72)
        while v > AUTOMATION_MAX:
            v = v / 100.0
    elif 0.0 < v <= 1.0:
        # Looks like 0–1 scale — convert to 0–100
        v = v * 100.0

    return round(max(AUTOMATION_MIN, min(v, AUTOMATION_MAX)), 1)


def format_automation_pct(value: Any) -> str:
    """
    Format an automation score as a human-readable percentage string.

    Examples:
        72.3  → "72%"
        0.65  → "65%"
        7200  → "72%"
        None  → "-"
    """
    normalised = normalize_automation_value(value)
    if normalised is None:
        return "-"
    return f"{round(normalised)}%"


def resolve_automation_score(props: Dict[str, Any]) -> Optional[float]:
    """
    Pick the best automation score from a node's property dict.

    Priority order (matches Explorer.js ``roleAutomationValue``):
        1. computed_automation_score  (bottom-up aggregated)
        2. automation_score           (static / ingested)
        3. automation_potential       (task-level)

    Returns the normalised 0–100 value, or ``None`` if no score exists.
    """
    for key in ("computed_automation_score", "automation_score", "automation_potential"):
        val = props.get(key)
        if val is not None:
            return normalize_automation_value(val)
    return None


def normalize_result_rows(
    rows: List[Dict[str, Any]],
    score_columns: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Post-process Cypher result rows, normalising automation-related columns.

    Automatically detects columns whose names contain ``automation`` or
    ``auto_pct`` and normalises their values to the 0–100 scale.

    Args:
        rows: List of row dicts from a Cypher query.
        score_columns: Explicit list of column names to normalise.
            If ``None``, columns are auto-detected by name.

    Returns:
        A new list of row dicts with automation values normalised.
    """
    if not rows:
        return rows

    # Auto-detect columns if not specified
    if score_columns is None:
        sample = rows[0]
        score_columns = [
            k for k in sample.keys()
            if any(tok in k.lower() for tok in ("automation", "auto_pct", "auto_score"))
        ]

    if not score_columns:
        return rows

    out = []
    for row in rows:
        new_row = dict(row)
        for col in score_columns:
            if col in new_row and new_row[col] is not None:
                new_row[col] = normalize_automation_value(new_row[col])
        out.append(new_row)
    return out
