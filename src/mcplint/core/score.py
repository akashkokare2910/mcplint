"""Computes the explainable 0-100 overall score documented in models/score.py.

Weighting (out of 100, each category capped independently, then summed and
clamped to [0, 100]):

  - critical/error findings (not already counted below): up to 40 points,
    8 points per finding.
  - warning/info findings (not already counted below): up to 20 points,
    2 points per finding.
  - ambiguity (`ambiguous-tool-overlap`, `missing-tool-distinction`):
    up to 15 points, 5 points per finding.
  - schema completeness (`missing-parameter-description`,
    `undocumented-required-constraint`, `schema-description-type-conflict`):
    up to 15 points, 3 points per finding.
  - safety clarity (`tool-name-action-conflict`,
    `destructive-tool-without-warning`, `state-changing-tool-marked-read-only`):
    up to 15 points, 5 points per finding.
  - benchmark accuracy (only when a BenchmarkResult is supplied): up to 15
    points, proportional to (1 - exact_tool_selection_accuracy).

These weights are a documented, adjustable heuristic — not a scientifically
derived formula. They exist so a regression in any one category is visible
without being able to silently zero out the score.
"""

from __future__ import annotations

from mcplint.models.benchmark import BenchmarkResult
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.models.score import ScoreBreakdown, ScoreDeduction

AMBIGUITY_RULE_IDS = frozenset({"ambiguous-tool-overlap", "missing-tool-distinction"})
SCHEMA_RULE_IDS = frozenset(
    {
        "missing-parameter-description",
        "undocumented-required-constraint",
        "schema-description-type-conflict",
    }
)
SAFETY_RULE_IDS = frozenset(
    {
        "tool-name-action-conflict",
        "destructive-tool-without-warning",
        "state-changing-tool-marked-read-only",
    }
)

_ERROR_POINTS_PER_FINDING = 8.0
_ERROR_CATEGORY_CAP = 40.0
_WARNING_POINTS_PER_FINDING = 2.0
_WARNING_CATEGORY_CAP = 20.0
_AMBIGUITY_POINTS_PER_FINDING = 5.0
_AMBIGUITY_CATEGORY_CAP = 15.0
_SCHEMA_POINTS_PER_FINDING = 3.0
_SCHEMA_CATEGORY_CAP = 15.0
_SAFETY_POINTS_PER_FINDING = 5.0
_SAFETY_CATEGORY_CAP = 15.0
_BENCHMARK_CATEGORY_CAP = 15.0


def _category(finding: Finding) -> str:
    if finding.rule_id in AMBIGUITY_RULE_IDS:
        return "ambiguity"
    if finding.rule_id in SCHEMA_RULE_IDS:
        return "schema_completeness"
    if finding.rule_id in SAFETY_RULE_IDS:
        return "safety_clarity"
    if finding.severity == Severity.ERROR:
        return "critical_error"
    return "warning_info"


def compute_score(
    report: LintReport, benchmark_result: BenchmarkResult | None = None
) -> ScoreBreakdown:
    counts: dict[str, int] = {}
    for finding in report.findings:
        category = _category(finding)
        counts[category] = counts.get(category, 0) + 1

    deductions: list[ScoreDeduction] = []

    def _add(category: str, label: str, per_finding: float, cap: float) -> None:
        count = counts.get(category, 0)
        if count == 0:
            return
        points = min(cap, count * per_finding)
        deductions.append(
            ScoreDeduction(
                category=category,
                points_lost=points,
                finding_count=count,
                explanation=(
                    f"{count} {label} finding(s) x {per_finding:.0f} pts "
                    f"(capped at {cap:.0f})"
                ),
            )
        )

    _add("critical_error", "critical/error", _ERROR_POINTS_PER_FINDING, _ERROR_CATEGORY_CAP)
    _add("warning_info", "warning/info", _WARNING_POINTS_PER_FINDING, _WARNING_CATEGORY_CAP)
    _add("ambiguity", "ambiguity", _AMBIGUITY_POINTS_PER_FINDING, _AMBIGUITY_CATEGORY_CAP)
    _add(
        "schema_completeness",
        "schema-completeness",
        _SCHEMA_POINTS_PER_FINDING,
        _SCHEMA_CATEGORY_CAP,
    )
    _add("safety_clarity", "safety-clarity", _SAFETY_POINTS_PER_FINDING, _SAFETY_CATEGORY_CAP)

    benchmark_accuracy: float | None = None
    if benchmark_result is not None:
        benchmark_accuracy = benchmark_result.exact_tool_selection_accuracy
        benchmark_points = round((1 - benchmark_accuracy) * _BENCHMARK_CATEGORY_CAP, 1)
        if benchmark_points > 0:
            deductions.append(
                ScoreDeduction(
                    category="benchmark_accuracy",
                    points_lost=benchmark_points,
                    finding_count=0,
                    explanation=(
                        f"exact tool-selection accuracy {benchmark_accuracy:.0%} "
                        f"(up to {_BENCHMARK_CATEGORY_CAP:.0f} pts)"
                    ),
                )
            )

    total_deducted = sum(d.points_lost for d in deductions)
    total_score = max(0, min(100, round(100 - total_deducted)))

    return ScoreBreakdown(
        total_score=total_score, deductions=deductions, benchmark_accuracy=benchmark_accuracy
    )
