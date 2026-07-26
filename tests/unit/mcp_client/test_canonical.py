from datetime import datetime, timedelta, timezone

from mcplint.mcp_client.canonical import canonical_json, stable_tool_id
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def test_stable_tool_id_deterministic() -> None:
    a = stable_tool_id("customer-server", "get_customer")
    b = stable_tool_id("customer-server", "get_customer")
    assert a == b
    assert len(a) == 16


def test_stable_tool_id_differs_by_tool_name() -> None:
    a = stable_tool_id("customer-server", "get_customer")
    b = stable_tool_id("customer-server", "delete_customer")
    assert a != b


def _snapshot(generated_at: datetime) -> MCPServerSnapshot:
    tool = ToolContract(
        id=stable_tool_id("customer-server", "get_customer"),
        name="get_customer",
        description="Fetch a customer.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=generated_at, mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[tool],
    )


def test_canonical_json_stable_across_generated_at() -> None:
    first = _snapshot(datetime(2026, 1, 1, tzinfo=timezone.utc))
    second = _snapshot(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=30))
    assert canonical_json(first) == canonical_json(second)


def test_canonical_json_changes_with_tool_content() -> None:
    same_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    base = _snapshot(same_time)
    mutated = _snapshot(same_time)
    mutated.tools[0].description = "Different description"
    assert canonical_json(base) != canonical_json(mutated)
