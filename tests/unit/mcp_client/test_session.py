from mcp.types import Tool, ToolAnnotations

from mcplint.mcp_client.session import parse_command, tool_from_mcp


def test_parse_command_splits_quoted_string() -> None:
    command, args = parse_command("python server.py --flag value")
    assert command == "python"
    assert args == ["server.py", "--flag", "value"]


def test_tool_from_mcp_maps_fields() -> None:
    sdk_tool = Tool(
        name="get_customer",
        description="Fetch a customer by id.",
        inputSchema={
            "type": "object",
            "properties": {"customer_id": {"type": "string", "description": "The id."}},
            "required": ["customer_id"],
        },
        annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=True),
    )
    contract = tool_from_mcp("customer-server", sdk_tool)
    assert contract.name == "get_customer"
    assert contract.description == "Fetch a customer by id."
    assert contract.parameters == [p for p in contract.parameters if p.name == "customer_id"]
    assert contract.parameters[0].required is True
    assert contract.parameters[0].description == "The id."
    assert contract.annotations.read_only_hint is True
    assert contract.annotations.destructive_hint is False
    assert len(contract.id) == 16


def test_tool_from_mcp_handles_missing_annotations_and_description() -> None:
    sdk_tool = Tool(name="ping", description=None, inputSchema={"type": "object"})
    contract = tool_from_mcp("server", sdk_tool)
    assert contract.description is None
    assert contract.parameters == []
    assert contract.annotations.read_only_hint is None
