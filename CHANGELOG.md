# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-26

Initial public release.

### Added

- Deterministic linter with 15 built-in rules covering missing/vague/misleading
  tool descriptions, undocumented parameters and constraints, schema/description
  conflicts, destructive-action warnings, and cross-tool ambiguity. No LLM key
  required.
- Cross-tool ambiguity engine (`compute_ambiguity`): a name/description/parameter
  similarity score with explainable evidence for every flagged pair, not just a
  number.
- Explainable 0-100 score with documented, capped-per-category deductions.
- `mcplint.yaml` configuration: severity overrides, thresholds, per-tool rule
  ignores, benchmark defaults.
- Benchmark suite: a YAML dataset format, a provider abstraction (fake, Anthropic,
  OpenAI stub), and a fully deterministic scorer (exact tool-selection accuracy,
  argument validity, latency, cost, stability). No LLM judge.
- `compare` command: diffs two snapshots' tool contracts, findings, and ambiguity
  scores, and optionally re-runs a benchmark against both to report accuracy/
  latency/cost deltas with a CI threshold.
- `fix` command: deterministic, schema-derived rewrite suggestions. Never
  modifies source files; produces a Markdown patch report only.
- Reporters: Rich terminal, JSON, SARIF 2.1.0, and a standalone self-contained
  HTML report.
- CLI commands: `inspect`, `snapshot`, `scan`, `rules`, `benchmark`, `compare`,
  `fix`.
- Example MCP servers (`good_server`, `bad_server`, `ambiguous_customer_server`)
  and a benchmark dataset demonstrating tool-selection confusion.
- Packaging: MIT license, CI and release GitHub Actions workflows, PyPI Trusted
  Publishing, Dockerfile, pre-commit configuration.

[Unreleased]: https://github.com/akashkokare2910/mcplint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/akashkokare2910/mcplint/releases/tag/v0.1.0
