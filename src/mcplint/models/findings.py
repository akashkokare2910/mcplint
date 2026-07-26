"""Finding, rule metadata, and the aggregate lint report."""

from __future__ import annotations

from collections import Counter
from enum import Enum

from pydantic import BaseModel, Field

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    evidence: str
    location: SourceLocation
    remediation: str
    confidence: float = Field(ge=0.0, le=1.0)


class RuleMetadata(BaseModel):
    id: str
    title: str
    description: str
    default_severity: Severity
    tags: list[str] = Field(default_factory=list)


class LintReport(BaseModel):
    metadata: ArtifactMetadata
    server_name: str
    findings: list[Finding]

    def count_by_severity(self) -> dict[Severity, int]:
        return dict(Counter(finding.severity for finding in self.findings))
