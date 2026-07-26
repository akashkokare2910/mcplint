"""Typed models for comparing two MCPServerSnapshots (and optionally two benchmark runs)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mcplint.models.common import ArtifactMetadata
from mcplint.models.findings import Finding


class SchemaChange(BaseModel):
    tool_name: str
    json_path: str
    before: object
    after: object


class DescriptionChange(BaseModel):
    tool_name: str
    before: str | None
    after: str | None


class AmbiguityScoreChange(BaseModel):
    tool_a: str
    tool_b: str
    before: float
    after: float


class ComparisonReport(BaseModel):
    metadata: ArtifactMetadata
    baseline_server_name: str
    candidate_server_name: str
    added_tools: list[str] = Field(default_factory=list)
    removed_tools: list[str] = Field(default_factory=list)
    schema_changes: list[SchemaChange] = Field(default_factory=list)
    description_changes: list[DescriptionChange] = Field(default_factory=list)
    new_findings: list[Finding] = Field(default_factory=list)
    resolved_findings: list[Finding] = Field(default_factory=list)
    ambiguity_score_changes: list[AmbiguityScoreChange] = Field(default_factory=list)

    benchmark_dataset_name: str | None = None
    baseline_accuracy: float | None = None
    candidate_accuracy: float | None = None
    benchmark_accuracy_delta: float | None = None
    argument_validity_delta: float | None = None
    latency_delta_ms: float | None = None
    cost_delta: float | None = None
    regressions_by_case: dict[str, str] = Field(default_factory=dict)

    min_accuracy_delta_threshold: float | None = None
    passes_ci_threshold: bool | None = None
