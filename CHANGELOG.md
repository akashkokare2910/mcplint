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
