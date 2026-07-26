"""Shared metadata mixin every persisted MCPLint artifact embeds."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from mcplint.__about__ import __version__ as _MCPLINT_VERSION


class ArtifactMetadata(BaseModel):
    schema_version: str
    generated_at: datetime
    mcplint_version: str

    @classmethod
    def create(cls, schema_version: str) -> "ArtifactMetadata":
        return cls(
            schema_version=schema_version,
            generated_at=datetime.now(timezone.utc),
            mcplint_version=_MCPLINT_VERSION,
        )
