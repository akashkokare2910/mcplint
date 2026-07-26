"""Typed models for the benchmark dataset format, provider results, and scoring."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mcplint.models.common import ArtifactMetadata


class ExpectedToolCall(BaseModel):
    tool: str
    arguments: dict[str, object] = Field(default_factory=dict)
    forbidden_tools: list[str] = Field(default_factory=list)
    argument_assertions: dict[str, object] = Field(default_factory=dict)

    def all_expected_arguments(self) -> dict[str, object]:
        return {**self.arguments, **self.argument_assertions}


class BenchmarkCase(BaseModel):
    id: str
    prompt: str
    expected: ExpectedToolCall


class BenchmarkDataset(BaseModel):
    name: str
    version: str
    cases: list[BenchmarkCase]


class ActualToolCall(BaseModel):
    tool: str | None
    arguments: dict[str, object] = Field(default_factory=dict)
    valid_arguments: bool = True
    error: str | None = None
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None


class BenchmarkTrial(BaseModel):
    case_id: str
    trial_index: int
    actual: ActualToolCall
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)


class BenchmarkResult(BaseModel):
    metadata: ArtifactMetadata
    dataset_name: str
    provider: str
    model: str
    runs_per_case: int
    trials: list[BenchmarkTrial]
    exact_tool_selection_accuracy: float
    valid_argument_rate: float
    required_argument_accuracy: float
    forbidden_tool_invocation_rate: float
    no_tool_rate: float
    mean_latency_ms: float
    p95_latency_ms: float
    total_estimated_cost: float | None
    per_case_pass_rate: dict[str, float]
    stability: dict[str, float]
