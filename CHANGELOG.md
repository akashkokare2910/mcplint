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
- `Severity`, `Finding`, `RuleMetadata`, `LintReport` models.
- `Rule` ABC, `RuleContext`, `RuleRegistry` (with entry-point plugin loading support).
- Five built-in rules: `missing-tool-description`, `description-repeats-name`,
  `vague-tool-description`, `missing-parameter-description`,
  `schema-description-type-conflict`.
- `lint_snapshot()` engine wiring the registry over every tool in a snapshot.
- Snapshot persistence: `save_snapshot`/`load_snapshot`.
- Terminal and JSON reporters (`render_terminal`, `render_json`).
- `mcplint snapshot --server "<command>" --output PATH` CLI command.
- `mcplint scan --server "<command>"` / `mcplint scan --snapshot PATH` CLI command
  with `--format terminal|json` and `--fail-on error|warning|never`.
- Remaining 10 built-in rules: `missing-return-semantics`,
  `undocumented-error-behaviour`, `undocumented-required-constraint`,
  `tool-name-action-conflict`, `destructive-tool-without-warning`,
  `state-changing-tool-marked-read-only`, `ambiguous-tool-overlap`,
  `missing-tool-distinction`, `excessive-description-length`,
  `undefined-domain-term` — all 15 spec rules now implemented.
- Semantic ambiguity engine (`compute_ambiguity`): name/description/parameter
  Jaccard similarity with structured, inspectable evidence (shared verbs,
  shared entities, overlapping parameters, absent exact-vs-search /
  one-vs-many / read-vs-write distinctions).
- `mcplint.yaml` configuration loading (`MCPLintConfig`): severity overrides,
  ambiguity/description-length thresholds, per-tool rule ignores, benchmark
  defaults. Wired into `scan --config`.
- `mcplint rules` CLI command listing the full rule catalogue.
- `examples/bad_server`: intentionally triggers all 15 built-in rules
  (verified by an integration test).
- `examples/ambiguous_customer_server`: get/search/update/delete customer
  tools for the upcoming benchmark dataset, verified to trigger
  `ambiguous-tool-overlap`.
- `examples/good_server` reworked to use `Annotated[..., Field(description=...)]`
  parameters and explicit tool annotations; verified to produce zero findings.
