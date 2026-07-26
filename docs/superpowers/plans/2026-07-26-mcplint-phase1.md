# MCPLint Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the MCPLint package skeleton, core Pydantic models, MCP stdio snapshot collection with canonicalization, and the `mcplint inspect` CLI command, fully tested.

**Architecture:** `src/mcplint/models/` holds all typed contracts (snapshot, tool/parameter contracts, findings — findings types are defined now even though no rules exist yet, since `LintReport` composes them). `src/mcplint/mcp_client/` wraps the official `mcp` SDK's `stdio_client` + `ClientSession` to produce an `MCPServerSnapshot`, with a `canonical.py` module providing the single canonicalization function used for both stable IDs and byte-stable JSON serialization. `src/mcplint/cli/` is a Typer app; `inspect` is the first command, printed via Rich, with no reporter abstraction yet (that lands in Phase 2).

**Tech Stack:** Python 3.11 (venv at `.venv`, already created), Pydantic v2, official `mcp` SDK 1.28.1, Typer, Rich, pytest + pytest-asyncio, Ruff, MyPy, hatchling build backend (uv-compatible `pyproject.toml`).

## Global Constraints

- Python 3.11+ only; venv is `/Users/akash.kokare/Documents/Personal/mcplint/.venv` using `/opt/homebrew/bin/python3.11`.
- Every persisted artifact model must carry `schema_version: str`, `generated_at: datetime`, `mcplint_version: str` (spec p.3).
- Deterministic, stable IDs where appropriate (spec p.3) — tool IDs are a hash of server name + tool name, not a random UUID.
- Canonicalised snapshots: identical server contracts produce byte-stable JSON except for generated metadata (`generated_at`) (spec p.3).
- No `any`/untyped code: full type hints, MyPy strict-ish (`disallow_untyped_defs`).
- No LLM calls anywhere in Phase 1 — deterministic only.
- Named exports only, no wildcard re-exports.
- Commands must return meaningful non-zero exit codes for CI (spec p.2) — `inspect` must exit 1 on connection/snapshot failure.
- Treat MCP servers as untrusted local processes — document this in the `mcp_client` module docstring; no shell=True, pass `command`/`args` as a list.
- Every phase ends with Ruff clean, MyPy clean, pytest green before moving on (spec p.11).

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/mcplint/__init__.py`
- Create: `src/mcplint/__about__.py`
- Create: `.gitignore`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`

**Interfaces:**
- Produces: `mcplint.__about__.__version__: str` (used by all `mcplint_version` fields later).
- Produces: console script `mcplint` → `mcplint.cli.main:app`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcplint"
version = "0.1.0"
description = "ESLint for MCP tool contracts"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
  "typer>=0.12",
  "pydantic>=2.7",
  "mcp>=1.28",
  "jsonschema>=4.22",
  "rich>=13.7",
  "pyyaml>=6.0",
  "jinja2>=3.1",
  "httpx>=0.27",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.34"]
openai = ["openai>=1.40"]
semantic = ["sentence-transformers>=3.0"]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "ruff>=0.5",
  "mypy>=1.10",
  "types-pyyaml",
  "types-jsonschema",
]

[project.scripts]
mcplint = "mcplint.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/mcplint"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
disallow_untyped_defs = true
disallow_incomplete_defs = true
no_implicit_optional = true
warn_unused_ignores = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write `src/mcplint/__about__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Write `src/mcplint/__init__.py`**

```python
from mcplint.__about__ import __version__

__all__ = ["__version__"]
```

- [ ] **Step 4: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
.coverage
htmlcov/
```

- [ ] **Step 5: Create empty test package files**

`tests/__init__.py` and `tests/unit/__init__.py` — empty files.

- [ ] **Step 6: Install package in editable mode and verify**

Run: `source .venv/bin/activate && pip install -e ".[dev]"`
Expected: installs cleanly, `python -c "import mcplint; print(mcplint.__version__)"` prints `0.1.0`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/mcplint/__init__.py src/mcplint/__about__.py .gitignore tests/__init__.py tests/unit/__init__.py
git commit -m "chore: project scaffolding"
```

---

### Task 2: Common artifact metadata mixin

**Files:**
- Create: `src/mcplint/models/__init__.py`
- Create: `src/mcplint/models/common.py`
- Test: `tests/unit/models/__init__.py`
- Test: `tests/unit/models/test_common.py`

**Interfaces:**
- Produces: `ArtifactMetadata(BaseModel)` with fields `schema_version: str`, `generated_at: datetime`, `mcplint_version: str`, and classmethod `ArtifactMetadata.create(schema_version: str) -> ArtifactMetadata` that fills `generated_at=datetime.now(timezone.utc)` and `mcplint_version` from `mcplint.__about__.__version__`.
- Consumed by: `MCPServerSnapshot`, `LintReport`, `BenchmarkResult`, `ComparisonReport` (later tasks) via composition (`metadata: ArtifactMetadata`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/models/test_common.py
from datetime import datetime, timezone

from mcplint.models.common import ArtifactMetadata


def test_create_fills_version_and_timestamp() -> None:
    meta = ArtifactMetadata.create(schema_version="1.0")
    assert meta.schema_version == "1.0"
    assert meta.mcplint_version == "0.1.0"
    assert isinstance(meta.generated_at, datetime)
    assert meta.generated_at.tzinfo is timezone.utc


def test_metadata_is_frozen_shape() -> None:
    meta = ArtifactMetadata(
        schema_version="1.0",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        mcplint_version="0.1.0",
    )
    assert meta.model_dump()["schema_version"] == "1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_common.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/models/__init__.py
```

(empty — marks package)

```python
# src/mcplint/models/common.py
"""Shared metadata mixin every persisted MCPLint artifact embeds."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from mcplint.__about__ import __version__ as _MCPLINT_VERSION


class ArtifactMetadata(BaseModel):
    schema_version: str
    generated_at: datetime
    mcplint_version: str

    @classmethod
    def create(cls, schema_version: str) -> "ArtifactMetadata":
        return cls(
            schema_version=schema_version,
            generated_at=datetime.now(timezone.utc),
            mcplint_version=_MCPLINT_VERSION,
        )
```

`tests/unit/models/__init__.py` — empty file.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/models/test_common.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/models/__init__.py src/mcplint/models/common.py tests/unit/models/__init__.py tests/unit/models/test_common.py
git commit -m "feat: add ArtifactMetadata mixin for persisted artifacts"
```

---

### Task 3: `ParameterContract`, `ToolAnnotation`, `SourceLocation` models

**Files:**
- Create: `src/mcplint/models/contracts.py`
- Test: `tests/unit/models/test_contracts.py`

**Interfaces:**
- Produces: `SourceLocation(BaseModel)`: `tool_name: str`, `json_path: str` (e.g. `"$.inputSchema.properties.customer_id"`).
- Produces: `ParameterContract(BaseModel)`: `name: str`, `json_schema: dict[str, object]`, `required: bool`, `description: str | None`.
- Produces: `ToolAnnotation(BaseModel)`: `title: str | None = None`, `read_only_hint: bool | None = None`, `destructive_hint: bool | None = None`, `idempotent_hint: bool | None = None`, `open_world_hint: bool | None = None`.
- Produces: `ToolContract(BaseModel)`: `id: str`, `name: str`, `description: str | None`, `input_schema: dict[str, object]`, `output_schema: dict[str, object] | None = None`, `parameters: list[ParameterContract]`, `annotations: ToolAnnotation`, `raw: dict[str, object]` (verbatim MCP `Tool` dump, for rules needing untouched data).
- Produces: `ToolContract.parameter_names() -> set[str]` helper used by ambiguity engine later.
- Consumed by: `MCPServerSnapshot.tools: list[ToolContract]` (Task 4), all rules (Phase 2+).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/models/test_contracts.py
from mcplint.models.contracts import (
    ParameterContract,
    SourceLocation,
    ToolAnnotation,
    ToolContract,
)


def test_source_location_roundtrip() -> None:
    loc = SourceLocation(tool_name="get_customer", json_path="$.description")
    assert loc.model_dump() == {"tool_name": "get_customer", "json_path": "$.description"}


def test_parameter_contract_defaults() -> None:
    param = ParameterContract(
        name="customer_id",
        json_schema={"type": "string"},
        required=True,
        description=None,
    )
    assert param.required is True
    assert param.description is None


def test_tool_annotation_all_optional() -> None:
    annotation = ToolAnnotation()
    assert annotation.destructive_hint is None
    assert annotation.read_only_hint is None


def test_tool_contract_parameter_names() -> None:
    tool = ToolContract(
        id="abc123",
        name="get_customer",
        description="Fetch a customer by id.",
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
        output_schema=None,
        parameters=[
            ParameterContract(
                name="customer_id",
                json_schema={"type": "string"},
                required=True,
                description="The customer id.",
            )
        ],
        annotations=ToolAnnotation(),
        raw={},
    )
    assert tool.parameter_names() == {"customer_id"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.models.contracts'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/models/contracts.py
"""Typed representations of an MCP tool contract, independent of the wire format."""

from __future__ import annotations

from pydantic import BaseModel


class SourceLocation(BaseModel):
    tool_name: str
    json_path: str


class ParameterContract(BaseModel):
    name: str
    json_schema: dict[str, object]
    required: bool
    description: str | None = None


class ToolAnnotation(BaseModel):
    title: str | None = None
    read_only_hint: bool | None = None
    destructive_hint: bool | None = None
    idempotent_hint: bool | None = None
    open_world_hint: bool | None = None


class ToolContract(BaseModel):
    id: str
    name: str
    description: str | None
    input_schema: dict[str, object]
    output_schema: dict[str, object] | None = None
    parameters: list[ParameterContract]
    annotations: ToolAnnotation
    raw: dict[str, object]

    def parameter_names(self) -> set[str]:
        return {param.name for param in self.parameters}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/models/test_contracts.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/models/contracts.py tests/unit/models/test_contracts.py
git commit -m "feat: add ToolContract, ParameterContract, ToolAnnotation, SourceLocation models"
```

---

### Task 4: `MCPServerSnapshot` model

**Files:**
- Create: `src/mcplint/models/snapshot.py`
- Test: `tests/unit/models/test_snapshot.py`

**Interfaces:**
- Consumes: `ArtifactMetadata` (Task 2), `ToolContract` (Task 3).
- Produces: `MCPServerSnapshot(BaseModel)`: `metadata: ArtifactMetadata`, `server_name: str`, `server_version: str | None`, `transport: str` (`"stdio"` or `"http"`), `command: str | None` (the invoked command, for provenance), `tools: list[ToolContract]`.
- Produces: `MCPServerSnapshot.get_tool(name: str) -> ToolContract | None` helper.
- Consumed by: `mcp_client` snapshot builder (Task 5), `inspect` CLI command (Task 6), Phase 2 rule engine.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/models/test_snapshot.py
from datetime import datetime, timezone

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def test_snapshot_get_tool_found() -> None:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[_tool("get_customer"), _tool("search_customers")],
    )
    found = snapshot.get_tool("search_customers")
    assert found is not None
    assert found.name == "search_customers"


def test_snapshot_get_tool_missing() -> None:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command="python server.py",
        tools=[_tool("get_customer")],
    )
    assert snapshot.get_tool("delete_customer") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_snapshot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.models.snapshot'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/models/snapshot.py
"""The canonical, persistable representation of one MCP server's tool contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolContract

TransportKind = Literal["stdio", "http"]


class MCPServerSnapshot(BaseModel):
    metadata: ArtifactMetadata
    server_name: str
    server_version: str | None
    transport: TransportKind
    command: str | None
    tools: list[ToolContract]

    def get_tool(self, name: str) -> ToolContract | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/models/test_snapshot.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/models/snapshot.py tests/unit/models/test_snapshot.py
git commit -m "feat: add MCPServerSnapshot model"
```

---

### Task 5: Canonicalization (stable IDs + byte-stable JSON)

**Files:**
- Create: `src/mcplint/mcp_client/__init__.py`
- Create: `src/mcplint/mcp_client/canonical.py`
- Test: `tests/unit/mcp_client/__init__.py`
- Test: `tests/unit/mcp_client/test_canonical.py`

**Interfaces:**
- Produces: `stable_tool_id(server_name: str, tool_name: str) -> str` — `sha256(f"{server_name}::{tool_name}")[:16]` hex digest, deterministic across runs.
- Produces: `canonical_json(snapshot: MCPServerSnapshot) -> str` — `model_dump(mode="json")`, drop `metadata.generated_at`, `json.dumps(..., sort_keys=True, separators=(",", ":"))`.
- Consumed by: `mcp_client/session.py` (Task 6) for tool IDs; `cli/commands/snapshot_cmd.py` (Phase 1 follow-on / Phase 2) and snapshot normalisation tests (Phase 3) for byte-stable output.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/mcp_client/test_canonical.py
from datetime import datetime, timedelta, timezone

from mcplint.mcp_client.canonical import canonical_json, stable_tool_id
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def test_stable_tool_id_deterministic() -> None:
    a = stable_tool_id("customer-server", "get_customer")
    b = stable_tool_id("customer-server", "get_customer")
    assert a == b
    assert len(a) == 16


def test_stable_tool_id_differs_by_tool_name() -> None:
    a = stable_tool_id("customer-server", "get_customer")
    b = stable_tool_id("customer-server", "delete_customer")
    assert a != b


def _snapshot(generated_at: datetime) -> MCPServerSnapshot:
    tool = ToolContract(
        id=stable_tool_id("customer-server", "get_customer"),
        name="get_customer",
        description="Fetch a customer.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=generated_at, mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[tool],
    )


def test_canonical_json_stable_across_generated_at() -> None:
    first = _snapshot(datetime(2026, 1, 1, tzinfo=timezone.utc))
    second = _snapshot(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=30))
    assert canonical_json(first) == canonical_json(second)


def test_canonical_json_changes_with_tool_content() -> None:
    same_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    base = _snapshot(same_time)
    mutated = _snapshot(same_time)
    mutated.tools[0].description = "Different description"
    assert canonical_json(base) != canonical_json(mutated)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/mcp_client/test_canonical.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.mcp_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/mcp_client/__init__.py
```

(empty — marks package)

```python
# src/mcplint/mcp_client/canonical.py
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
    digest = hashlib.sha256(f"{server_name}::{tool_name}".encode("utf-8")).hexdigest()
    return digest[:16]


def canonical_json(snapshot: "MCPServerSnapshot") -> str:
    payload = snapshot.model_dump(mode="json")
    payload["metadata"].pop("generated_at", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

`tests/unit/mcp_client/__init__.py` — empty file.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/mcp_client/test_canonical.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/mcp_client/__init__.py src/mcplint/mcp_client/canonical.py tests/unit/mcp_client/__init__.py tests/unit/mcp_client/test_canonical.py
git commit -m "feat: add canonicalization for stable tool IDs and byte-stable snapshot JSON"
```

---

### Task 6: Example stdio MCP server fixture

**Files:**
- Create: `examples/good_server/server.py`
- Create: `examples/good_server/pyproject.toml`

**Interfaces:**
- Produces: a runnable `python examples/good_server/server.py` stdio MCP server exposing 2 well-documented tools (`get_customer`, `search_customers`), used by Task 7's integration test and Phase 3's rule-triggering fixtures build on top of this pattern.

- [ ] **Step 1: Write the server**

```python
# examples/good_server/server.py
"""A well-documented example MCP server used by MCPLint's own tests.

Run directly: python examples/good_server/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("good-customer-server")


@mcp.tool(
    description=(
        "Retrieve a single customer record by its exact customer ID "
        "(format CUST-XXXX). Read-only. Raises a not-found error if the "
        "ID does not exist. Use search_customers to find a customer when "
        "you don't already have the exact ID."
    )
)
def get_customer(customer_id: str) -> dict[str, str]:
    """customer_id: the exact customer identifier, e.g. CUST-1042."""
    return {"customer_id": customer_id, "name": "Example Customer"}


@mcp.tool(
    description=(
        "Search for customers matching a company name and/or status filter. "
        "Read-only, returns zero or more matches. Use get_customer instead "
        "when you already know the exact customer ID."
    )
)
def search_customers(company: str, status: str = "active") -> list[dict[str, str]]:
    """company: company name to match. status: one of 'active', 'inactive'."""
    return [{"customer_id": "CUST-1042", "company": company, "status": status}]


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Write minimal server pyproject (for isolated dependency clarity)**

```toml
# examples/good_server/pyproject.toml
[project]
name = "good-server-example"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["mcp[cli]>=1.28"]
```

- [ ] **Step 3: Verify it starts and speaks MCP over stdio**

Run:
```bash
source .venv/bin/activate
pip install -q "mcp[cli]"
python - <<'EOF'
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main() -> None:
    params = StdioServerParameters(command="python", args=["examples/good_server/server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

asyncio.run(main())
EOF
```
Expected: prints `['get_customer', 'search_customers']`

- [ ] **Step 4: Commit**

```bash
git add examples/good_server/server.py examples/good_server/pyproject.toml
git commit -m "feat: add good_server example MCP server fixture"
```

---

### Task 7: Stdio snapshot collector (`mcp_client/session.py`, `stdio.py`)

**Files:**
- Create: `src/mcplint/mcp_client/stdio.py`
- Create: `src/mcplint/mcp_client/session.py`
- Test: `tests/unit/mcp_client/test_session.py`
- Test: `tests/integration/__init__.py`
- Test: `tests/integration/test_example_servers.py`

**Interfaces:**
- Consumes: `mcp.types.Tool` (SDK), `stable_tool_id` (Task 5), `ToolContract`/`ParameterContract`/`ToolAnnotation` (Task 3), `MCPServerSnapshot` (Task 4).
- Produces: `tool_from_mcp(server_name: str, tool: "mcp.types.Tool") -> ToolContract` (pure function, unit-testable without a live process).
- Produces: `async def collect_stdio_snapshot(command: str, args: list[str], *, env: dict[str, str] | None = None) -> MCPServerSnapshot` — spawns the process via `StdioServerParameters` + `stdio_client` + `ClientSession`, calls `initialize()` then `list_tools()`, builds the snapshot.
- Produces: `parse_command(command_line: str) -> tuple[str, list[str]]` using `shlex.split`, so `--server "python server.py"` becomes `("python", ["server.py"])`.
- Consumed by: `inspect` CLI command (Task 8), `snapshot` CLI command (Phase 2).

- [ ] **Step 1: Write the failing unit test (pure function, no process)**

```python
# tests/unit/mcp_client/test_session.py
from mcp.types import Tool, ToolAnnotations

from mcplint.mcp_client.session import parse_command, tool_from_mcp


def test_parse_command_splits_quoted_string() -> None:
    command, args = parse_command("python server.py --flag value")
    assert command == "python"
    assert args == ["server.py", "--flag", "value"]


def test_tool_from_mcp_maps_fields() -> None:
    sdk_tool = Tool(
        name="get_customer",
        description="Fetch a customer by id.",
        inputSchema={
            "type": "object",
            "properties": {"customer_id": {"type": "string", "description": "The id."}},
            "required": ["customer_id"],
        },
        annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=True),
    )
    contract = tool_from_mcp("customer-server", sdk_tool)
    assert contract.name == "get_customer"
    assert contract.description == "Fetch a customer by id."
    assert contract.parameters == [
        p for p in contract.parameters if p.name == "customer_id"
    ]
    assert contract.parameters[0].required is True
    assert contract.parameters[0].description == "The id."
    assert contract.annotations.read_only_hint is True
    assert contract.annotations.destructive_hint is False
    assert len(contract.id) == 16


def test_tool_from_mcp_handles_missing_annotations_and_description() -> None:
    sdk_tool = Tool(name="ping", description=None, inputSchema={"type": "object"})
    contract = tool_from_mcp("server", sdk_tool)
    assert contract.description is None
    assert contract.parameters == []
    assert contract.annotations.read_only_hint is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/mcp_client/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.mcp_client.session'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/mcp_client/stdio.py
"""Process-spawning helpers for stdio MCP servers.

MCP servers invoked here are treated as untrusted local processes: the
command/args are passed as a list (never shell=True) and no output beyond
the MCP protocol stream is trusted or persisted.
"""

from __future__ import annotations

import shlex


def parse_command(command_line: str) -> tuple[str, list[str]]:
    parts = shlex.split(command_line)
    if not parts:
        raise ValueError("Empty server command")
    return parts[0], parts[1:]
```

```python
# src/mcplint/mcp_client/session.py
"""Connects to a stdio MCP server and produces an MCPServerSnapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcplint.mcp_client.canonical import stable_tool_id
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

if TYPE_CHECKING:
    from mcp.types import Tool as SDKTool

SNAPSHOT_SCHEMA_VERSION = "1.0"


def tool_from_mcp(server_name: str, tool: "SDKTool") -> ToolContract:
    schema = tool.inputSchema or {"type": "object"}
    properties: dict[str, object] = schema.get("properties", {})  # type: ignore[assignment]
    required: list[str] = schema.get("required", [])  # type: ignore[assignment]

    parameters = [
        ParameterContract(
            name=name,
            json_schema=prop_schema if isinstance(prop_schema, dict) else {},
            required=name in required,
            description=(
                prop_schema.get("description") if isinstance(prop_schema, dict) else None
            ),
        )
        for name, prop_schema in properties.items()
    ]

    annotations = ToolAnnotation()
    if tool.annotations is not None:
        annotations = ToolAnnotation(
            title=tool.annotations.title,
            read_only_hint=tool.annotations.readOnlyHint,
            destructive_hint=tool.annotations.destructiveHint,
            idempotent_hint=tool.annotations.idempotentHint,
            open_world_hint=tool.annotations.openWorldHint,
        )

    return ToolContract(
        id=stable_tool_id(server_name, tool.name),
        name=tool.name,
        description=tool.description,
        input_schema=schema,
        output_schema=tool.outputSchema,
        parameters=parameters,
        annotations=annotations,
        raw=tool.model_dump(mode="json"),
    )


async def collect_stdio_snapshot(
    command: str, args: list[str], *, env: dict[str, str] | None = None
) -> MCPServerSnapshot:
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()
            server_name = init_result.serverInfo.name
            server_version = init_result.serverInfo.version
            listed = await session.list_tools()
            tools = [tool_from_mcp(server_name, t) for t in listed.tools]

    command_line = " ".join([command, *args])
    return MCPServerSnapshot(
        metadata=ArtifactMetadata.create(schema_version=SNAPSHOT_SCHEMA_VERSION),
        server_name=server_name,
        server_version=server_version,
        transport="stdio",
        command=command_line,
        tools=tools,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/mcp_client/test_session.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the integration test against the example server**

```python
# tests/integration/test_example_servers.py
import sys
from pathlib import Path

import pytest

from mcplint.mcp_client.session import collect_stdio_snapshot

EXAMPLES = Path(__file__).parent.parent.parent / "examples"


@pytest.mark.asyncio
async def test_collect_snapshot_from_good_server() -> None:
    server_path = EXAMPLES / "good_server" / "server.py"
    snapshot = await collect_stdio_snapshot(sys.executable, [str(server_path)])
    assert snapshot.server_name == "good-customer-server"
    tool_names = {tool.name for tool in snapshot.tools}
    assert tool_names == {"get_customer", "search_customers"}
    get_customer = snapshot.get_tool("get_customer")
    assert get_customer is not None
    assert get_customer.description is not None
    assert "customer_id" in get_customer.parameter_names()
```

`tests/integration/__init__.py` — empty file.

- [ ] **Step 6: Run integration test to verify it passes**

Run: `pytest tests/integration/test_example_servers.py -v`
Expected: PASS (1 test) — spawns the real example server as a subprocess over stdio, no network calls.

- [ ] **Step 7: Commit**

```bash
git add src/mcplint/mcp_client/stdio.py src/mcplint/mcp_client/session.py tests/unit/mcp_client/test_session.py tests/integration/__init__.py tests/integration/test_example_servers.py
git commit -m "feat: collect MCPServerSnapshot from a live stdio MCP server"
```

---

### Task 8: `mcplint inspect` CLI command

**Files:**
- Create: `src/mcplint/cli/__init__.py`
- Create: `src/mcplint/cli/main.py`
- Create: `src/mcplint/cli/commands/__init__.py`
- Create: `src/mcplint/cli/commands/inspect_cmd.py`
- Test: `tests/cli/__init__.py`
- Test: `tests/cli/test_inspect.py`

**Interfaces:**
- Consumes: `parse_command`, `collect_stdio_snapshot` (Task 7).
- Produces: Typer app `app` in `mcplint.cli.main`, registered as the `mcplint` console script (Task 1).
- Produces: `inspect --server "<command line>"` prints a Rich table of tool name / description / parameter count / destructive flag, exits `0` on success.
- Produces: exit code `1` with a Rich-formatted error message (via `typer.Exit(code=1)`) if the server fails to start or `list_tools` raises.

- [ ] **Step 1: Write the failing CLI test**

```python
# tests/cli/test_inspect.py
import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def test_inspect_lists_tools() -> None:
    result = runner.invoke(
        app, ["inspect", "--server", f"{sys.executable} {GOOD_SERVER}"]
    )
    assert result.exit_code == 0, result.output
    assert "get_customer" in result.output
    assert "search_customers" in result.output


def test_inspect_fails_on_bad_command() -> None:
    result = runner.invoke(app, ["inspect", "--server", "this-command-does-not-exist"])
    assert result.exit_code == 1
```

`tests/cli/__init__.py` — empty file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_inspect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.cli'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/cli/__init__.py
```

(empty)

```python
# src/mcplint/cli/commands/__init__.py
```

(empty)

```python
# src/mcplint/cli/commands/inspect_cmd.py
"""`mcplint inspect` — connect to an MCP server and print its tool contracts."""

from __future__ import annotations

import anyio
import typer
from rich.console import Console
from rich.table import Table

from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command

console = Console()
error_console = Console(stderr=True)


def inspect_command(
    server: str = typer.Option(..., "--server", help="Command line to launch the MCP server."),
) -> None:
    command, args = parse_command(server)

    try:
        snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to inspect server:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Tools on {snapshot.server_name}")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Params", justify="right")
    table.add_column("Destructive", justify="center")

    for tool in snapshot.tools:
        table.add_row(
            tool.name,
            tool.description or "[dim]—[/dim]",
            str(len(tool.parameters)),
            "yes" if tool.annotations.destructive_hint else "",
        )

    console.print(table)
```

```python
# src/mcplint/cli/main.py
"""MCPLint CLI entrypoint."""

from __future__ import annotations

import typer

from mcplint.cli.commands.inspect_cmd import inspect_command

app = typer.Typer(name="mcplint", help="ESLint for MCP tool contracts.")
app.command("inspect")(inspect_command)


if __name__ == "__main__":
    app()
```

Add `anyio` to `pyproject.toml` `dependencies` (it's already a transitive dependency of `mcp`, but pin it explicitly since we import it directly):

```toml
  "anyio>=4.4",
```

Re-run `pip install -e ".[dev]"` after editing `pyproject.toml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_inspect.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Verify the console script works end-to-end**

Run: `mcplint inspect --server "python examples/good_server/server.py"`
Expected: a Rich table listing `get_customer` and `search_customers` with descriptions and param counts, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add src/mcplint/cli/ tests/cli/ pyproject.toml
git commit -m "feat: add mcplint inspect CLI command"
```

---

### Task 9: Phase 1 verification gate

**Files:**
- Modify: `CHANGELOG.md` (create if absent)
- Modify: `IMPLEMENTATION_STATUS.md` (create if absent)

- [ ] **Step 1: Run Ruff**

Run: `source .venv/bin/activate && ruff check src tests examples`
Expected: `All checks passed!` — fix any findings before proceeding.

- [ ] **Step 2: Run MyPy**

Run: `mypy src`
Expected: `Success: no issues found` — fix any findings before proceeding. (Note: `examples/` and `tests/` are intentionally excluded from strict MyPy; only `src` is gated.)

- [ ] **Step 3: Run full test suite with coverage**

Run: `pytest --cov=mcplint --cov-report=term-missing`
Expected: all tests pass; note coverage % for `models` and `mcp_client` packages.

- [ ] **Step 4: Write `CHANGELOG.md`**

```markdown
# Changelog

## [Unreleased]

### Added
- Project scaffolding (`pyproject.toml`, package layout, dev tooling).
- Core Pydantic models: `ArtifactMetadata`, `SourceLocation`, `ParameterContract`,
  `ToolAnnotation`, `ToolContract`, `MCPServerSnapshot`.
- Canonicalization module: deterministic stable tool IDs, byte-stable snapshot JSON.
- Stdio MCP client: `collect_stdio_snapshot`, mapping SDK `Tool` objects to `ToolContract`.
- `examples/good_server`: a well-documented example MCP server fixture.
- `mcplint inspect --server "<command>"` CLI command with Rich table output.
```

- [ ] **Step 5: Write `IMPLEMENTATION_STATUS.md`**

```markdown
# Implementation Status

## Completed (Phase 1)
- Project scaffolding, editable install, Ruff/MyPy/pytest gate.
- Models: ArtifactMetadata, SourceLocation, ParameterContract, ToolAnnotation,
  ToolContract, MCPServerSnapshot.
- Canonicalization: stable_tool_id, canonical_json.
- Stdio snapshot collection against the real `mcp` SDK (verified: mcp==1.28.1).
- `examples/good_server` fixture + integration test.
- `mcplint inspect` CLI command with CI-meaningful exit codes.

## Incomplete
- `snapshot`, `scan`, `benchmark`, `fix`, `compare`, `rules` commands (Phase 2+).
- Rule engine, RuleRegistry, all 15 built-in rules (Phase 2/3).
- Ambiguity engine (Phase 3).
- Configuration loading (`mcplint.yaml`) (Phase 3).
- Benchmark dataset format, fake provider, scorer (Phase 4).
- Anthropic provider, compare command, fix suggestions (Phase 5).
- SARIF/HTML reporters, packaging polish, docs (Phase 6).
- HTTP transport for MCP servers (security constraints: timeout, response-size
  limit, header redaction) — not yet implemented, needed before Phase 6 docs
  claim HTTP support.

## Known limitations
- `inspect` only supports stdio transport.
- No config file support yet — `inspect` takes CLI flags only.

## Decisions made
- Targeted Python 3.11 explicitly (via Homebrew python3.11) instead of the
  system Python 3.14, to avoid dependency-compatibility risk with optional
  extras (sentence-transformers) later in the project.
- Verified official `mcp` SDK API surface (v1.28.1) directly before writing
  code: `StdioServerParameters`, `stdio_client`, `ClientSession.initialize`/
  `list_tools`, `Tool`/`ToolAnnotations` field names.
- `ToolContract.raw` stores the verbatim SDK tool dump so later rules can
  inspect fields not yet promoted to typed model fields.

## Next task
Phase 2: rule engine (`Rule` ABC, `RuleRegistry`), `Finding`/`RuleMetadata`/
`LintReport` models, first five rules (`missing-tool-description`,
`description-repeats-name`, `vague-tool-description`,
`missing-parameter-description`, `schema-description-type-conflict`), and
terminal + JSON reporters wired to a new `scan` command.
```

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md IMPLEMENTATION_STATUS.md
git commit -m "docs: record Phase 1 status and changelog"
```
