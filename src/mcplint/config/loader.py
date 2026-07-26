"""Load and validate mcplint.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from mcplint.config.schema import MCPLintConfig


class ConfigError(Exception):
    """Raised when mcplint.yaml exists but fails validation."""


def load_config(path: Path | None) -> MCPLintConfig:
    if path is None:
        return MCPLintConfig()
    if not path.exists():
        return MCPLintConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"{path}: expected a YAML mapping at the top level, got {type(raw).__name__}"
        )

    try:
        return MCPLintConfig.model_validate(raw)
    except ValidationError as exc:
        messages = "\n".join(
            f"  - {'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(f"{path}: invalid configuration:\n{messages}") from exc
