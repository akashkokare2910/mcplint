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

## Completed (Phase 5)
- `AnthropicProvider` (`benchmark/providers/anthropic_provider.py`): verified
  against the real `anthropic` SDK (0.120.0) — `AsyncAnthropic.messages.create`
  tool shape (`name`/`description`/`input_schema`), response content blocks
  (`type == "tool_use"`, `.name`, `.input`), `usage.input_tokens`/
  `output_tokens`. API exceptions are caught and surfaced as a scored
  `ProviderResult.error`, never a crash. Illustrative (not authoritative)
  per-model USD/1M-token pricing table for cost estimation. Tests mock the
  client entirely (`pytest.importorskip("anthropic")` guards them) — zero
  real API calls.
- `OpenAIProvider` (`benchmark/providers/openai_provider.py`): typed stub,
  raises `NotImplementedError` only when `.run()` is actually called — real
  Phase-5-follow-up TODO, doesn't block Anthropic per spec.
- `benchmark/providers/factory.py::create_provider` now fully wires `"fake"`,
  `"anthropic"` (requires `--model`), and `"openai"` (stub).
- `ComparisonReport`, `SchemaChange`, `DescriptionChange`, `AmbiguityScoreChange`
  models. `compare/differ.py`: pure diff functions for tool add/remove,
  schema/description changes, new/resolved findings (matched by rule+tool+
  path+message identity), pairwise ambiguity score changes for tools common
  to both snapshots, and benchmark metric deltas + per-case regressions.
- `mcplint compare --baseline --candidate [--dataset --provider --model --runs
  --min-accuracy-delta --format --output]` — re-runs a benchmark dataset
  against both snapshots' tool lists (no live server needed) when `--dataset`
  is given; exits 1 when the accuracy delta falls below
  `--min-accuracy-delta`.
- `RewriteSuggestion` model. `fix/suggest.py::build_suggestions`/
  `suggest_for_tool`: deterministic, schema-derived clauses for
  `missing-return-semantics` (describes outputSchema fields, or a generic
  fallback when there's no schema), `undocumented-required-constraint`
  (enum values / numeric bounds read directly from the parameter's JSON
  Schema), `destructive-tool-without-warning`, `missing-tool-distinction`
  (low-confidence placeholder naming the other tool), and
  `excessive-description-length` (deterministic truncation at a sentence
  boundary). `missing-tool-description`/`description-repeats-name`/
  `vague-tool-description` get an honest `[TODO ...]` placeholder at
  confidence 0.2 rather than fabricated prose — deterministic mode has no
  LLM to invent real content.
- `reporters/fix_markdown.py::render_fix_markdown` — the Markdown patch report.
- `mcplint fix --snapshot [--output PATH] [--llm-provider ...]` — never
  writes to source files (verified by a test); `--llm-provider` is accepted
  as a flag but explicitly rejected with a clear error until LLM-assisted
  rewriting exists (real TODO, not a silent stub).
- 153 tests passing, 93% coverage. Ruff/MyPy clean.

## Completed (Phase 6)
- `ScoreBreakdown`/`ScoreDeduction` models + `core/score.py::compute_score`:
  documented, per-category-capped 0-100 score (critical/error up to 40 @ 8pts,
  warning/info up to 20 @ 2pts, ambiguity up to 15 @ 5pts, schema completeness
  up to 15 @ 3pts, safety clarity up to 15 @ 5pts, benchmark accuracy up to
  15 proportional to 1-accuracy). Categories are mutually exclusive by
  rule ID so nothing is double-counted. Explicit "not scientifically
  universal" disclaimer on the model. Shown in the terminal reporter.
- SARIF 2.1.0 reporter (`reporters/sarif.py`): full rule catalogue as
  `tool.driver.rules`, one `result` per finding with `ruleId`/`level`/
  `message`/`locations`; severity mapped error->error, warning->warning,
  info->note. Verified with a structural smoke test (three tests covering
  top-level shape, one result's shape, and rule-descriptor severity
  levels) — not full JSON-Schema validation against the real SARIF schema,
  since that would need network access the default test suite doesn't have.
- Standalone HTML reporter (`reporters/html.py` + `templates/report.html.j2`):
  score, findings-by-severity table, tool inventory, ambiguity pairs
  (recomputed live from the snapshot, not stored), and optional
  benchmark/before-after-comparison/remediation-suggestion sections when
  those objects are passed in. Embedded CSS with a dark-mode media query,
  zero external requests, zero `<script>` tags (verified by a test).
  Confirmed the `.j2` template is actually included in the built wheel
  (hatchling includes non-`.py` files under a package dir by default —
  checked by building the wheel and inspecting its contents).
- `mcplint scan --format sarif|html` and a new `--output PATH` global-ish
  option on `scan` to also write the rendered report to a file regardless
  of format.
- `mcplint --version`.
- Packaging: `LICENSE` (MIT), `CONTRIBUTING.md` (dev setup + rule/provider
  extension guides), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  `SECURITY.md` (MCP-servers-are-untrusted-code threat model — running
  `inspect`/`scan`/`benchmark`/`compare` against a server executes that
  server's code locally; planned HTTP-transport security constraints;
  secrets handling). GitHub bug-report/feature-request issue templates,
  PR template. `.github/workflows/ci.yml` (lint, typecheck, unit+cli tests
  with `--cov-fail-under=80`, integration tests, sdist/wheel build).
  `.github/workflows/release.yml` (PyPI trusted publishing on `v*` tags).
  `.github/workflows/example-scan-mcp-server.yml`: a documented example
  workflow for *downstream* users — install MCPLint, invoke their server,
  scan, upload SARIF via `github/codeql-action/upload-sarif`, fail on
  error — no custom JavaScript Action, per spec. `Dockerfile` (untested —
  no Docker available in this environment; standard `pip install .`
  pattern against the existing `pyproject.toml`/`src` layout).
  `.pre-commit-config.yaml` (ruff, ruff-format, mypy, standard hygiene
  hooks) — written but not dry-run in this environment.
- Full README rewrite: opens with the spec's exact problem statement,
  60-second quickstart, real captured `mcplint scan` output against
  `examples/bad_server`, architecture diagram, full rule catalogue table,
  ambiguity-engine evidence model explained, benchmark/compare/fix/CI/
  plugin guides, a limitations section cross-referencing this file, a
  roadmap, and a comparison section (MCP Inspector, schema-diff tools,
  generic LLM eval frameworks) that explicitly avoids superiority claims.
- 168 tests passing, 94% coverage. Ruff/MyPy clean.

## Incomplete
- HTTP transport for MCP servers (timeout, response-size limit, header
  redaction, no auto-redirects per spec's security constraints) — not yet
  implemented; `inspect`/`snapshot`/`scan`/`benchmark`/`compare` are all
  stdio-only.
- Optional sentence-transformer embeddings for the ambiguity engine (the
  `semantic` extra) — interface allows for it (score is a weighted blend)
  but no embedding backend is wired in yet; deterministic token/name/schema
  similarity is the only mode. Not required for v1 per spec ("optional").
- Real OpenAI benchmark provider (typed stub exists, raises `NotImplementedError`).
- LLM-assisted rewriting for `mcplint fix` (`--llm-provider` flag exists and
  is validated, but always rejected — no LLM call path implemented).
- `--verbose` global option is not implemented.
- Dockerfile and `.pre-commit-config.yaml` are written to standard patterns
  but not executed/dry-run in this environment (no Docker, and running
  `pre-commit run --all-files` with `ruff-format` would reformat the whole
  tree in ways not reviewed here) — worth doing before a real release.

## Known limitations
- `inspect`/`snapshot`/`scan`/`benchmark`/`compare` only support stdio transport.
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
- Verified the real `anthropic` SDK (0.120.0) API surface before writing
  `AnthropicProvider`, same discipline as Phase 1's `mcp` SDK verification:
  checked `messages.create` signature, `ToolParam` fields, `Message`/
  `ToolUseBlock`/`Usage` fields directly against the installed package.
- `anthropic` added to the `dev` extra (not just the `anthropic` extra) so
  CI exercises `AnthropicProvider`'s tests by default; those tests still use
  `pytest.importorskip` so the suite degrades gracefully without it.
- `compare`'s benchmark re-run uses each snapshot's own `tools` list rather
  than requiring a live `--server` — matches the spec ("Compare two
  snapshots and optionally run benchmark datasets against each") and means
  `compare` never spawns a process.
- `fix/suggest.py` re-derives constraint values (enum/min/max) from
  `tool.parameters` via the finding's `json_path` rather than parsing
  `Finding.evidence` text, so a rule's message wording can change without
  breaking the fixer.
- Score categories partition findings by rule ID (ambiguity/schema/safety
  rule-ID sets checked first, generic error/warning bucket last) rather
  than by severity alone, so e.g. `destructive-tool-without-warning`
  (severity error) is counted once under `safety_clarity`, not also under
  the generic `critical_error` bucket.
- HTML report recomputes ambiguity pairs live from the snapshot at render
  time (via `compute_ambiguity`) instead of reading them off `LintReport`,
  since ambiguity results aren't a stored artifact (see Phase 3 decision
  above) — keeps the HTML reporter as the one place that needs both the
  snapshot and the report.
- `mcplint scan`'s SARIF/HTML formats reuse the same `RuleRegistry.with_builtin_rules()`
  default (unconfigured) registry for the SARIF rule catalogue, independent
  of whatever config-derived registry produced the findings — the catalogue
  describes what rules exist, not what ran.

## Next task
The project now implements every command, model, rule, and reporter listed
in the spec's required scope, with the explicitly-deferred exceptions
above (HTTP transport, semantic-extra embeddings, OpenAI provider,
LLM-assisted fix). Suggested next steps for a real release: dry-run
`.pre-commit-config.yaml` and the `Dockerfile` build in an environment that
has Docker/pre-commit available, do a real end-to-end SARIF-schema
validation (network access to the official schema), and decide whether
HTTP transport or the `semantic` embedding extra is the higher-value next
increment.
