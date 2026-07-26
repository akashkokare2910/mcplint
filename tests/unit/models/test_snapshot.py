from datetime import datetime, timezone

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def test_snapshot_get_tool_found() -> None:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[_tool("get_customer"), _tool("search_customers")],
    )
    found = snapshot.get_tool("search_customers")
    assert found is not None
    assert found.name == "search_customers"


def test_snapshot_get_tool_missing() -> None:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command="python server.py",
        tools=[_tool("get_customer")],
    )
    assert snapshot.get_tool("delete_customer") is None
