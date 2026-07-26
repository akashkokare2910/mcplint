"""Single source of truth for deterministic IDs and byte-stable snapshot JSON.

MCP servers are untrusted local (or remote) processes; this module only ever
touches data already parsed into typed models, never raw process output.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcplint.models.snapshot import MCPServerSnapshot


def stable_tool_id(server_name: str, tool_name: str) -> str:
    digest = hashlib.sha256(f"{server_name}::{tool_name}".encode()).hexdigest()
    return digest[:16]


def canonical_json(snapshot: MCPServerSnapshot) -> str:
    payload = snapshot.model_dump(mode="json")
    payload["metadata"].pop("generated_at", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
