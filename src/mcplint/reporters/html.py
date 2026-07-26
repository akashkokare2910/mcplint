"""Render a standalone HTML report — no backend, embedded CSS, no external requests."""

from __future__ import annotations

from importlib import resources

from jinja2 import Environment, FileSystemLoader, select_autoescape

from mcplint.core.rules.ambiguity import (
    DEFAULT_AMBIGUITY_THRESHOLD,
    AmbiguityPairResult,
    compute_ambiguity,
)
from mcplint.core.score import compute_score
from mcplint.models.benchmark import BenchmarkResult
from mcplint.models.comparison import ComparisonReport
from mcplint.models.findings import LintReport
from mcplint.models.fixes import RewriteSuggestion
from mcplint.models.snapshot import MCPServerSnapshot


def _score_class(total_score: int) -> str:
    if total_score >= 80:
        return "good"
    if total_score >= 50:
        return "ok"
    return "bad"


def _ambiguity_pairs(
    snapshot: MCPServerSnapshot, threshold: float
) -> list[AmbiguityPairResult]:
    pairs: list[AmbiguityPairResult] = []
    tools = sorted(snapshot.tools, key=lambda t: t.name)
    for index, tool_a in enumerate(tools):
        for tool_b in tools[index + 1 :]:
            result = compute_ambiguity(tool_a, tool_b)
            if result.score >= threshold:
                pairs.append(result)
    return pairs


def render_html_report(
    snapshot: MCPServerSnapshot,
    report: LintReport,
    *,
    benchmark_result: BenchmarkResult | None = None,
    comparison: ComparisonReport | None = None,
    suggestions: list[RewriteSuggestion] | None = None,
    ambiguity_threshold: float = DEFAULT_AMBIGUITY_THRESHOLD,
) -> str:
    template_dir = resources.files("mcplint.reporters") / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
    )
    template = env.get_template("report.html.j2")

    score = compute_score(report, benchmark_result)

    return template.render(
        server_name=snapshot.server_name,
        generated_at=report.metadata.generated_at.isoformat(),
        mcplint_version=report.metadata.mcplint_version,
        score=score,
        score_class=_score_class(score.total_score),
        findings=report.findings,
        tools=snapshot.tools,
        ambiguity_pairs=_ambiguity_pairs(snapshot, ambiguity_threshold),
        benchmark=benchmark_result,
        comparison=comparison,
        suggestions=suggestions or [],
    )
