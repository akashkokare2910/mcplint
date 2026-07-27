"""Typed schema for a user-authored `mcplint.contract.yaml`.

This describes the *behavioral* semantics of an MCP server's tools —
things a JSON Schema can't express: which tool should be preferred over
another and when, what a caller must never combine with a given tool, and
what failure modes are expected. It is user-authored, like `mcplint.yaml`,
so (unlike generated artifacts) it does not embed `ArtifactMetadata` —
`schema_version` here is a plain top-level field the author controls.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CONTRACT_SCHEMA_VERSION = "1"


class ToolIntent(BaseModel):
    operation: Literal["read", "write", "update", "delete", "create", "other"]
    cardinality: Literal["one", "many", "none"]
    matching: Literal["exact", "partial", "fuzzy", "none"]
    side_effects: Literal["none", "internal", "external"]
    risk: Literal["low", "medium", "high"]


class ReturnsSpec(BaseModel):
    cardinality: Literal["one", "many", "none"]
    entity: str


class PreferOverRule(BaseModel):
    when: str


class ToolBehavior(BaseModel):
    intent: ToolIntent
    requires: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    returns: ReturnsSpec | None = None
    prefer_over: dict[str, PreferOverRule] = Field(default_factory=dict)
    avoid_when: list[str] = Field(default_factory=list)
    expected_failures: list[str] = Field(default_factory=list)


class BehavioralContract(BaseModel):
    schema_version: str
    name: str
    description: str | None = None
    tools: dict[str, ToolBehavior]

    def tool_names(self) -> set[str]:
        return set(self.tools)
