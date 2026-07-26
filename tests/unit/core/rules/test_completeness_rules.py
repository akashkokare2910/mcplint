from datetime import UTC, datetime

from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.completeness_rules import (
    ExcessiveDescriptionLengthRule,
    MissingReturnSemanticsRule,
    UndefinedDomainTermRule,
    UndocumentedErrorBehaviourRule,
    UndocumentedRequiredConstraintRule,
)
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(
    name: str = "search_customers",
    description: str | None = "Search for customers matching a company filter.",
    output_schema: dict[str, object] | None = None,
    parameters: list[ParameterContract] | None = None,
) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=output_schema,
        parameters=parameters or [],
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


def test_missing_return_semantics_flags_no_schema_no_wording() -> None:
    tool = _tool(description="Search for customers by company.")
    findings = MissingReturnSemanticsRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_missing_return_semantics_passes_with_output_schema() -> None:
    tool = _tool(output_schema={"type": "array"})
    assert MissingReturnSemanticsRule().check(tool, _context(tool)) == []


def test_missing_return_semantics_passes_with_return_wording() -> None:
    tool = _tool(description="Returns a list of matching customer records.")
    assert MissingReturnSemanticsRule().check(tool, _context(tool)) == []


def test_undocumented_error_behaviour_flags_missing_wording() -> None:
    tool = _tool(description="Search for customers matching a company filter.")
    findings = UndocumentedErrorBehaviourRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_undocumented_error_behaviour_passes_with_error_wording() -> None:
    tool = _tool(description="Search for customers. Raises an error if the filter is invalid.")
    assert UndocumentedErrorBehaviourRule().check(tool, _context(tool)) == []


def test_undocumented_required_constraint_flags_undocumented_enum() -> None:
    tool = _tool(
        parameters=[
            ParameterContract(
                name="status",
                json_schema={"type": "string", "enum": ["active", "inactive"]},
                required=True,
                description="The customer status.",
            )
        ]
    )
    findings = UndocumentedRequiredConstraintRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_undocumented_required_constraint_passes_when_values_mentioned() -> None:
    tool = _tool(
        parameters=[
            ParameterContract(
                name="status",
                json_schema={"type": "string", "enum": ["active", "inactive"]},
                required=True,
                description="The customer status: one of active or inactive.",
            )
        ]
    )
    assert UndocumentedRequiredConstraintRule().check(tool, _context(tool)) == []


def test_excessive_description_length_flags_long_description() -> None:
    tool = _tool(description="x" * 900)
    findings = ExcessiveDescriptionLengthRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_excessive_description_length_passes_normal_description() -> None:
    tool = _tool(description="Search for customers matching a company filter.")
    assert ExcessiveDescriptionLengthRule().check(tool, _context(tool)) == []


def test_undefined_domain_term_flags_unexplained_acronym() -> None:
    tool = _tool(description="Look up a customer using their CIF and branch code.")
    findings = UndefinedDomainTermRule().check(tool, _context(tool))
    assert any("CIF" in f.message for f in findings)


def test_undefined_domain_term_skips_well_known_acronyms() -> None:
    tool = _tool(description="Look up a customer by their ID via the API.")
    assert UndefinedDomainTermRule().check(tool, _context(tool)) == []


def test_undefined_domain_term_skips_explained_terms() -> None:
    tool = _tool(description="Look up a customer using their CIF (Customer Information File).")
    assert UndefinedDomainTermRule().check(tool, _context(tool)) == []
