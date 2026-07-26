from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcplint.mcp_client.persistence import load_snapshot, save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _snapshot() -> MCPServerSnapshot:
    tool = ToolContract(
        id="abc",
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
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[tool],
    )


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.snapshot.json"
    save_snapshot(_snapshot(), path)
    loaded = load_snapshot(path)
    assert loaded.server_name == "customer-server"
    assert loaded.tools[0].name == "get_customer"


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path / "does-not-exist.json")
