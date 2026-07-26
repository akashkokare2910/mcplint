"""The Rule contract every deterministic and plugin rule implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, RuleMetadata, Severity
from mcplint.models.snapshot import MCPServerSnapshot


class RuleContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot: MCPServerSnapshot


class Rule(ABC):
    id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    default_severity: ClassVar[Severity]
    tags: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]: ...

    @classmethod
    def metadata(cls) -> RuleMetadata:
        return RuleMetadata(
            id=cls.id,
            title=cls.title,
            description=cls.description,
            default_severity=cls.default_severity,
            tags=list(cls.tags),
        )
