from datetime import UTC, datetime

from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.schema_rules import (
    MissingParameterDescriptionRule,
    SchemaDescriptionTypeConflictRule,
)
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool_with_params(parameters: list[ParameterContract]) -> ToolContract:
    return ToolContract(
        id="id-1",
        name="search_customers",
        description="Search for customers.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters,
        annotations=ToolAnnotation(),
        raw={},
    )


def _context(tool: ToolContract) -> RuleContext:
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
        tools=[tool],
    )
    return RuleContext(snapshot=snapshot)


def test_missing_parameter_description_flags_each_undocumented_param() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="company", json_schema={"type": "string"}, required=True, description=None
            ),
            ParameterContract(
                name="status",
                json_schema={"type": "string"},
                required=False,
                description="active or inactive",
            ),
        ]
    )
    findings = MissingParameterDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].location.json_path == "$.inputSchema.properties.company"


def test_missing_parameter_description_passes_when_documented() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="company",
                json_schema={"type": "string"},
                required=True,
                description="Company name.",
            )
        ]
    )
    assert MissingParameterDescriptionRule().check(tool, _context(tool)) == []


def test_schema_description_type_conflict_flags_count_as_string() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="limit",
                json_schema={"type": "string"},
                required=False,
                description="The number of results to return.",
            )
        ]
    )
    findings = SchemaDescriptionTypeConflictRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "schema-description-type-conflict"


def test_schema_description_type_conflict_flags_list_as_string() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="tags",
                json_schema={"type": "string"},
                required=False,
                description="A list of tags to filter by.",
            )
        ]
    )
    findings = SchemaDescriptionTypeConflictRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_schema_description_type_conflict_passes_when_types_match() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="limit",
                json_schema={"type": "integer"},
                required=False,
                description="The number of results.",
            ),
            ParameterContract(
                name="tags",
                json_schema={"type": "array"},
                required=False,
                description="A list of tags.",
            ),
        ]
    )
    assert SchemaDescriptionTypeConflictRule().check(tool, _context(tool)) == []


def test_schema_description_type_conflict_skips_undocumented_param() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="limit", json_schema={"type": "string"}, required=False, description=None
            )
        ]
    )
    assert SchemaDescriptionTypeConflictRule().check(tool, _context(tool)) == []
