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
