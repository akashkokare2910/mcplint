"""Typed models for contract mutation testing.

A mutation is "killed" when the benchmark's exact tool-selection accuracy
drops by at least the configured threshold after the mutation is applied;
otherwise it "survives", meaning the eval suite failed to notice a
regression it should have caught.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from mcplint.models.common import ArtifactMetadata

MUTATION_REPORT_SCHEMA_VERSION = "1.0"


class MutationResult(BaseModel):
    mutator_id: str
    tool_name: str
    baseline_accuracy: float
    mutated_accuracy: float
    accuracy_drop: float
    killed: bool


class MutationTestingReport(BaseModel):
    metadata: ArtifactMetadata
    dataset_name: str
    kill_threshold: float
    results: list[MutationResult] = Field(default_factory=list)
    survival_rate: float
