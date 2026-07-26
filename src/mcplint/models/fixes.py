"""The deterministic (or optionally LLM-assisted) rewrite suggestion model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RewriteSuggestion(BaseModel):
    tool_name: str
    proposed_description: str
    resolved_rule_ids: list[str] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
