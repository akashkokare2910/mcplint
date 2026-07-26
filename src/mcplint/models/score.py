"""The explainable 0-100 overall score. Not a scientifically validated metric —
a weighted, documented heuristic meant to make regressions visible at a glance.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreDeduction(BaseModel):
    category: str
    points_lost: float
    finding_count: int
    explanation: str


class ScoreBreakdown(BaseModel):
    total_score: int = Field(ge=0, le=100)
    deductions: list[ScoreDeduction] = Field(default_factory=list)
    benchmark_accuracy: float | None = None
    disclaimer: str = (
        "This score is an explainable heuristic, not a scientifically validated "
        "or universal quality metric. Use the deductions below to see exactly "
        "why points were lost."
    )
