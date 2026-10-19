"""Connects to a stdio MCP server and produces an MCPServerSnapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

from mcplint.mcp_client.canonical import stable_tool_id
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

if TYPE_CHECKING:
    from mcp.types import Tool as SDKTool

SNAPSHOT_SCHEMA_VERSION = "1.0"

__all__ = ["collect_stdio_snapshot", "tool_from_mcp", "parse_command"]


def _wire(model: BaseModel) -> dict[str, Any]:
    """An SDK model in MCP wire format (camelCase keys), whatever the SDK version.

    The ``mcp`` SDK renamed its Python attributes from the protocol's camelCase
    (``inputSchema``, ``serverInfo``) to snake_case in 2.x, keeping camelCase as
    aliases. Reading through an alias-keyed dump depends only on the protocol,
    which is stable, rather than on whichever attribute names the installed SDK
    uses.
    """
    return model.model_dump(mode="json", by_alias=True)


def tool_from_mcp(server_name: str, tool: SDKTool) -> ToolContract:
    wire = _wire(tool)
    schema: dict[str, Any] = wire.get("inputSchema") or {"type": "object"}
    properties: dict[str, object] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    parameters = [
        ParameterContract(
            name=name,
            json_schema=prop_schema if isinstance(prop_schema, dict) else {},
            required=name in required,
            description=(prop_schema.get("description") if isinstance(prop_schema, dict) else None),
        )
        for name, prop_schema in properties.items()
    ]

    annotations = ToolAnnotation()
    hints: dict[str, Any] | None = wire.get("annotations")
    if hints is not None:
        annotations = ToolAnnotation(
            title=hints.get("title"),
            read_only_hint=hints.get("readOnlyHint"),
            destructive_hint=hints.get("destructiveHint"),
            idempotent_hint=hints.get("idempotentHint"),
            open_world_hint=hints.get("openWorldHint"),
        )

    return ToolContract(
        id=stable_tool_id(server_name, wire["name"]),
        name=wire["name"],
        description=wire.get("description"),
        input_schema=schema,
        output_schema=wire.get("outputSchema"),
        parameters=parameters,
        annotations=annotations,
        raw=wire,
    )


async def collect_stdio_snapshot(
    command: str, args: list[str], *, env: dict[str, str] | None = None
) -> MCPServerSnapshot:
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        server_info = _wire(await session.initialize())["serverInfo"]
        server_name = server_info["name"]
        server_version = server_info["version"]
        listed = await session.list_tools()
        tools = [tool_from_mcp(server_name, t) for t in listed.tools]

    command_line = " ".join([command, *args])
    return MCPServerSnapshot(
        metadata=ArtifactMetadata.create(schema_version=SNAPSHOT_SCHEMA_VERSION),
        server_name=server_name,
        server_version=server_version,
        transport="stdio",
        command=command_line,
        tools=tools,
    )
