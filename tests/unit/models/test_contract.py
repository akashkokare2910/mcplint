from mcplint.models.contract import (
    BehavioralContract,
    PreferOverRule,
    ReturnsSpec,
    ToolBehavior,
    ToolIntent,
)


def test_tool_behavior_defaults_are_empty() -> None:
    behavior = ToolBehavior(
        intent=ToolIntent(
            operation="read",
            cardinality="many",
            matching="partial",
            side_effects="none",
            risk="low",
        )
    )
    assert behavior.requires == []
    assert behavior.excludes == []
    assert behavior.returns is None
    assert behavior.prefer_over == {}
    assert behavior.avoid_when == []
    assert behavior.expected_failures == []


def test_behavioral_contract_parses_full_example() -> None:
    contract = BehavioralContract(
        schema_version="1",
        name="customer-server",
        description="Behavioral semantics for customer MCP tools",
        tools={
            "get_customer": ToolBehavior(
                intent=ToolIntent(
                    operation="read",
                    cardinality="one",
                    matching="exact",
                    side_effects="none",
                    risk="low",
                ),
                requires=["customer_id"],
                excludes=["partial_name", "company_query"],
                returns=ReturnsSpec(cardinality="one", entity="customer"),
                prefer_over={
                    "search_customers": PreferOverRule(
                        when="A known immutable customer ID is supplied."
                    )
                },
                avoid_when=[
                    "The user does not know the exact customer ID.",
                    "The user requests multiple customers.",
                ],
                expected_failures=["customer_not_found"],
            ),
            "search_customers": ToolBehavior(
                intent=ToolIntent(
                    operation="read",
                    cardinality="many",
                    matching="partial",
                    side_effects="none",
                    risk="low",
                ),
                prefer_over={
                    "get_customer": PreferOverRule(when="The exact customer ID is unknown.")
                },
            ),
        },
    )
    assert contract.tool_names() == {"get_customer", "search_customers"}
    assert contract.tools["get_customer"].requires == ["customer_id"]
    assert contract.tools["get_customer"].returns is not None
    assert contract.tools["get_customer"].returns.entity == "customer"
    assert (
        contract.tools["search_customers"].prefer_over["get_customer"].when
        == "The exact customer ID is unknown."
    )
