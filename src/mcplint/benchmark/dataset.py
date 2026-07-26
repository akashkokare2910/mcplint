"""Load and validate a benchmark dataset YAML file."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from mcplint.models.benchmark import BenchmarkDataset


class DatasetError(Exception):
    """Raised when a benchmark dataset file is missing or fails validation."""


def load_dataset(path: Path) -> BenchmarkDataset:
    if not path.exists():
        raise DatasetError(f"Benchmark dataset not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise DatasetError(
            f"{path}: expected a YAML mapping at the top level, got {type(raw).__name__}"
        )

    try:
        return BenchmarkDataset.model_validate(raw)
    except ValidationError as exc:
        messages = "\n".join(
            f"  - {'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise DatasetError(f"{path}: invalid benchmark dataset:\n{messages}") from exc
