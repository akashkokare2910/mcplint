from datetime import UTC, datetime

from mcplint.core.score import compute_score
from mcplint.models.benchmark import BenchmarkResult
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity


def _finding(rule_id: str, severity: Severity, tool_name: str = "t") -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        message="m",
        evidence="e",
        location=SourceLocation(tool_name=tool_name, json_path="$"),
        remediation="r",
        confidence=1.0,
    )


def _report(findings: list[Finding]) -> LintReport:
    return LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="s",
        findings=findings,
    )


def test_score_clean_report_is_100() -> None:
    breakdown = compute_score(_report([]))
    assert breakdown.total_score == 100
    assert breakdown.deductions == []


def test_score_deducts_for_error_findings() -> None:
    findings = [_finding("missing-tool-description", Severity.ERROR)]
    breakdown = compute_score(_report(findings))
    assert breakdown.total_score == 92
    assert breakdown.deductions[0].category == "critical_error"


def test_score_error_category_is_capped() -> None:
    findings = [_finding("missing-tool-description", Severity.ERROR) for _ in range(20)]
    breakdown = compute_score(_report(findings))
    error_deduction = next(d for d in breakdown.deductions if d.category == "critical_error")
    assert error_deduction.points_lost == 40.0
    assert breakdown.total_score == 60


def test_score_ambiguity_and_safety_are_not_double_counted_as_generic() -> None:
    findings = [
        _finding("ambiguous-tool-overlap", Severity.WARNING),
        _finding("destructive-tool-without-warning", Severity.ERROR),
    ]
    breakdown = compute_score(_report(findings))
    categories = {d.category for d in breakdown.deductions}
    assert categories == {"ambiguity", "safety_clarity"}
    assert breakdown.total_score == 90


def test_score_never_goes_below_zero() -> None:
    findings = [_finding("missing-tool-description", Severity.ERROR) for _ in range(5)] + [
        _finding("ambiguous-tool-overlap", Severity.WARNING) for _ in range(5)
    ] + [
        _finding("tool-name-action-conflict", Severity.ERROR) for _ in range(5)
    ] + [
        _finding("missing-parameter-description", Severity.WARNING) for _ in range(5)
    ] + [
        _finding("description-repeats-name", Severity.WARNING) for _ in range(20)
    ]
    breakdown = compute_score(_report(findings))
    assert breakdown.total_score == 0


def _benchmark_result(accuracy: float) -> BenchmarkResult:
    return BenchmarkResult(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        dataset_name="d",
        provider="fake",
        model="fake-model",
        runs_per_case=1,
        trials=[],
        exact_tool_selection_accuracy=accuracy,
        valid_argument_rate=1.0,
        required_argument_accuracy=1.0,
        forbidden_tool_invocation_rate=0.0,
        no_tool_rate=0.0,
        mean_latency_ms=0.0,
        p95_latency_ms=0.0,
        total_estimated_cost=None,
        per_case_pass_rate={},
        stability={},
    )


def test_score_deducts_for_low_benchmark_accuracy() -> None:
    breakdown = compute_score(_report([]), _benchmark_result(0.5))
    assert breakdown.total_score == 92
    assert breakdown.benchmark_accuracy == 0.5


def test_score_no_benchmark_deduction_at_perfect_accuracy() -> None:
    breakdown = compute_score(_report([]), _benchmark_result(1.0))
    assert breakdown.total_score == 100
    assert breakdown.deductions == []
