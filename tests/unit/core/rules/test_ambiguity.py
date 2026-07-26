from mcplint.core.rules.ambiguity import compute_ambiguity
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract


def _tool(
    name: str,
    description: str | None,
    parameters: list[ParameterContract] | None = None,
    read_only_hint: bool | None = None,
) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters or [],
        annotations=ToolAnnotation(read_only_hint=read_only_hint),
        raw={},
    )


def test_compute_ambiguity_high_score_for_overlapping_tools() -> None:
    get_customer = _tool(
        "get_customer",
        "Retrieve a customer record by its ID.",
        parameters=[
            ParameterContract(name="customer_id", json_schema={"type": "string"}, required=True)
        ],
        read_only_hint=True,
    )
    search_customer = _tool(
        "search_customer",
        "Retrieve a customer record by search criteria.",
        parameters=[
            ParameterContract(name="customer_id", json_schema={"type": "string"}, required=False)
        ],
        read_only_hint=True,
    )
    result = compute_ambiguity(get_customer, search_customer)
    assert result.score > 0.5
    assert "customer_id" in result.evidence.overlapping_parameters


def test_compute_ambiguity_low_score_for_unrelated_tools() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer record by its ID.")
    send_email = _tool("send_email", "Send an email notification to a mailing list.")
    result = compute_ambiguity(get_customer, send_email)
    assert result.score < 0.3


def test_compute_ambiguity_flags_absent_exact_vs_search_distinction() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer record by its ID.")
    search_customers = _tool("search_customers", "Find customer records by company name.")
    result = compute_ambiguity(get_customer, search_customers)
    assert result.evidence.absent_exact_vs_search_distinction is True


def test_compute_ambiguity_no_missing_distinction_when_explained() -> None:
    get_customer = _tool(
        "get_customer", "Retrieve a customer by its exact ID. Use search_customers otherwise."
    )
    search_customers = _tool(
        "search_customers", "Find customers by company name when you don't have the exact ID."
    )
    result = compute_ambiguity(get_customer, search_customers)
    assert result.evidence.absent_exact_vs_search_distinction is False


def test_compute_ambiguity_flags_absent_read_vs_write_distinction() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer record.", read_only_hint=True)
    update_customer = _tool("update_customer", "Update a customer record.", read_only_hint=False)
    result = compute_ambiguity(get_customer, update_customer)
    assert result.evidence.absent_read_vs_write_distinction is True
