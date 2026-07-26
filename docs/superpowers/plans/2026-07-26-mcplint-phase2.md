# MCPLint Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rule engine (`Rule` ABC, `RuleContext`, `RuleRegistry`), `Finding`/`RuleMetadata`/`LintReport`/`Severity` models, five deterministic rules, snapshot persistence, terminal + JSON reporters, and the `mcplint snapshot` / `mcplint scan` CLI commands.

**Architecture:** Rules are stateless classes with class-level metadata (`id`, `title`, `description`, `default_severity`, `tags`) and a `check(tool, context) -> list[Finding]` method. `RuleRegistry` holds built-in rules plus optional entry-point plugins. `core/engine.py` is the pure function that runs every registered rule over every tool in a snapshot and assembles a `LintReport` — no I/O. Reporters are pure functions `LintReport -> str`. The `scan` command is the only place that ties snapshot acquisition (`--server` or `--snapshot`), the engine, and a reporter together, and computes the process exit code from `--fail-on`.

**Tech Stack:** Same as Phase 1 (Pydantic v2, Typer, Rich, pytest). No new external dependencies.

## Global Constraints

- No LLM calls — rules 1-14 (this phase implements 5 of them) must be pure deterministic Python (spec p.3).
- Every `Finding` carries: rule ID, severity, concise message, evidence, affected tool, affected JSON path, remediation guidance, confidence 0-1 (spec p.3-4).
- Confidence must reflect actual certainty — do not hardcode 1.0 for heuristic rules (spec p.4).
- `LintReport` is a persisted artifact → must embed `ArtifactMetadata` (schema_version/generated_at/mcplint_version).
- Commands must return meaningful non-zero exit codes for CI (spec p.2).
- Reuse `SourceLocation` (`models/contracts.py`) for a finding's tool/JSON-path location rather than duplicating fields.
- Ruff/MyPy/pytest clean at the end of the phase (spec p.11).

---

### Task 1: `Severity`, `Finding`, `RuleMetadata`, `LintReport` models

**Files:**
- Create: `src/mcplint/models/findings.py`
- Test: `tests/unit/models/test_findings.py`

**Interfaces:**
- Consumes: `ArtifactMetadata` (`models/common.py`), `SourceLocation` (`models/contracts.py`).
- Produces: `Severity(str, Enum)` with values `"error"`, `"warning"`, `"info"`.
- Produces: `Finding(BaseModel)`: `rule_id: str`, `severity: Severity`, `message: str`, `evidence: str`, `location: SourceLocation`, `remediation: str`, `confidence: float` (validated `0.0 <= confidence <= 1.0` via `Field(ge=0.0, le=1.0)`).
- Produces: `RuleMetadata(BaseModel)`: `id: str`, `title: str`, `description: str`, `default_severity: Severity`, `tags: list[str] = []`.
- Produces: `LintReport(BaseModel)`: `metadata: ArtifactMetadata`, `server_name: str`, `findings: list[Finding]`, with method `LintReport.count_by_severity() -> dict[Severity, int]`.
- Consumed by: every `Rule.check()` (Task 3), `core/engine.py` (Task 4), reporters (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/models/test_findings.py
import pytest
from pydantic import ValidationError

from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, RuleMetadata, Severity
from mcplint.models.common import ArtifactMetadata
from datetime import UTC, datetime


def _finding(severity: Severity = Severity.ERROR) -> Finding:
    return Finding(
        rule_id="missing-tool-description",
        severity=severity,
        message="Tool has no description.",
        evidence="description is None",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description explaining what the tool does and when to use it.",
        confidence=1.0,
    )


def test_finding_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="x",
            severity=Severity.ERROR,
            message="m",
            evidence="e",
            location=SourceLocation(tool_name="t", json_path="$"),
            remediation="r",
            confidence=1.5,
        )


def test_rule_metadata_defaults_empty_tags() -> None:
    meta = RuleMetadata(
        id="missing-tool-description",
        title="Missing tool description",
        description="Flags tools with no description.",
        default_severity=Severity.ERROR,
    )
    assert meta.tags == []


def test_lint_report_count_by_severity() -> None:
    report = LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        findings=[_finding(Severity.ERROR), _finding(Severity.WARNING), _finding(Severity.ERROR)],
    )
    counts = report.count_by_severity()
    assert counts[Severity.ERROR] == 2
    assert counts[Severity.WARNING] == 1
    assert counts.get(Severity.INFO, 0) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_findings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.models.findings'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/models/findings.py
"""Finding, rule metadata, and the aggregate lint report."""

from __future__ import annotations

from collections import Counter
from enum import Enum

from pydantic import BaseModel, Field

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    evidence: str
    location: SourceLocation
    remediation: str
    confidence: float = Field(ge=0.0, le=1.0)


class RuleMetadata(BaseModel):
    id: str
    title: str
    description: str
    default_severity: Severity
    tags: list[str] = Field(default_factory=list)


class LintReport(BaseModel):
    metadata: ArtifactMetadata
    server_name: str
    findings: list[Finding]

    def count_by_severity(self) -> dict[Severity, int]:
        return dict(Counter(finding.severity for finding in self.findings))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/models/test_findings.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/models/findings.py tests/unit/models/test_findings.py
git commit -m "feat: add Severity, Finding, RuleMetadata, LintReport models"
```

---

### Task 2: `Rule` ABC, `RuleContext`, `RuleRegistry`

**Files:**
- Create: `src/mcplint/core/__init__.py`
- Create: `src/mcplint/core/rules/__init__.py`
- Create: `src/mcplint/core/rules/base.py`
- Create: `src/mcplint/core/registry.py`
- Test: `tests/unit/core/__init__.py`
- Test: `tests/unit/core/test_registry.py`

**Interfaces:**
- Consumes: `ToolContract` (`models/contracts.py`), `Finding`, `RuleMetadata`, `Severity` (Task 1), `MCPServerSnapshot` (`models/snapshot.py`).
- Produces: `RuleContext(BaseModel)` (arbitrary_types allowed): `snapshot: MCPServerSnapshot`.
- Produces: `Rule` ABC (`core/rules/base.py`) with `ClassVar[str] id`, `ClassVar[str] title`, `ClassVar[str] description`, `ClassVar[Severity] default_severity`, `ClassVar[tuple[str, ...]] tags = ()`, abstract `check(self, tool: ToolContract, context: RuleContext) -> list[Finding]`, and `classmethod metadata(cls) -> RuleMetadata`.
- Produces: `RuleRegistry` (`core/registry.py`): `register(rule: Rule) -> None` (raises `ValueError` on duplicate `rule.id`), `get(rule_id: str) -> Rule | None`, `all() -> list[Rule]` (sorted by `id`), `load_entry_point_plugins() -> None` (iterates `importlib.metadata.entry_points(group="mcplint.rules")`, instantiates and registers each).
- Consumed by: all 5 rules (Task 3), `core/engine.py` (Task 4), `scan` command (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_registry.py
import pytest

from mcplint.core.registry import RuleRegistry
from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.findings import Finding, Severity
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.models.common import ArtifactMetadata
from datetime import UTC, datetime


class _FakeRule(Rule):
    id = "fake-rule"
    title = "Fake rule"
    description = "A rule used only in tests."
    default_severity = Severity.INFO

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        return []


def test_register_and_get() -> None:
    registry = RuleRegistry()
    registry.register(_FakeRule())
    found = registry.get("fake-rule")
    assert found is not None
    assert found.metadata().title == "Fake rule"


def test_register_duplicate_raises() -> None:
    registry = RuleRegistry()
    registry.register(_FakeRule())
    with pytest.raises(ValueError, match="fake-rule"):
        registry.register(_FakeRule())


def test_all_sorted_by_id() -> None:
    class _ARule(_FakeRule):
        id = "a-rule"

    class _ZRule(_FakeRule):
        id = "z-rule"

    registry = RuleRegistry()
    registry.register(_ZRule())
    registry.register(_ARule())
    assert [rule.id for rule in registry.all()] == ["a-rule", "z-rule"]


def test_rule_context_holds_snapshot() -> None:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[],
    )
    context = RuleContext(snapshot=snapshot)
    assert context.snapshot.server_name == "s"
```

`tests/unit/core/__init__.py` — empty file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.core'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/core/__init__.py
```

(empty)

```python
# src/mcplint/core/rules/__init__.py
```

(empty)

```python
# src/mcplint/core/rules/base.py
"""The Rule contract every deterministic and plugin rule implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, RuleMetadata, Severity
from mcplint.models.snapshot import MCPServerSnapshot


class RuleContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot: MCPServerSnapshot


class Rule(ABC):
    id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    default_severity: ClassVar[Severity]
    tags: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]: ...

    @classmethod
    def metadata(cls) -> RuleMetadata:
        return RuleMetadata(
            id=cls.id,
            title=cls.title,
            description=cls.description,
            default_severity=cls.default_severity,
            tags=list(cls.tags),
        )
```

```python
# src/mcplint/core/registry.py
"""Collects built-in and plugin rules for the lint engine to run."""

from __future__ import annotations

from importlib.metadata import entry_points

from mcplint.core.rules.base import Rule


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.id in self._rules:
            raise ValueError(f"Rule '{rule.id}' is already registered")
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def all(self) -> list[Rule]:
        return [self._rules[key] for key in sorted(self._rules)]

    def load_entry_point_plugins(self) -> None:
        for entry_point in entry_points(group="mcplint.rules"):
            rule_cls = entry_point.load()
            self.register(rule_cls())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/test_registry.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/core/__init__.py src/mcplint/core/rules/__init__.py src/mcplint/core/rules/base.py src/mcplint/core/registry.py tests/unit/core/__init__.py tests/unit/core/test_registry.py
git commit -m "feat: add Rule ABC, RuleContext, RuleRegistry"
```

---

### Task 3: Five built-in rules

**Files:**
- Create: `src/mcplint/core/rules/description_rules.py`
- Create: `src/mcplint/core/rules/schema_rules.py`
- Create: `src/mcplint/core/rules/builtin.py`
- Test: `tests/unit/core/rules/__init__.py`
- Test: `tests/unit/core/rules/test_description_rules.py`
- Test: `tests/unit/core/rules/test_schema_rules.py`

**Interfaces:**
- Consumes: `Rule`, `RuleContext` (Task 2); `ToolContract`, `ParameterContract`, `ToolAnnotation` (`models/contracts.py`); `Finding`, `Severity` (Task 1).
- Produces concrete rules, each a `Rule` subclass with a fixed `id`:
  - `MissingToolDescriptionRule` — `id = "missing-tool-description"`
  - `DescriptionRepeatsNameRule` — `id = "description-repeats-name"`
  - `VagueToolDescriptionRule` — `id = "vague-tool-description"`
  - `MissingParameterDescriptionRule` — `id = "missing-parameter-description"`
  - `SchemaDescriptionTypeConflictRule` — `id = "schema-description-type-conflict"`
- Produces: `BUILTIN_RULES: list[type[Rule]]` in `core/rules/builtin.py`, consumed by `RuleRegistry` construction helper (Task 4) and the `rules` CLI command (future phase).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/core/rules/test_description_rules.py
from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.description_rules import (
    DescriptionRepeatsNameRule,
    MissingToolDescriptionRule,
    VagueToolDescriptionRule,
)
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.models.common import ArtifactMetadata
from datetime import UTC, datetime


def _tool(name: str, description: str | None, parameters: list = []) -> ToolContract:  # noqa: B006
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters,
        annotations=ToolAnnotation(),
        raw={},
    )


def _context(*tools: ToolContract) -> RuleContext:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )
    return RuleContext(snapshot=snapshot)


def test_missing_tool_description_flags_none() -> None:
    tool = _tool("delete_customer", None)
    findings = MissingToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "missing-tool-description"
    assert findings[0].confidence == 1.0


def test_missing_tool_description_flags_blank() -> None:
    tool = _tool("delete_customer", "   ")
    findings = MissingToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_missing_tool_description_passes_with_text() -> None:
    tool = _tool("delete_customer", "Deletes a customer permanently.")
    assert MissingToolDescriptionRule().check(tool, _context(tool)) == []


def test_description_repeats_name_flags_bare_restatement() -> None:
    tool = _tool("get_customer", "Get customer")
    findings = DescriptionRepeatsNameRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "description-repeats-name"


def test_description_repeats_name_passes_with_detail() -> None:
    tool = _tool(
        "get_customer",
        "Retrieve a single customer record by its exact customer ID.",
    )
    assert DescriptionRepeatsNameRule().check(tool, _context(tool)) == []


def test_description_repeats_name_skips_missing_description() -> None:
    tool = _tool("get_customer", None)
    assert DescriptionRepeatsNameRule().check(tool, _context(tool)) == []


def test_vague_tool_description_flags_short_description() -> None:
    tool = _tool("get_customer", "Gets data.")
    findings = VagueToolDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "vague-tool-description"


def test_vague_tool_description_passes_with_enough_detail() -> None:
    tool = _tool(
        "get_customer",
        "Retrieve a single customer record by its exact customer ID (format CUST-XXXX).",
    )
    assert VagueToolDescriptionRule().check(tool, _context(tool)) == []


def test_vague_tool_description_skips_missing_description() -> None:
    tool = _tool("get_customer", None)
    assert VagueToolDescriptionRule().check(tool, _context(tool)) == []
```

```python
# tests/unit/core/rules/test_schema_rules.py
from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.schema_rules import (
    MissingParameterDescriptionRule,
    SchemaDescriptionTypeConflictRule,
)
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.models.common import ArtifactMetadata
from datetime import UTC, datetime


def _tool_with_params(parameters: list[ParameterContract]) -> ToolContract:
    return ToolContract(
        id="id-1",
        name="search_customers",
        description="Search for customers.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters,
        annotations=ToolAnnotation(),
        raw={},
    )


def _context(tool: ToolContract) -> RuleContext:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    return RuleContext(snapshot=snapshot)


def test_missing_parameter_description_flags_each_undocumented_param() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(name="company", json_schema={"type": "string"}, required=True, description=None),
            ParameterContract(
                name="status", json_schema={"type": "string"}, required=False, description="active or inactive"
            ),
        ]
    )
    findings = MissingParameterDescriptionRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].location.json_path == "$.inputSchema.properties.company"


def test_missing_parameter_description_passes_when_documented() -> None:
    tool = _tool_with_params(
        [ParameterContract(name="company", json_schema={"type": "string"}, required=True, description="Company name.")]
    )
    assert MissingParameterDescriptionRule().check(tool, _context(tool)) == []


def test_schema_description_type_conflict_flags_count_as_string() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="limit",
                json_schema={"type": "string"},
                required=False,
                description="The number of results to return.",
            )
        ]
    )
    findings = SchemaDescriptionTypeConflictRule().check(tool, _context(tool))
    assert len(findings) == 1
    assert findings[0].rule_id == "schema-description-type-conflict"


def test_schema_description_type_conflict_flags_list_as_string() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="tags",
                json_schema={"type": "string"},
                required=False,
                description="A list of tags to filter by.",
            )
        ]
    )
    findings = SchemaDescriptionTypeConflictRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_schema_description_type_conflict_passes_when_types_match() -> None:
    tool = _tool_with_params(
        [
            ParameterContract(
                name="limit", json_schema={"type": "integer"}, required=False, description="The number of results."
            ),
            ParameterContract(
                name="tags", json_schema={"type": "array"}, required=False, description="A list of tags."
            ),
        ]
    )
    assert SchemaDescriptionTypeConflictRule().check(tool, _context(tool)) == []


def test_schema_description_type_conflict_skips_undocumented_param() -> None:
    tool = _tool_with_params(
        [ParameterContract(name="limit", json_schema={"type": "string"}, required=False, description=None)]
    )
    assert SchemaDescriptionTypeConflictRule().check(tool, _context(tool)) == []
```

`tests/unit/core/rules/__init__.py` — empty file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/rules -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.core.rules.description_rules'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/core/rules/description_rules.py
"""Rules that judge a tool's top-level description text."""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, Severity
from mcplint.models.contracts import SourceLocation

MIN_DESCRIPTION_WORDS = 4


def _normalize_words(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [word for word in cleaned.split() if word]


class MissingToolDescriptionRule(Rule):
    id = "missing-tool-description"
    title = "Missing tool description"
    description = "Flags tools with no description or a whitespace-only description."
    default_severity = Severity.ERROR
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if tool.description is not None and tool.description.strip():
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' has no description.",
                evidence="description is missing or blank",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Add a description explaining what the tool does, its inputs, "
                    "and when an agent should choose it over similar tools."
                ),
                confidence=1.0,
            )
        ]


class DescriptionRepeatsNameRule(Rule):
    id = "description-repeats-name"
    title = "Description repeats the tool name"
    description = (
        "Flags descriptions that only restate the tool name in words, adding no "
        "information beyond what the name already conveys."
    )
    default_severity = Severity.WARNING
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or not tool.description.strip():
            return []
        name_words = _normalize_words(tool.name.replace("_", " ").replace("-", " "))
        description_words = _normalize_words(tool.description)
        if description_words != name_words:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' description only restates its name.",
                evidence=f"description '{tool.description}' normalizes to the same words as the tool name",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Explain what the tool actually does: inputs, output shape, "
                    "side effects, and when to prefer it over similar tools."
                ),
                confidence=0.9,
            )
        ]


class VagueToolDescriptionRule(Rule):
    id = "vague-tool-description"
    title = "Vague tool description"
    description = f"Flags descriptions shorter than {MIN_DESCRIPTION_WORDS} words as likely too vague to disambiguate tool choice."
    default_severity = Severity.WARNING
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or not tool.description.strip():
            return []
        words = _normalize_words(tool.description)
        if len(words) >= MIN_DESCRIPTION_WORDS:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' description is very short ({len(words)} words).",
                evidence=f"description: '{tool.description}'",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Expand the description with the specific action, inputs, and "
                    "when an agent should use this tool versus alternatives."
                ),
                confidence=0.7,
            )
        ]
```

```python
# src/mcplint/core/rules/schema_rules.py
"""Rules that cross-check a tool's parameter descriptions against its JSON Schema."""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity

_NUMERIC_HINTS = re.compile(r"\b(number of|count of|quantity of|amount of)\b", re.IGNORECASE)
_LIST_HINTS = re.compile(r"\b(list of|array of|comma-separated list of)\b", re.IGNORECASE)
_BOOLEAN_HINTS = re.compile(r"\b(true or false|boolean flag|yes or no)\b", re.IGNORECASE)


class MissingParameterDescriptionRule(Rule):
    id = "missing-parameter-description"
    title = "Missing parameter description"
    description = "Flags input parameters with no description."
    default_severity = Severity.WARNING
    tags = ("schema",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for param in tool.parameters:
            if param.description and param.description.strip():
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=f"Parameter '{param.name}' on tool '{tool.name}' has no description.",
                    evidence="parameter description is missing or blank",
                    location=SourceLocation(
                        tool_name=tool.name, json_path=f"$.inputSchema.properties.{param.name}"
                    ),
                    remediation=(
                        f"Document '{param.name}': its purpose, expected format, and any "
                        "constraints not already captured by the schema."
                    ),
                    confidence=1.0,
                )
            )
        return findings


class SchemaDescriptionTypeConflictRule(Rule):
    id = "schema-description-type-conflict"
    title = "Description conflicts with parameter schema type"
    description = (
        "Flags parameters whose description implies a different JSON Schema type "
        "than the one declared (e.g. 'number of X' on a string-typed parameter)."
    )
    default_severity = Severity.ERROR
    tags = ("schema",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for param in tool.parameters:
            if not param.description or not param.description.strip():
                continue
            declared_type = param.json_schema.get("type")
            conflict = self._detect_conflict(param.description, declared_type)
            if conflict is None:
                continue
            expected_type, hint = conflict
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=(
                        f"Parameter '{param.name}' on tool '{tool.name}' reads as "
                        f"{expected_type!r} but the schema declares type {declared_type!r}."
                    ),
                    evidence=f"description matched pattern '{hint}', schema type is {declared_type!r}",
                    location=SourceLocation(
                        tool_name=tool.name, json_path=f"$.inputSchema.properties.{param.name}.type"
                    ),
                    remediation=(
                        f"Either change the schema type to {expected_type!r} or rewrite the "
                        "description so it matches the declared type."
                    ),
                    confidence=0.6,
                )
            )
        return findings

    @staticmethod
    def _detect_conflict(description: str, declared_type: object) -> tuple[str, str] | None:
        if _NUMERIC_HINTS.search(description) and declared_type not in ("integer", "number"):
            return "integer", _NUMERIC_HINTS.search(description).group(0)  # type: ignore[union-attr]
        if _LIST_HINTS.search(description) and declared_type != "array":
            return "array", _LIST_HINTS.search(description).group(0)  # type: ignore[union-attr]
        if _BOOLEAN_HINTS.search(description) and declared_type != "boolean":
            return "boolean", _BOOLEAN_HINTS.search(description).group(0)  # type: ignore[union-attr]
        return None
```

```python
# src/mcplint/core/rules/builtin.py
"""Registry of all built-in rule classes."""

from __future__ import annotations

from mcplint.core.rules.base import Rule
from mcplint.core.rules.description_rules import (
    DescriptionRepeatsNameRule,
    MissingToolDescriptionRule,
    VagueToolDescriptionRule,
)
from mcplint.core.rules.schema_rules import (
    MissingParameterDescriptionRule,
    SchemaDescriptionTypeConflictRule,
)

BUILTIN_RULES: list[type[Rule]] = [
    MissingToolDescriptionRule,
    DescriptionRepeatsNameRule,
    VagueToolDescriptionRule,
    MissingParameterDescriptionRule,
    SchemaDescriptionTypeConflictRule,
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/rules -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/core/rules/description_rules.py src/mcplint/core/rules/schema_rules.py src/mcplint/core/rules/builtin.py tests/unit/core/rules/
git commit -m "feat: add five built-in rules (description + schema checks)"
```

---

### Task 4: `RuleRegistry.with_builtin_rules()` + lint engine

**Files:**
- Modify: `src/mcplint/core/registry.py`
- Create: `src/mcplint/core/engine.py`
- Test: `tests/unit/core/test_registry.py` (add one test)
- Test: `tests/unit/core/test_engine.py`

**Interfaces:**
- Consumes: `BUILTIN_RULES` (Task 3), `RuleRegistry` (Task 2), `MCPServerSnapshot`, `LintReport` (Task 1).
- Produces: `RuleRegistry.with_builtin_rules() -> RuleRegistry` classmethod.
- Produces: `lint_snapshot(snapshot: MCPServerSnapshot, registry: RuleRegistry) -> LintReport` in `core/engine.py`.
- Consumed by: `scan` CLI command (Task 8).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/core/test_registry.py`:

```python
def test_with_builtin_rules_registers_all_five() -> None:
    registry = RuleRegistry.with_builtin_rules()
    ids = {rule.id for rule in registry.all()}
    assert ids == {
        "missing-tool-description",
        "description-repeats-name",
        "vague-tool-description",
        "missing-parameter-description",
        "schema-description-type-conflict",
    }
```

```python
# tests/unit/core/test_engine.py
from datetime import UTC, datetime

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _snapshot(*tools: ToolContract) -> MCPServerSnapshot:
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )


def test_lint_snapshot_collects_findings_across_tools() -> None:
    undocumented = ToolContract(
        id="a",
        name="delete_customer",
        description=None,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    documented = ToolContract(
        id="b",
        name="get_customer",
        description="Retrieve a single customer record by its exact customer ID.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(undocumented, documented), RuleRegistry.with_builtin_rules())
    assert report.server_name == "customer-server"
    rule_ids = {f.rule_id for f in report.findings}
    assert "missing-tool-description" in rule_ids
    assert all(f.location.tool_name == "delete_customer" for f in report.findings if f.rule_id == "missing-tool-description")


def test_lint_snapshot_clean_server_has_no_findings() -> None:
    clean = ToolContract(
        id="a",
        name="get_customer",
        description="Retrieve a single customer record by its exact customer ID (format CUST-XXXX).",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(clean), RuleRegistry.with_builtin_rules())
    assert report.findings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/core/test_registry.py tests/unit/core/test_engine.py -v`
Expected: FAIL — `with_builtin_rules` doesn't exist yet; `mcplint.core.engine` doesn't exist.

- [ ] **Step 3: Write minimal implementation**

Add to `src/mcplint/core/registry.py` (append inside the class, after `__init__`):

```python
    @classmethod
    def with_builtin_rules(cls) -> "RuleRegistry":
        from mcplint.core.rules.builtin import BUILTIN_RULES

        registry = cls()
        for rule_cls in BUILTIN_RULES:
            registry.register(rule_cls())
        return registry
```

```python
# src/mcplint/core/engine.py
"""Pure function that runs every registered rule over every tool in a snapshot."""

from __future__ import annotations

from mcplint.core.registry import RuleRegistry
from mcplint.core.rules.base import RuleContext
from mcplint.models.common import ArtifactMetadata
from mcplint.models.findings import LintReport
from mcplint.models.snapshot import MCPServerSnapshot

REPORT_SCHEMA_VERSION = "1.0"


def lint_snapshot(snapshot: MCPServerSnapshot, registry: RuleRegistry) -> LintReport:
    context = RuleContext(snapshot=snapshot)
    findings = []
    for tool in snapshot.tools:
        for rule in registry.all():
            findings.extend(rule.check(tool, context))
    return LintReport(
        metadata=ArtifactMetadata.create(schema_version=REPORT_SCHEMA_VERSION),
        server_name=snapshot.server_name,
        findings=findings,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/core/test_registry.py tests/unit/core/test_engine.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/core/registry.py src/mcplint/core/engine.py tests/unit/core/test_registry.py tests/unit/core/test_engine.py
git commit -m "feat: add RuleRegistry.with_builtin_rules and lint_snapshot engine"
```

---

### Task 5: Snapshot persistence (save/load)

**Files:**
- Create: `src/mcplint/mcp_client/persistence.py`
- Test: `tests/unit/mcp_client/test_persistence.py`

**Interfaces:**
- Consumes: `MCPServerSnapshot` (`models/snapshot.py`).
- Produces: `save_snapshot(snapshot: MCPServerSnapshot, path: Path) -> None` (writes `model_dump_json(indent=2)`).
- Produces: `load_snapshot(path: Path) -> MCPServerSnapshot` (raises `FileNotFoundError` with a clear message if missing).
- Consumed by: `snapshot` CLI command (Task 7), `scan --snapshot` CLI command (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/mcp_client/test_persistence.py
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcplint.mcp_client.persistence import load_snapshot, save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _snapshot() -> MCPServerSnapshot:
    tool = ToolContract(
        id="abc",
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
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        server_version="1.0.0",
        transport="stdio",
        command="python server.py",
        tools=[tool],
    )


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "mcplint.snapshot.json"
    save_snapshot(_snapshot(), path)
    loaded = load_snapshot(path)
    assert loaded.server_name == "customer-server"
    assert loaded.tools[0].name == "get_customer"


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path / "does-not-exist.json")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/mcp_client/test_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.mcp_client.persistence'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/mcp_client/persistence.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/mcp_client/test_persistence.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/mcp_client/persistence.py tests/unit/mcp_client/test_persistence.py
git commit -m "feat: add MCPServerSnapshot save/load persistence"
```

---

### Task 6: Terminal + JSON reporters

**Files:**
- Create: `src/mcplint/reporters/__init__.py`
- Create: `src/mcplint/reporters/terminal.py`
- Create: `src/mcplint/reporters/json_reporter.py`
- Test: `tests/unit/reporters/__init__.py`
- Test: `tests/unit/reporters/test_terminal.py`
- Test: `tests/unit/reporters/test_json_reporter.py`

**Interfaces:**
- Consumes: `LintReport` (Task 1).
- Produces: `render_terminal(report: LintReport) -> str` (`reporters/terminal.py`) — uses a Rich `Console(record=True)` writing to an in-memory buffer so it stays a pure function, no direct printing.
- Produces: `render_json(report: LintReport) -> str` (`reporters/json_reporter.py`) — `report.model_dump_json(indent=2)`.
- Consumed by: `scan` CLI command (Task 8).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/reporters/test_terminal.py
from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.reporters.terminal import render_terminal


def _report(findings: list[Finding]) -> LintReport:
    return LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        findings=findings,
    )


def test_render_terminal_no_findings_reports_clean() -> None:
    output = render_terminal(_report([]))
    assert "customer-server" in output
    assert "0" in output


def test_render_terminal_lists_finding_rule_and_tool() -> None:
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    output = render_terminal(_report([finding]))
    assert "missing-tool-description" in output
    assert "delete_customer" in output
    assert "error" in output.lower()
```

```python
# tests/unit/reporters/test_json_reporter.py
import json
from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.reporters.json_reporter import render_json


def test_render_json_roundtrips_findings() -> None:
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    report = LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="customer-server",
        findings=[finding],
    )
    payload = json.loads(render_json(report))
    assert payload["server_name"] == "customer-server"
    assert payload["findings"][0]["rule_id"] == "missing-tool-description"
    assert payload["findings"][0]["severity"] == "error"
```

`tests/unit/reporters/__init__.py` — empty file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/reporters -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcplint.reporters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/reporters/__init__.py
```

(empty)

```python
# src/mcplint/reporters/terminal.py
"""Render a LintReport as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.models.findings import LintReport, Severity

_SEVERITY_STYLE = {Severity.ERROR: "bold red", Severity.WARNING: "yellow", Severity.INFO: "cyan"}


def render_terminal(report: LintReport) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=120, record=True)

    counts = report.count_by_severity()
    console.print(
        f"[bold]{report.server_name}[/bold] — "
        f"{len(report.findings)} finding(s) "
        f"({counts.get(Severity.ERROR, 0)} error, "
        f"{counts.get(Severity.WARNING, 0)} warning, "
        f"{counts.get(Severity.INFO, 0)} info)"
    )

    if report.findings:
        table = Table()
        table.add_column("Rule")
        table.add_column("Severity")
        table.add_column("Tool")
        table.add_column("Message")
        table.add_column("Confidence", justify="right")
        for finding in report.findings:
            style = _SEVERITY_STYLE[finding.severity]
            table.add_row(
                finding.rule_id,
                f"[{style}]{finding.severity.value}[/{style}]",
                finding.location.tool_name,
                finding.message,
                f"{finding.confidence:.2f}",
            )
        console.print(table)

    return buffer.getvalue()
```

```python
# src/mcplint/reporters/json_reporter.py
"""Render a LintReport as JSON."""

from __future__ import annotations

from mcplint.models.findings import LintReport


def render_json(report: LintReport) -> str:
    return report.model_dump_json(indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/reporters -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/reporters/ tests/unit/reporters/
git commit -m "feat: add terminal and JSON reporters for LintReport"
```

---

### Task 7: `mcplint snapshot` CLI command

**Files:**
- Create: `src/mcplint/cli/commands/snapshot_cmd.py`
- Modify: `src/mcplint/cli/main.py`
- Test: `tests/cli/test_snapshot.py`

**Interfaces:**
- Consumes: `parse_command`, `collect_stdio_snapshot` (`mcp_client/session.py`), `save_snapshot` (Task 5).
- Produces: `snapshot_command(server: str, output: Path) -> None` registered as `mcplint snapshot --server "..." --output PATH`.

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_snapshot.py
import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import load_snapshot

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def test_snapshot_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "mcplint.snapshot.json"
    result = runner.invoke(
        app,
        ["snapshot", "--server", f"{sys.executable} {GOOD_SERVER}", "--output", str(output)],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    snapshot = load_snapshot(output)
    assert {t.name for t in snapshot.tools} == {"get_customer", "search_customers"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_snapshot.py -v`
Expected: FAIL — `snapshot` is not a registered command (`Usage: ... No such command 'snapshot'`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/cli/commands/snapshot_cmd.py
"""`mcplint snapshot` — connect to an MCP server and persist its contract as JSON."""

from __future__ import annotations

from pathlib import Path

import anyio
import typer
from rich.console import Console

from mcplint.mcp_client.persistence import save_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command

console = Console()
error_console = Console(stderr=True)


def snapshot_command(
    server: str = typer.Option(..., "--server", help="Command line to launch the MCP server."),
    output: Path = typer.Option(..., "--output", help="Path to write the snapshot JSON to."),
) -> None:
    command, args = parse_command(server)

    try:
        snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to snapshot server:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    save_snapshot(snapshot, output)
    console.print(f"[green]Wrote snapshot for {snapshot.server_name} to {output}[/green]")
```

Edit `src/mcplint/cli/main.py`:

```python
from mcplint.cli.commands.snapshot_cmd import snapshot_command
```

and after `app.command("inspect")(inspect_command)`:

```python
app.command("snapshot")(snapshot_command)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_snapshot.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add src/mcplint/cli/commands/snapshot_cmd.py src/mcplint/cli/main.py tests/cli/test_snapshot.py
git commit -m "feat: add mcplint snapshot CLI command"
```

---

### Task 8: `mcplint scan` CLI command

**Files:**
- Create: `src/mcplint/cli/commands/scan_cmd.py`
- Modify: `src/mcplint/cli/main.py`
- Test: `tests/cli/test_scan.py`

**Interfaces:**
- Consumes: `parse_command`, `collect_stdio_snapshot`, `load_snapshot`, `RuleRegistry.with_builtin_rules`, `lint_snapshot`, `render_terminal`, `render_json`.
- Produces: `scan_command(server: str | None, snapshot: Path | None, format: str, fail_on: str) -> None` registered as `mcplint scan --server "..."` or `mcplint scan --snapshot PATH`, with `--format terminal|json` (default `terminal`) and `--fail-on error|warning|never` (default `error`).
- Exit codes: `0` if no findings meet-or-exceed `--fail-on`'s severity; `1` otherwise; `2` (Typer's usage-error default) if neither or both of `--server`/`--snapshot` are given.

- [ ] **Step 1: Write the failing tests**

```python
# tests/cli/test_scan.py
import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import save_snapshot
from mcplint.mcp_client.stdio import parse_command
from mcplint.mcp_client.session import tool_from_mcp
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot
from datetime import UTC, datetime

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def _bad_snapshot_path(tmp_path: Path) -> Path:
    tool = ToolContract(
        id="a",
        name="delete_customer",
        description=None,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="bad-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    path = tmp_path / "bad.snapshot.json"
    save_snapshot(snapshot, path)
    return path


def test_scan_snapshot_with_findings_exits_1_by_default(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(app, ["scan", "--snapshot", str(path)])
    assert result.exit_code == 1
    assert "missing-tool-description" in result.output


def test_scan_snapshot_fail_on_never_exits_0(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(app, ["scan", "--snapshot", str(path), "--fail-on", "never"])
    assert result.exit_code == 0


def test_scan_snapshot_json_format(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(app, ["scan", "--snapshot", str(path), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0
    assert '"rule_id": "missing-tool-description"' in result.output


def test_scan_live_server_clean(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", "--server", f"{sys.executable} {GOOD_SERVER}"])
    assert result.exit_code == 0, result.output


def test_scan_requires_server_or_snapshot() -> None:
    result = runner.invoke(app, ["scan"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/cli/test_scan.py -v`
Expected: FAIL — `scan` is not a registered command.

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcplint/cli/commands/scan_cmd.py
"""`mcplint scan` — lint a live MCP server or a saved snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
from rich.console import Console

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.findings import LintReport, Severity
from mcplint.reporters.json_reporter import render_json
from mcplint.reporters.terminal import render_terminal

console = Console()
error_console = Console(stderr=True)

_SEVERITY_RANK = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
_FAIL_ON_THRESHOLD = {"error": _SEVERITY_RANK[Severity.ERROR], "warning": _SEVERITY_RANK[Severity.WARNING]}


def _should_fail(report: LintReport, fail_on: str) -> bool:
    if fail_on == "never":
        return False
    threshold = _FAIL_ON_THRESHOLD[fail_on]
    return any(_SEVERITY_RANK[finding.severity] >= threshold for finding in report.findings)


def scan_command(
    server: Annotated[str | None, typer.Option("--server", help="Command line to launch the MCP server.")] = None,
    snapshot: Annotated[Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format.")] = "terminal",
    fail_on: Annotated[str, typer.Option("--fail-on", help="Minimum severity that fails the command.")] = "error",
) -> None:
    if (server is None) == (snapshot is None):
        error_console.print("[bold red]Exactly one of --server or --snapshot is required.[/bold red]")
        raise typer.Exit(code=2)
    if format not in ("terminal", "json"):
        error_console.print(f"[bold red]Unknown format: {format}[/bold red]")
        raise typer.Exit(code=2)
    if fail_on not in ("error", "warning", "never"):
        error_console.print(f"[bold red]Unknown --fail-on: {fail_on}[/bold red]")
        raise typer.Exit(code=2)

    try:
        if snapshot is not None:
            server_snapshot = load_snapshot(snapshot)
        else:
            assert server is not None
            command, args = parse_command(server)
            server_snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to load server contract:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    report = lint_snapshot(server_snapshot, RuleRegistry.with_builtin_rules())

    if format == "json":
        console.print(render_json(report))
    else:
        console.print(render_terminal(report))

    if _should_fail(report, fail_on):
        raise typer.Exit(code=1)
```

Edit `src/mcplint/cli/main.py`:

```python
from mcplint.cli.commands.scan_cmd import scan_command
```

and:

```python
app.command("scan")(scan_command)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/cli/test_scan.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Verify end-to-end via console script**

Run: `mcplint scan --server "python examples/good_server/server.py"`
Expected: exit code 0, "0 finding(s)" printed.

- [ ] **Step 6: Commit**

```bash
git add src/mcplint/cli/commands/scan_cmd.py src/mcplint/cli/main.py tests/cli/test_scan.py
git commit -m "feat: add mcplint scan CLI command with terminal/json output and CI exit codes"
```

---

### Task 9: Phase 2 verification gate

- [ ] **Step 1: Run Ruff**

Run: `ruff check --fix src tests examples && ruff check src tests examples`
Expected: `All checks passed!`

- [ ] **Step 2: Run MyPy**

Run: `mypy src`
Expected: `Success: no issues found`

- [ ] **Step 3: Run full test suite with coverage**

Run: `pytest --cov=mcplint --cov-report=term-missing`
Expected: all tests pass; `core` and `reporters` packages at or near 100%.

- [ ] **Step 4: Update `CHANGELOG.md` and `IMPLEMENTATION_STATUS.md`**

Add a `### Added` block for Phase 2 (rule engine, 5 rules, snapshot persistence, reporters, `snapshot`/`scan` commands) to `CHANGELOG.md`; update `IMPLEMENTATION_STATUS.md`'s Completed/Incomplete/Next sections to reflect Phase 2 completion and Phase 3 next steps (remaining 10 rules, ambiguity engine, configuration).

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md IMPLEMENTATION_STATUS.md
git commit -m "docs: record Phase 2 status and changelog"
```
