from mcplint.models.contracts import (
    ParameterContract,
    SourceLocation,
    ToolAnnotation,
    ToolContract,
)


def test_source_location_roundtrip() -> None:
    loc = SourceLocation(tool_name="get_customer", json_path="$.description")
    assert loc.model_dump() == {"tool_name": "get_customer", "json_path": "$.description"}


def test_parameter_contract_defaults() -> None:
    param = ParameterContract(
        name="customer_id",
        json_schema={"type": "string"},
        required=True,
        description=None,
    )
    assert param.required is True
    assert param.description is None


def test_tool_annotation_all_optional() -> None:
    annotation = ToolAnnotation()
    assert annotation.destructive_hint is None
    assert annotation.read_only_hint is None


def test_tool_contract_parameter_names() -> None:
    tool = ToolContract(
        id="abc123",
        name="get_customer",
        description="Fetch a customer by id.",
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
        output_schema=None,
        parameters=[
            ParameterContract(
                name="customer_id",
                json_schema={"type": "string"},
                required=True,
                description="The customer id.",
            )
        ],
        annotations=ToolAnnotation(),
        raw={},
    )
    assert tool.parameter_names() == {"customer_id"}
