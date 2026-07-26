from pathlib import Path

import pytest

from mcplint.benchmark.dataset import DatasetError, load_dataset


def test_load_dataset_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "evals.yaml"
    path.write_text(
        """
name: customer-tools
version: "1"
cases:
  - id: exact-customer-lookup
    prompt: Retrieve customer CUST-1042.
    expected:
      tool: get_customer
      arguments:
        customer_id: CUST-1042
      forbidden_tools:
        - delete_customer
  - id: customer-search
    prompt: Find active customers whose company is Acme.
    expected:
      tool: search_customers
      argument_assertions:
        status: active
        company: Acme
""",
        encoding="utf-8",
    )
    dataset = load_dataset(path)
    assert dataset.name == "customer-tools"
    assert len(dataset.cases) == 2
    assert dataset.cases[0].expected.tool == "get_customer"
    assert dataset.cases[0].expected.forbidden_tools == ["delete_customer"]
    assert dataset.cases[1].expected.argument_assertions == {"status": "active", "company": "Acme"}


def test_load_dataset_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="not found"):
        load_dataset(tmp_path / "missing.yaml")


def test_load_dataset_invalid_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "evals.yaml"
    path.write_text("name: no-cases-field\nversion: '1'\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="cases"):
        load_dataset(path)
