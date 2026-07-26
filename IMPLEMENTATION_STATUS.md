# Implementation Status

## Completed (Phase 1)
- Project scaffolding, editable install, Ruff/MyPy/pytest gate — all clean.
- Models: `ArtifactMetadata`, `SourceLocation`, `ParameterContract`, `ToolAnnotation`,
  `ToolContract`, `MCPServerSnapshot`.
- Canonicalization: `stable_tool_id`, `canonical_json`.
- Stdio snapshot collection against the real `mcp` SDK (verified: `mcp==1.28.1`).
- `examples/good_server` fixture + integration test.
- `mcplint inspect` CLI command with CI-meaningful exit codes.

## Completed (Phase 2)
- Models: `Severity` (`StrEnum`), `Finding`, `RuleMetadata`, `LintReport`.
- `Rule` ABC, `RuleContext`, `RuleRegistry` (entry-point plugin loading).
- Five built-in rules with unit tests.
- `lint_snapshot(snapshot, registry) -> LintReport` — pure engine function.
- Snapshot persistence, terminal + JSON reporters.
- `mcplint snapshot` and `mcplint scan` CLI commands.

## Completed (Phase 3)
- Remaining 10 built-in rules — **all 15 spec rules now implemented**:
  - `missing-return-semantics`, `undocumented-error-behaviour`,
    `undocumented-required-constraint` (`completeness_rules.py`)
  - `tool-name-action-conflict`, `destructive-tool-without-warning`,
    `state-changing-tool-marked-read-only` (`safety_rules.py`)
  - `ambiguous-tool-overlap`, `missing-tool-distinction` (`ambiguity_rules.py`,
    backed by the cross-tool `compute_ambiguity` engine in `ambiguity.py`)
  - `excessive-description-length`, `undefined-domain-term` (`completeness_rules.py`)
- Ambiguity engine: 0-1 score from name (25%) + description (45%, stopword-filtered
  Jaccard) + parameter-name (30%) similarity; every flagged pair carries
  structured evidence (`shared_verbs`, `shared_entities`, `overlapping_parameters`,
  and three boolean "absent distinction" flags) — inspectable, not an opaque
  number, per spec p.4.
- `mcplint.yaml` config: `MCPLintConfig` (severity overrides, ambiguity/
  description-length thresholds, per-tool `ignore` entries, `benchmark`
  defaults), loaded via `load_config()` with actionable `ConfigError` messages
  on invalid YAML. `RuleRegistry.with_builtin_rules(config)` applies threshold
  overrides; `lint_snapshot(..., config)` applies ignores and severity overrides.
  Wired into `mcplint scan --config`.
- `mcplint rules` CLI command.
- `examples/bad_server`: 12 tools, each a deliberate trigger for one or more
  rules; an integration test asserts all 15 rule IDs fire.
- `examples/ambiguous_customer_server`: `get_customer`/`search_customers`/
  `update_customer`/`delete_customer`, verified to trigger
  `ambiguous-tool-overlap` between the first two.
- `examples/good_server` reworked (`Annotated[..., Field(description=...)]`
  parameters, explicit `ToolAnnotations`) and verified via integration test
  to produce **zero** findings against the full 15-rule registry — resolves
  the Phase 2 known limitation about undocumented parameters.
- 99 tests passing, 96%+ coverage. Ruff/MyPy clean.

## Completed (Phase 4)
- Models: `ExpectedToolCall`, `BenchmarkCase`, `BenchmarkDataset`, `ActualToolCall`,
  `BenchmarkTrial`, `BenchmarkResult`.
- `ToolCallingProvider` Protocol + `ProviderResult`; `FakeProvider` wraps a plain
  Python function so scorer/runner tests make zero network calls.
- Scorer (`benchmark/scorer.py`): `validate_arguments` (jsonschema-based),
  `score_trial` (exact tool match, forbidden-tool check, argument equality —
  no LLM judge), `aggregate_metrics` (accuracy, valid-argument rate,
  required-argument accuracy, forbidden-tool rate, no-tool rate, mean/P95
  latency, total cost, per-case pass rate, stability).
- `benchmark/runner.py::run_benchmark` ties dataset + tools + provider + scorer
  into a `BenchmarkResult`.
- `benchmark/providers/factory.py::create_provider` — `"fake"` works now;
  `"anthropic"`/`"openai"` raise `ProviderNotAvailableError` with an actionable
  message rather than silently stubbing (per doc's "do not silently stub"
  rule) — real Phase 5 TODO.
- `mcplint benchmark DATASET --server/--snapshot --provider --runs --format
  --output` CLI command, with a Rich terminal reporter for `BenchmarkResult`.
- `examples/ambiguous_customer_server/customer-tools.evals.yaml`: the
  get/search/update/delete-customer confusion dataset, run end-to-end against
  the live example server with `--provider fake` in CLI tests.
- 119 tests passing, 95% coverage. Ruff/MyPy clean.

## Incomplete
- `fix`, `compare` commands (Phase 5).
- Anthropic provider, `compare` command, `fix` suggestions (Phase 5).
- Overall 0-100 explainable score (Phase 6, per spec p.7 — deferred from
  Phase 3 since it's listed under Phase 6 in the doc's phase breakdown and
  benefits from benchmark accuracy being available as an input).
- SARIF/HTML reporters, packaging polish, full docs (Phase 6).
- HTTP transport for MCP servers (timeout, response-size limit, header
  redaction, no auto-redirects per spec's security constraints) — not yet
  implemented.
- Optional sentence-transformer embeddings for the ambiguity engine (the
  `semantic` extra) — interface allows for it (score is a weighted blend)
  but no embedding backend is wired in yet; deterministic token/name/schema
  similarity is the only mode. Not required for v1 per spec ("optional").

## Known limitations
- `inspect`/`snapshot`/`scan` only support stdio transport.
- `--format`/`--output`/`--verbose` global options and SARIF/HTML formats
  are not yet implemented — only `terminal`/`json`.
- The ambiguity engine's Jaccard similarity does no stemming/lemmatization,
  so plural/singular mismatches (e.g. "customer" vs "customers") reduce
  measured overlap between genuinely similar tools. Confirmed while building
  `examples/ambiguous_customer_server`: had to deliberately align tool
  vocabulary (shared parameter names, matching root words) to cross the
  default 0.55 threshold. This is a real precision/recall trade-off of the
  deterministic approach, not a bug — the spec explicitly scopes stemming-free
  token overlap as the baseline and sentence-transformer embeddings as the
  optional upgrade path.
- `undefined-domain-term`'s acronym heuristic (`\b[A-Z]{2,6}\b` minus a
  well-known list) will both under- and over-flag on real-world servers;
  it's intentionally conservative (info severity, confidence 0.4).

## Decisions made
- Targeted Python 3.11 explicitly (via Homebrew `python3.11`).
- Verified the official `mcp` SDK API surface (v1.28.1) directly against a
  running interpreter before writing any code, including confirming that
  `Annotated[T, Field(description=...)]` on FastMCP tool parameters produces
  `description`/`enum` in the generated `inputSchema`, and that a plain
  `dict`/`list` return annotation (vs. `dict[str, str]`) avoids FastMCP
  auto-generating an `outputSchema` — both load-bearing for the example
  servers' intended rule triggers.
- Cross-tool rules (`ambiguous-tool-overlap`, `missing-tool-distinction`)
  still use the standard `Rule.check(tool, context)` signature, iterating
  `context.snapshot.tools` and only emitting a finding when
  `other.name > tool.name`, so each unordered pair is reported exactly once
  even though the engine calls every rule once per tool.
- `AmbiguityPairResult`/`AmbiguityEvidence` are plain frozen dataclasses
  internal to `core/rules/ambiguity.py`, not persisted Pydantic models —
  the spec's model list doesn't include a standalone ambiguity artifact;
  results surface through `Finding.evidence` text.
- Renamed `safety_rules._first_word` to public `first_word` so
  `ambiguity.py` could import it without reaching into a private name.
- Config threshold overrides mutate rule *instances* (`rule.threshold = ...`)
  produced fresh per `with_builtin_rules()` call, never the class attribute —
  no cross-test or cross-request pollution.
- `--config` defaults to `Path("mcplint.yaml")` (spec's documented default)
  and silently falls back to defaults when the file doesn't exist, matching
  `load_config`'s existing missing-path behavior from before the CLI was wired up.

## Next task
Phase 5: Anthropic provider adapter (structure OpenAI as a separate stub
per spec, don't let it block Anthropic), `mcplint compare` (snapshot diff +
optional benchmark re-run + `--min-accuracy-delta` CI threshold), and
`mcplint fix` (deterministic rewrite suggestions first, optional
LLM-assisted rewriting behind an explicit provider flag, Markdown patch
report, never overwrite source files).
