---
name: mcplint
description: Lint an MCP server's tool definitions for the description and schema problems that make agents pick the wrong tool or build invalid arguments, then fix them and verify the fix. Use when building, reviewing, or debugging an MCP server, when an agent keeps choosing the wrong tool, before publishing an MCP server, or when asked to check tool descriptions or tool contracts.
---

# mcplint: check MCP tool contracts before agents trip on them

A tool can pass JSON Schema validation and still mislead a model: two tools
whose descriptions overlap, a destructive action with no warning, a required
parameter whose constraints are never stated. `mcplint` connects to the
server, reads its tool list, and reports these problems with evidence and a
suggested remediation.

## Setup

```bash
pip install mcplint-cli
mcplint --version
```

No API key is needed for linting. The server is launched over stdio from the
command line you give `--server`, exactly as an MCP client would launch it.

## Workflow

Follow these steps in order. Do not edit tool descriptions before step 2.

1. **Find how the server starts.** Look in the project's MCP client config,
   README, or entry point for the launch command, for example
   `python server.py`, `uv run my-server`, or `node dist/index.js`.

2. **Record a baseline.**

   ```bash
   mcplint snapshot --server "<launch command>" --output mcplint-before.json
   mcplint scan --snapshot mcplint-before.json --format json --output mcplint-report.json
   ```

   The scan prints a 0-100 score and one row per finding: rule ID, severity,
   tool, message. The JSON report adds each finding's evidence, remediation
   and confidence. Exit code 1 means at least one error-severity finding.

3. **Get concrete rewrites.**

   ```bash
   mcplint fix --snapshot mcplint-before.json --output mcplint-fixes.md
   ```

   This writes a Markdown report of suggested description and schema
   changes. It never edits source files.

4. **Apply fixes in the server's source**, highest severity first:
   - `error`: fix all of them. These are missing descriptions, destructive
     tools with no warning, and annotations that contradict behaviour.
   - `warning`: fix unless the finding is clearly wrong for this server.
   - `info`: fix when cheap. These are heuristics; check each finding's
     confidence score before acting on it.

   Keep each description true to what the code does. Never add a claim
   about behaviour you have not confirmed in the implementation.

5. **Verify.**

   ```bash
   mcplint snapshot --server "<launch command>" --output mcplint-after.json
   mcplint compare --baseline mcplint-before.json --candidate mcplint-after.json
   mcplint scan --server "<launch command>"
   ```

   Report the score before and after, the findings fixed, and any finding
   deliberately left in place with the reason.

## Reading findings

- `ambiguous-tool-overlap` and `missing-tool-distinction`: two tools a model
  could confuse. Fix by saying in each description when to use *this* tool
  rather than the other one, not by making both descriptions longer.
- `destructive-tool-without-warning`, `state-changing-tool-marked-read-only`,
  `tool-name-action-conflict`: safety. The description and MCP annotations
  must say the tool changes or deletes state.
- `undocumented-required-constraint`, `schema-description-type-conflict`:
  the prose and the schema disagree or the prose omits a rule the schema
  enforces. Make the prose match the schema.

`mcplint rules` lists every rule with its default severity.

## Gating CI

```bash
mcplint scan --server "<launch command>" --format sarif --output results.sarif --fail-on error
```

`--fail-on error` (the default) exits 1 on any error-severity finding.
`--fail-on never` always exits 0, for report-only jobs. Scan formats:
`terminal`, `json`, `sarif`, `html`. Severities can be overridden or rules
ignored in `mcplint.yaml`.

## Going further

To check that tool descriptions actually change model behaviour, use
`mcplint benchmark` (tool-selection accuracy on a dataset) and the
`mcplint contract` commands (`validate`, `generate-benchmark`, `mutate`).
Benchmarks against a real model need that provider's API key; ask the user
before running one, because it costs money. See the project README:
https://github.com/akashkokare2910/mcplint

## Limits

mcplint reads tool definitions only. It does not run the tools, so it
cannot detect a description that is well written but wrong about what the
code does. That check is yours, in step 4.
