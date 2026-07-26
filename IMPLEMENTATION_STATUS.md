# Implementation Status

## Completed (Phase 1)
- Project scaffolding, editable install, Ruff/MyPy/pytest gate — all clean.
- Models: `ArtifactMetadata`, `SourceLocation`, `ParameterContract`, `ToolAnnotation`,
  `ToolContract`, `MCPServerSnapshot`.
- Canonicalization: `stable_tool_id`, `canonical_json`.
- Stdio snapshot collection against the real `mcp` SDK (verified: `mcp==1.28.1`).
- `examples/good_server` fixture + integration test (spawns a real subprocess over stdio).
- `mcplint inspect` CLI command with CI-meaningful exit codes (0 on success, 1 on
  connection/protocol failure).
- 18 tests passing, 93% overall coverage, 100% on `models` and `mcp_client` packages.

## Incomplete
- `snapshot`, `scan`, `benchmark`, `fix`, `compare`, `rules` commands (Phase 2+).
- Rule engine, `RuleRegistry`, all 15 built-in rules (Phase 2/3).
- `Finding`, `RuleMetadata`, `LintReport` models (Phase 2).
- Ambiguity engine (Phase 3).
- Configuration loading (`mcplint.yaml`) (Phase 3).
- Benchmark dataset format, fake provider, scorer (Phase 4).
- Anthropic provider, `compare` command, `fix` suggestions (Phase 5).
- SARIF/HTML reporters, packaging polish, full docs (Phase 6).
- HTTP transport for MCP servers (timeout, response-size limit, header
  redaction, no auto-redirects per spec's security constraints) — not yet
  implemented, needed before Phase 6 docs claim HTTP support.
- `examples/bad_server`, `examples/ambiguous_customer_server`, benchmark dataset
  showing `get_customer`/`search_customers`/`update_customer`/`delete_customer`
  confusion — deferred to Phase 3/4 once rules exist to trigger.

## Known limitations
- `inspect` only supports stdio transport.
- No config file support yet — `inspect` takes CLI flags only.
- No `--format`/`--output`/`--fail-on` global options yet — those land with the
  reporter abstraction in Phase 2.

## Decisions made
- Targeted Python 3.11 explicitly (via Homebrew `python3.11`) instead of the
  system Python 3.14, to avoid dependency-compatibility risk with optional
  extras (sentence-transformers) later in the project.
- Verified the official `mcp` SDK API surface (v1.28.1) directly against a
  running interpreter before writing any code: `StdioServerParameters`,
  `stdio_client`, `ClientSession.initialize`/`list_tools`, `Tool`/
  `ToolAnnotations` field names all confirmed, not assumed.
- `ToolContract.raw` stores the verbatim SDK tool dump so later rules can
  inspect fields not yet promoted to typed model fields.
- Added an explicit Typer `@app.callback()` in `cli/main.py` — Typer collapses
  to single-command mode when only one command is registered, which would have
  made `mcplint inspect ...` fail; the callback forces subcommand mode ahead
  of Phase 2+ adding more commands.
- Local git identity configured per-repo (not global), using the user's email
  from session context.

## Next task
Phase 2: rule engine (`Rule` ABC, `RuleRegistry`), `Finding`/`RuleMetadata`/
`LintReport` models, first five rules (`missing-tool-description`,
`description-repeats-name`, `vague-tool-description`,
`missing-parameter-description`, `schema-description-type-conflict`), and
terminal + JSON reporters wired to a new `scan` command.
