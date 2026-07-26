from datetime import UTC, datetime

from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.description_rules import (
    DescriptionRepeatsNameRule,
    MissingToolDescriptionRule,
    VagueToolDescriptionRule,
)
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(
    name: str, description: str | None, parameters: list[ParameterContract] | None = None
) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters or [],
        annotations=ToolAnnotation(),
        raw={},
    )


def _context(*tools: ToolContract) -> RuleContext:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )
    return RuleContext(snapshot=snapshot)


def test_missing_tool_description_flags_none() -> None:
    tool = _tool("delete_customer", None)
    findings = MissingToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "missing-tool-description"
    assert findings[0].confidence == 1.0


def test_missing_tool_description_flags_blank() -> None:
    tool = _tool("delete_customer", "   ")
    findings = MissingToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_missing_tool_description_passes_with_text() -> None:
    tool = _tool("delete_customer", "Deletes a customer permanently.")
    assert MissingToolDescriptionRule().check(tool, _context(tool)) == []


def test_description_repeats_name_flags_bare_restatement() -> None:
    tool = _tool("get_customer", "Get customer")
    findings = DescriptionRepeatsNameRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "description-repeats-name"


def test_description_repeats_name_passes_with_detail() -> None:
    tool = _tool(
        "get_customer",
        "Retrieve a single customer record by its exact customer ID.",
    )
    assert DescriptionRepeatsNameRule().check(tool, _context(tool)) == []


def test_description_repeats_name_skips_missing_description() -> None:
    tool = _tool("get_customer", None)
    assert DescriptionRepeatsNameRule().check(tool, _context(tool)) == []


def test_vague_tool_description_flags_short_description() -> None:
    tool = _tool("get_customer", "Gets data.")
    findings = VagueToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "vague-tool-description"


def test_vague_tool_description_passes_with_enough_detail() -> None:
    tool = _tool(
        "get_customer",
        "Retrieve a single customer record by its exact customer ID (format CUST-XXXX).",
    )
    assert VagueToolDescriptionRule().check(tool, _context(tool)) == []


def test_vague_tool_description_skips_missing_description() -> None:
    tool = _tool("get_customer", None)
    assert VagueToolDescriptionRule().check(tool, _context(tool)) == []
