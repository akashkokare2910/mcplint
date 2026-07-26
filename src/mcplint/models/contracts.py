"""Typed representations of an MCP tool contract, independent of the wire format."""

from __future__ import annotations

from pydantic import BaseModel


class SourceLocation(BaseModel):
    tool_name: str
    json_path: str


class ParameterContract(BaseModel):
    name: str
    json_schema: dict[str, object]
    required: bool
    description: str | None = None


class ToolAnnotation(BaseModel):
    title: str | None = None
    read_only_hint: bool | None = None
    destructive_hint: bool | None = None
    idempotent_hint: bool | None = None
    open_world_hint: bool | None = None


class ToolContract(BaseModel):
    id: str
    name: str
    description: str | None
    input_schema: dict[str, object]
    output_schema: dict[str, object] | None = None
    parameters: list[ParameterContract]
    annotations: ToolAnnotation
    raw: dict[str, object]

    def parameter_names(self) -> set[str]:
        return {param.name for param in self.parameters}
