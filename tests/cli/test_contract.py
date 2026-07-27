from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

runner = CliRunner()

VALID_CONTRACT = """
schema_version: "1"
name: customer-server
tools:
  get_customer:
    intent:
      operation: read
      cardinality: one
      matching: exact
      side_effects: none
      risk: low
    requires:
      - customer_id
    prefer_over:
      search_customers:
        when: A known immutable customer ID is supplied.
  search_customers:
    intent:
      operation: read
      cardinality: many
      matching: partial
      side_effects: none
      risk: low
"""


def _snapshot_path(tmp_path: Path) -> Path:
    get_customer = ToolContract(
        id="a",
        name="get_customer",
        description="Retrieve a customer by ID.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[
            ParameterContract(name="customer_id", json_schema={"type": "string"}, required=True)
        ],
        annotations=ToolAnnotation(),
        raw={},
    )
    search_customers = ToolContract(
        id="b",
        name="search_customers",
        description="Search for customers.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[get_customer, search_customers],
    )
    path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, path)
    return path


def test_contract_validate_passes_for_consistent_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "mcplint.contract.yaml"
    contract_path.write_text(VALID_CONTRACT, encoding="utf-8")
    snapshot_path = _snapshot_path(tmp_path)

    result = runner.invoke(
        app, ["contract", "validate", str(contract_path), "--snapshot", str(snapshot_path)]
    )
    assert result.exit_code == 0, result.output
    assert "consistent" in result.output


def test_contract_validate_fails_for_unknown_tool(tmp_path: Path) -> None:
    contract_path = tmp_path / "mcplint.contract.yaml"
    contract_path.write_text(
        VALID_CONTRACT.replace("search_customers", "delete_customer"), encoding="utf-8"
    )
    snapshot_path = _snapshot_path(tmp_path)

    result = runner.invoke(
        app, ["contract", "validate", str(contract_path), "--snapshot", str(snapshot_path)]
    )
    assert result.exit_code == 1
    assert "delete_customer" in result.output


def test_contract_validate_requires_server_or_snapshot(tmp_path: Path) -> None:
    contract_path = tmp_path / "mcplint.contract.yaml"
    contract_path.write_text(VALID_CONTRACT, encoding="utf-8")

    result = runner.invoke(app, ["contract", "validate", str(contract_path)])
    assert result.exit_code == 2


def test_contract_validate_missing_contract_file(tmp_path: Path) -> None:
    snapshot_path = _snapshot_path(tmp_path)
    result = runner.invoke(
        app,
        [
            "contract",
            "validate",
            str(tmp_path / "missing.contract.yaml"),
            "--snapshot",
            str(snapshot_path),
        ],
    )
    assert result.exit_code == 2
