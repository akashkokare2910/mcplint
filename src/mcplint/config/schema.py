"""Typed schema for mcplint.yaml."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mcplint.core.rules.ambiguity import DEFAULT_AMBIGUITY_THRESHOLD
from mcplint.core.rules.completeness_rules import DEFAULT_MAX_DESCRIPTION_CHARACTERS
from mcplint.models.findings import Severity


class ThresholdsConfig(BaseModel):
    ambiguity: float = Field(default=DEFAULT_AMBIGUITY_THRESHOLD, ge=0.0, le=1.0)
    max_description_characters: int = Field(default=DEFAULT_MAX_DESCRIPTION_CHARACTERS, gt=0)


class IgnoreEntry(BaseModel):
    tool: str
    rules: list[str] = Field(default_factory=list)


class BenchmarkConfig(BaseModel):
    provider: str | None = None
    model: str | None = None
    runs: int = Field(default=3, ge=1)


class MCPLintConfig(BaseModel):
    severity: dict[str, Severity] = Field(default_factory=dict)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    ignore: list[IgnoreEntry] = Field(default_factory=list)
    benchmark: BenchmarkConfig | None = None

    def ignored_rule_ids_for_tool(self, tool_name: str, all_rule_ids: set[str]) -> set[str]:
        ignored: set[str] = set()
        for entry in self.ignore:
            if entry.tool != tool_name:
                continue
            ignored |= set(entry.rules) if entry.rules else all_rule_ids
        return ignored
