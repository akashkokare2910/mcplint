from pathlib import Path

import pytest

from mcplint.contract.loader import ContractError, load_contract


def test_load_contract_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.contract.yaml"
    path.write_text(
        """
schema_version: "1"
name: customer-server
description: Behavioral semantics for customer MCP tools

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
    excludes:
      - partial_name
    returns:
      cardinality: one
      entity: customer
    prefer_over:
      search_customers:
        when: A known immutable customer ID is supplied.
    avoid_when:
      - The user does not know the exact customer ID.
    expected_failures:
      - customer_not_found

  search_customers:
    intent:
      operation: read
      cardinality: many
      matching: partial
      side_effects: none
      risk: low
    prefer_over:
      get_customer:
        when: The exact customer ID is unknown.
""",
        encoding="utf-8",
    )
    contract = load_contract(path)
    assert contract.name == "customer-server"
    assert contract.tools["get_customer"].requires == ["customer_id"]
    assert (
        contract.tools["get_customer"].prefer_over["search_customers"].when
        == "A known immutable customer ID is supplied."
    )


def test_load_contract_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="not found"):
        load_contract(tmp_path / "missing.contract.yaml")


def test_load_contract_invalid_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.contract.yaml"
    path.write_text(
        """
schema_version: "1"
name: customer-server
tools:
  get_customer:
    intent:
      operation: not-a-real-operation
      cardinality: one
      matching: exact
      side_effects: none
      risk: low
""",
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="operation"):
        load_contract(path)


def test_load_contract_non_mapping_raises(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.contract.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ContractError, match="mapping"):
        load_contract(path)
