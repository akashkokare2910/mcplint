"""Read/write MCPServerSnapshot to/from disk as JSON."""

from __future__ import annotations

from pathlib import Path

from mcplint.models.snapshot import MCPServerSnapshot


def save_snapshot(snapshot: MCPServerSnapshot, path: Path) -> None:
    path.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_snapshot(path: Path) -> MCPServerSnapshot:
    if not path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {path}")
    return MCPServerSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
