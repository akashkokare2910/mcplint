"""Load and validate mcplint.contract.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from mcplint.models.contract import BehavioralContract


class ContractError(Exception):
    """Raised when a behavioral contract file is missing or fails validation."""


def load_contract(path: Path) -> BehavioralContract:
    if not path.exists():
        raise ContractError(f"Behavioral contract not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ContractError(
            f"{path}: expected a YAML mapping at the top level, got {type(raw).__name__}"
        )

    try:
        return BehavioralContract.model_validate(raw)
    except ValidationError as exc:
        messages = "\n".join(
            f"  - {'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ContractError(f"{path}: invalid behavioral contract:\n{messages}") from exc
