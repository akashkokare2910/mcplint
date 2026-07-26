"""The canonical, persistable representation of one MCP server's tool contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolContract

TransportKind = Literal["stdio", "http"]


class MCPServerSnapshot(BaseModel):
    metadata: ArtifactMetadata
    server_name: str
    server_version: str | None
    transport: TransportKind
    command: str | None
    tools: list[ToolContract]

    def get_tool(self, name: str) -> ToolContract | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
