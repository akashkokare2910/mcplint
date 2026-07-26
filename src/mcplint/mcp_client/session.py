"""Connects to a stdio MCP server and produces an MCPServerSnapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcplint.mcp_client.canonical import stable_tool_id
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

if TYPE_CHECKING:
    from mcp.types import Tool as SDKTool

SNAPSHOT_SCHEMA_VERSION = "1.0"

__all__ = ["collect_stdio_snapshot", "tool_from_mcp", "parse_command"]


def tool_from_mcp(server_name: str, tool: "SDKTool") -> ToolContract:
    schema = tool.inputSchema or {"type": "object"}
    properties: dict[str, object] = schema.get("properties", {})  # type: ignore[assignment]
    required: list[str] = schema.get("required", [])  # type: ignore[assignment]

    parameters = [
        ParameterContract(
            name=name,
            json_schema=prop_schema if isinstance(prop_schema, dict) else {},
            required=name in required,
            description=(
                prop_schema.get("description") if isinstance(prop_schema, dict) else None
            ),
        )
        for name, prop_schema in properties.items()
    ]

    annotations = ToolAnnotation()
    if tool.annotations is not None:
        annotations = ToolAnnotation(
            title=tool.annotations.title,
            read_only_hint=tool.annotations.readOnlyHint,
            destructive_hint=tool.annotations.destructiveHint,
            idempotent_hint=tool.annotations.idempotentHint,
            open_world_hint=tool.annotations.openWorldHint,
        )

    return ToolContract(
        id=stable_tool_id(server_name, tool.name),
        name=tool.name,
        description=tool.description,
        input_schema=schema,
        output_schema=tool.outputSchema,
        parameters=parameters,
        annotations=annotations,
        raw=tool.model_dump(mode="json"),
    )


async def collect_stdio_snapshot(
    command: str, args: list[str], *, env: dict[str, str] | None = None
) -> MCPServerSnapshot:
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()
            server_name = init_result.serverInfo.name
            server_version = init_result.serverInfo.version
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
