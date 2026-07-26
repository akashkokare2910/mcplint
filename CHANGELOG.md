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
- Benchmark models: `ExpectedToolCall`, `BenchmarkCase`, `BenchmarkDataset`,
  `ActualToolCall`, `BenchmarkTrial`, `BenchmarkResult`.
- `ToolCallingProvider` protocol + `ProviderResult`; `FakeProvider` for
  network-free tests and dry runs.
- Deterministic scorer (`score_trial`, `aggregate_metrics`): exact
  tool-selection accuracy, valid-argument rate (JSON Schema validated),
  required-argument accuracy, forbidden-tool invocation rate, no-tool rate,
  mean/P95 latency, total estimated cost, per-case pass rate, and stability
  across repeated trials. No LLM judge.
- `mcplint benchmark DATASET --server "<command>" --provider fake --runs N`
  CLI command with terminal/JSON output and `--output PATH`.
  `--provider anthropic|openai` is recognized but raises a clear
  "not implemented yet" error (Phase 5).
- `examples/ambiguous_customer_server/customer-tools.evals.yaml`: the
  get/search/update/delete-customer confusion dataset required by the spec.
- `AnthropicProvider`: verified against the real `anthropic` SDK (0.120.0);
  API errors surface as a scored `ProviderResult.error`, not a crash;
  illustrative per-model cost table. `OpenAIProvider` is a typed stub.
  `--provider anthropic` now works end-to-end via `mcplint benchmark`.
- `ComparisonReport` model + `compare/differ.py` (`diff_tool_names`,
  `diff_tool_contracts`, `diff_findings`, `diff_ambiguity`, `diff_benchmarks`).
- `mcplint compare --baseline --candidate [--dataset --min-accuracy-delta]`
  CLI command with a Rich terminal reporter; fails CI (exit 1) when the
  accuracy delta falls below the threshold.
- `RewriteSuggestion` model + `fix/suggest.py`: deterministic, schema-derived
  rewrite suggestions (output shape, enum/numeric constraints, destructive
  warnings, tool-distinction placeholders, description truncation).
  Markdown patch report reporter.
- `mcplint fix --snapshot [--output PATH]` CLI command — never overwrites
  source files; `--llm-provider` is recognized but explicitly rejected
  until LLM-assisted rewriting is implemented.
- `ScoreBreakdown` model + `core/score.py::compute_score`: explainable 0-100
  score, capped per category (critical/error, warning/info, ambiguity,
  schema completeness, safety clarity, optional benchmark accuracy), with
  an explicit not-a-scientific-metric disclaimer. Shown in the terminal
  reporter.
- SARIF 2.1.0 reporter (`reporters/sarif.py`) with a full rule catalogue
  and per-finding results/locations.
- Standalone, self-contained HTML report (`reporters/html.py` + Jinja2
  template, embedded CSS, no external requests): score, findings by
  severity, tool inventory, ambiguity pairs, and optional
  benchmark/comparison/fix-suggestion sections.
- `mcplint scan --format sarif|html` and a new global `--output PATH` to
  also write the rendered report to a file.
- `mcplint --version`.
- Packaging: `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, GitHub issue/PR templates, `ci.yml`/`release.yml`
  GitHub Actions, a documented example scan-and-upload-SARIF workflow,
  `Dockerfile`, `.pre-commit-config.yaml`.
- Full README rewrite: quickstart, real example output, architecture,
  rule catalogue, ambiguity engine explanation, benchmark/compare/fix/CI/
  plugin guides, limitations, roadmap, and a comparison section.
