"""Render a LintReport as JSON."""

from __future__ import annotations

from mcplint.models.findings import LintReport


def render_json(report: LintReport) -> str:
    return report.model_dump_json(indent=2)
