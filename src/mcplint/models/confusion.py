"""Typed models for tool-selection confusion analysis."""

from __future__ import annotations

from pydantic import BaseModel

from mcplint.models.common import ArtifactMetadata

CONFUSION_SCHEMA_VERSION = "1.0"


class ConfusionPair(BaseModel):
    tool_a: str
    tool_b: str
    ambiguity_score: float
    predicted: bool
    observed_confusions: int
    relevant_trials: int
    observed_confusion_rate: float
    confirmed: bool
    surprising: bool


class ConfusionAnalysis(BaseModel):
    metadata: ArtifactMetadata
    dataset_name: str
    ambiguity_threshold: float
    pairs: list[ConfusionPair]
