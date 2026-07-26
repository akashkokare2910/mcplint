from pathlib import Path

import pytest

from mcplint.config.loader import ConfigError, load_config


def test_load_config_missing_path_returns_defaults() -> None:
    config = load_config(None)
    assert config.thresholds.ambiguity == 0.55


def test_load_config_nonexistent_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "does-not-exist.yaml")
    assert config.thresholds.ambiguity == 0.55


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.yaml"
    path.write_text(
        """
severity:
  missing-tool-description: error
thresholds:
  ambiguity: 0.78
  max_description_characters: 500
ignore:
  - tool: internal_debug
    rules:
      - missing-return-semantics
""",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.thresholds.ambiguity == 0.78
    assert config.thresholds.max_description_characters == 500
    assert config.ignore[0].tool == "internal_debug"


def test_load_config_invalid_yaml_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.yaml"
    path.write_text("thresholds:\n  ambiguity: 5.0\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="ambiguity"):
        load_config(path)


def test_load_config_non_mapping_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(path)
