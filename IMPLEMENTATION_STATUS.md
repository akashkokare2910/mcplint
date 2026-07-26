# Implementation Status

## Completed (Phase 1)
- Project scaffolding, editable install, Ruff/MyPy/pytest gate — all clean.
- Models: `ArtifactMetadata`, `SourceLocation`, `ParameterContract`, `ToolAnnotation`,
  `ToolContract`, `MCPServerSnapshot`.
- Canonicalization: `stable_tool_id`, `canonical_json`.
- Stdio snapshot collection against the real `mcp` SDK (verified: `mcp==1.28.1`).
- `examples/good_server` fixture + integration test (spawns a real subprocess over stdio).
- `mcplint inspect` CLI command with CI-meaningful exit codes.

## Completed (Phase 2)
- Models: `Severity` (`StrEnum`), `Finding`, `RuleMetadata`, `LintReport`
  (with `count_by_severity()`).
- `Rule` ABC (class-level `id`/`title`/`description`/`default_severity`/`tags`,
  `check(tool, context) -> list[Finding]`), `RuleContext` (frozen, wraps a
  snapshot), `RuleRegistry` (register/get/all, duplicate-id guard,
  `load_entry_point_plugins()` via `importlib.metadata.entry_points(group="mcplint.rules")`,
  `with_builtin_rules()` classmethod).
- Five built-in rules, each with unit tests covering flag and pass cases:
  - `missing-tool-description` (error, confidence 1.0)
  - `description-repeats-name` (warning, confidence 0.9)
  - `vague-tool-description` (warning, confidence 0.7, <4-word threshold)
  - `missing-parameter-description` (warning, confidence 1.0, per-parameter)
  - `schema-description-type-conflict` (error, confidence 0.6, regex-hint based)
- `lint_snapshot(snapshot, registry) -> LintReport` — pure engine function, no I/O.
- Snapshot persistence: `save_snapshot`/`load_snapshot` (JSON roundtrip via Pydantic).
- Reporters: `render_terminal` (Rich, pure function via in-memory console),
  `render_json` (`LintReport.model_dump_json`).
- `mcplint snapshot --server "<cmd>" --output PATH` CLI command.
- `mcplint scan --server "<cmd>"` / `mcplint scan --snapshot PATH` CLI command:
  `--format terminal|json`, `--fail-on error|warning|never` (default `error`),
  exit 0/1 based on whether any finding meets the fail-on threshold, exit 2 on
  usage errors (both or neither of `--server`/`--snapshot` given).
- 54 tests passing, 94% overall coverage; `core`, `models`, `mcp_client`,
  `reporters` packages at or near 100%.

## Incomplete
- `benchmark`, `fix`, `compare`, `rules` commands (Phase 3+).
- Remaining 10 built-in rules: `missing-return-semantics`,
  `undocumented-error-behaviour`, `undocumented-required-constraint`,
  `tool-name-action-conflict`, `destructive-tool-without-warning`,
  `state-changing-tool-marked-read-only`, `ambiguous-tool-overlap`,
  `missing-tool-distinction`, `excessive-description-length`,
  `undefined-domain-term` (Phase 3).
- Semantic ambiguity engine (Phase 3).
- Configuration loading (`mcplint.yaml`), `--config`/`--ignore`/`--severity`
  overrides (Phase 3).
- Overall 0-100 explainable score (Phase 3, per spec p.7).
- Benchmark dataset format, fake provider, scorer (Phase 4).
- Anthropic provider, `compare` command, `fix` suggestions (Phase 5).
- SARIF/HTML reporters, packaging polish, full docs (Phase 6).
- HTTP transport for MCP servers (timeout, response-size limit, header
  redaction, no auto-redirects per spec's security constraints) — not yet
  implemented, needed before Phase 6 docs claim HTTP support.
- `examples/bad_server`, `examples/ambiguous_customer_server`, benchmark dataset
  showing `get_customer`/`search_customers`/`update_customer`/`delete_customer`
  confusion — deferred to Phase 3/4 once the remaining rules and ambiguity
  engine exist to trigger.

## Known limitations
- `inspect`/`snapshot`/`scan` only support stdio transport.
- No config file support yet — commands take CLI flags only; `--config`,
  `--output` (global), `--verbose` not yet wired.
- `examples/good_server`'s parameter docstrings (e.g. `customer_id: the exact
  customer identifier...`) are not propagated into `inputSchema.properties.*.description`
  by FastMCP from a plain function docstring — confirmed by running
  `mcplint scan` against it, which correctly flags `missing-parameter-description`
  for both tools. This is a real, useful finding, not a bug in the rule; fixing
  the example to use `Annotated[str, Field(description=...)]` parameters is
  deferred to Phase 3 when `examples/good_server` is revisited as the "clean"
  baseline for `examples/bad_server` contrast.
- `schema-description-type-conflict`'s regex hints (`number of`, `list of`,
  `true or false`, etc.) are intentionally narrow to stay deterministic and
  low-false-positive; broader semantic conflict detection is out of scope
  for the deterministic rules (rules 1-14 must not use an LLM per spec p.3).

## Decisions made
- Targeted Python 3.11 explicitly (via Homebrew `python3.11`) instead of the
  system Python 3.14, to avoid dependency-compatibility risk with optional
  extras (sentence-transformers) later in the project.
- Verified the official `mcp` SDK API surface (v1.28.1) directly against a
  running interpreter before writing any code.
- `ToolContract.raw` stores the verbatim SDK tool dump so later rules can
  inspect fields not yet promoted to typed model fields.
- Added an explicit Typer `@app.callback()` in `cli/main.py` so the CLI stays
  in subcommand mode as commands are added one at a time.
- All CLI options use `Annotated[...]` (not bare `= typer.Option(...)` defaults)
  for consistency and to avoid B008 lint ambiguity between commands.
- `Finding.location` reuses `SourceLocation` (`models/contracts.py`) rather than
  duplicating `tool_name`/`json_path` fields on `Finding`, per DRY.
- `RuleContext` is a frozen Pydantic model wrapping the snapshot, not a plain
  dataclass, so it validates the same way as every other typed artifact and
  can carry config (Phase 3) without changing the `Rule.check()` signature.
- `Severity` is `StrEnum` (not `str, Enum`) per Ruff UP042 — `StrEnum` is
  available since Python 3.11, which matches the project's floor.
- Local git identity configured per-repo (not global), using the user's email
  from session context.

## Next task
Phase 3: remaining 10 built-in rules, the semantic ambiguity engine
(token/name/description/input-schema similarity, optional sentence-transformer
embeddings, explainable evidence per flagged pair), `mcplint.yaml` configuration
loading, and `examples/bad_server` + `examples/ambiguous_customer_server`
fixtures that intentionally trigger every rule.
