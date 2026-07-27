# MCPLint

[![PyPI](https://img.shields.io/pypi/v/mcplint-cli.svg)](https://pypi.org/project/mcplint-cli/)
[![CI](https://github.com/akashkokare2910/mcplint/actions/workflows/ci.yml/badge.svg)](https://github.com/akashkokare2910/mcplint/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**Your MCP server can pass schema validation while the model still chooses the wrong tool.**

MCPLint connects to a [Model Context Protocol](https://modelcontextprotocol.io)
server, retrieves its tool definitions, and detects the description and schema
problems that cause LLM agents to select the wrong tool or construct invalid
arguments. It suggests fixes and benchmarks tool-selection behavior before and
after changes.

A tool can have a perfectly valid `inputSchema` and still be a trap for an
agent: two tools whose descriptions overlap, a destructive action with no
warning, a required parameter whose constraints are never mentioned in prose.
JSON Schema validation does not catch any of that. MCPLint does.

## Quick start

```bash
pip install mcplint-cli

mcplint scan --server "python my_server.py"
```

No config file and no API key are required for the core linter. `mcplint scan`
connects over stdio, retrieves the tool list, runs 15 deterministic rules, and
prints a scored report with a non-zero exit code when something is wrong, the
same way `eslint` gates a pull request.

## Example output

```
$ mcplint scan --server "python examples/bad_server/server.py"

bad-customer-server: 34 finding(s) (6 error, 13 warning, 15 info), score 32/100
  -8.0  1 critical/error finding(s) x 8 pts (capped at 40)
  -20.0 18 warning/info finding(s) x 2 pts (capped at 20)
  -10.0 2 ambiguity finding(s) x 5 pts (capped at 15)
  -15.0 9 schema-completeness finding(s) x 3 pts (capped at 15)
  -15.0 4 safety-clarity finding(s) x 5 pts (capped at 15)

Rule                            Severity  Tool           Message
missing-tool-description        error     ping           Tool 'ping' has no description.
description-repeats-name        warning   get_status     Description only restates its name.
vague-tool-description          warning   get_status     Description is very short (2 words).
missing-parameter-description   warning   fetch_record   Parameter 'record_id' has no description.
...                                                       (30 more)
```

Every finding includes a rule ID, severity, evidence, remediation text, and a
confidence score. Heuristic findings are never presented as certain: compare
`undocumented-error-behaviour` at confidence 0.5 to `missing-tool-description`
at 1.0.

## Architecture

```
mcp_client/   Stdio connection to the MCP server, producing an MCPServerSnapshot.
core/         Rule ABC, RuleRegistry, and the lint_snapshot() engine.
                core/rules/  15 built-in rules and the cross-tool ambiguity engine.
                core/score.py  The explainable 0-100 score.
config/       mcplint.yaml loading (severity overrides, thresholds, ignores).
benchmark/    Dataset format, ToolCallingProvider protocol, scorer, runner.
                providers/  fake (tests), anthropic, openai (stub).
compare/      Pure diff functions between two snapshots, reports, or benchmarks.
fix/          Deterministic rewrite suggestions derived from schema and annotations.
models/       Every persisted artifact as a typed Pydantic model.
reporters/    Terminal (Rich), JSON, SARIF 2.1.0, standalone HTML, Markdown.
cli/          Typer commands, thin wrappers around the modules above.
```

The deterministic linter (`core/`) never imports an LLM client. Only
`benchmark/providers/anthropic_provider.py` (and the `openai` stub) call a
model API, and only when `--provider anthropic` is passed explicitly.

## Rule catalogue

Run `mcplint rules` for the live list (ID, title, default severity, tags). All
15 rules are deterministic and require no LLM key.

| Rule | Default severity | What it catches |
|---|---|---|
| `missing-tool-description` | error | No description at all |
| `description-repeats-name` | warning | Description just restates the tool name |
| `vague-tool-description` | warning | Description under 4 words |
| `missing-parameter-description` | warning | A parameter with no description |
| `missing-return-semantics` | warning | No outputSchema and no return-related wording |
| `undocumented-error-behaviour` | info | Description never mentions failure or error conditions |
| `undocumented-required-constraint` | warning | Required parameter's enum, min, or max not mentioned in prose |
| `schema-description-type-conflict` | error | Description implies a type the schema does not declare |
| `tool-name-action-conflict` | error | Name reads read-only but is annotated destructive |
| `destructive-tool-without-warning` | error | Destructive annotation with no warning in the description |
| `state-changing-tool-marked-read-only` | error | Name reads as a mutation but `readOnlyHint` is true |
| `ambiguous-tool-overlap` | warning | Two tools score above the ambiguity threshold |
| `missing-tool-distinction` | info | Ambiguous pair never states when to use which tool |
| `excessive-description-length` | info | Description exceeds the configured character limit |
| `undefined-domain-term` | info | An unexplained acronym or jargon term |

See `examples/bad_server/server.py` for one deliberate trigger per rule, and
`examples/good_server/server.py` for a server that scores zero findings
against all 15.

### The ambiguity engine

`ambiguous-tool-overlap` and `missing-tool-distinction` are backed by
`core/rules/ambiguity.py::compute_ambiguity`, a pairwise score from 0 to 1
built from:

- name token similarity (25%)
- description token similarity, stopword filtered (45%)
- parameter name overlap (30%)

Every flagged pair carries evidence, not just a number: shared verbs, shared
entities, overlapping parameters, and three explicit booleans for whether the
pair states an exact-vs-search, one-vs-many, or read-vs-write distinction.
This is deliberately explainable rather than an opaque embedding score. See
`examples/ambiguous_customer_server` for a worked example (`get_customer` vs
`search_customers`).

An optional `semantic` extra (`sentence-transformers`) is planned as an
additional signal on top of this token-based score, not a replacement. It is
not yet wired in; see Limitations.

## Configuration

`mcplint.yaml` is auto-loaded from the current directory (`--config` to
override the path):

```yaml
severity:
  missing-tool-description: error
  excessive-description-length: info

thresholds:
  ambiguity: 0.78
  max_description_characters: 800

ignore:
  - tool: internal_debug
    rules:
      - missing-return-semantics

benchmark:
  provider: anthropic
  model: claude-sonnet
  runs: 3
```

Invalid configuration fails with a specific, actionable field-level error
rather than a generic traceback.

## Benchmark guide

Deterministic linting catches contract problems. The benchmark measures
whether a real model actually picks the right tool.

```yaml
# evals.yaml
name: customer-tools
version: "1"
cases:
  - id: exact-customer-lookup
    prompt: Retrieve customer CUST-1042.
    expected:
      tool: get_customer
      arguments:
        customer_id: CUST-1042
      forbidden_tools:
        - delete_customer
```

```bash
# No API key needed: dry-run against a live server
mcplint benchmark evals.yaml --server "python my_server.py" --provider fake

# Real model
export ANTHROPIC_API_KEY=sk-...
mcplint benchmark evals.yaml --server "python my_server.py" \
  --provider anthropic --model claude-sonnet-5 --runs 3
```

Metrics are entirely deterministic: exact tool-selection accuracy,
valid-argument rate (checked against the tool's real JSON Schema),
required-argument accuracy, forbidden-tool invocation rate, no-tool rate,
mean and P95 latency, estimated cost, and per-case stability across repeated
trials. No LLM judge is used anywhere; every pass or fail is a literal
comparison.

`examples/ambiguous_customer_server/customer-tools.evals.yaml` is a worked
example of get/search/update/delete-customer confusion.

## Compare and fix

```bash
mcplint snapshot --server "python my_server.py" --output before.json
# edit your tool descriptions
mcplint snapshot --server "python my_server.py" --output after.json

mcplint compare --baseline before.json --candidate after.json \
  --dataset evals.yaml --provider fake --min-accuracy-delta -0.02
```

`compare` diffs tool contracts (added and removed tools, schema and
description changes), findings (new versus resolved), and ambiguity scores
between two snapshots. With `--dataset`, it also re-runs the benchmark
against both tool lists and reports the accuracy, latency, and cost deltas.
It exits 1 if `--min-accuracy-delta` is not met, so it gates a pull request.

```bash
mcplint fix --snapshot before.json --output fix-report.md
```

`fix` proposes rewrites for whatever it can derive mechanically from the
JSON Schema and annotations (output shape, enum values, numeric bounds,
destructive warnings, tool-distinction placeholders). It never writes to
your source files, only a Markdown patch report you review by hand. Purely
semantic issues, such as a vague description or one that just restates the
name, get an honest low-confidence placeholder rather than fabricated prose,
since the deterministic engine has no LLM to invent real content.

## CI guide

```bash
mcplint scan --server "python my_server.py" --format sarif --output results.sarif --fail-on error
```

`--fail-on error` (the default) exits 1 on any error-severity finding and 0
otherwise. `--fail-on never` always exits 0, useful for a report-only job.
See `.github/workflows/example-scan-mcp-server.yml` for a complete example
workflow: install MCPLint, invoke your server, scan, upload SARIF to GitHub
code scanning, and fail on error. No custom JavaScript GitHub Action is
required.

## Plugin guide

Third-party rules register through a Python entry point; no changes to this
repository are needed:

```toml
# your_package's pyproject.toml
[project.entry-points."mcplint.rules"]
my-custom-rule = "your_package.rules:MyCustomRule"
```

```python
from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, Severity

class MyCustomRule(Rule):
    id = "my-custom-rule"
    title = "My custom rule"
    description = "Explain what this catches."
    default_severity = Severity.WARNING

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        ...
```

`RuleRegistry().load_entry_point_plugins()` discovers everything registered
under the `mcplint.rules` group and merges it with the 15 built-in rules.

## Limitations

- Stdio transport only. HTTP MCP servers are not supported yet (planned:
  connection timeout, response-size limit, header redaction; see
  `SECURITY.md`).
- The ambiguity engine's token overlap does no stemming or lemmatization, so
  "customer" versus "customers" reduces measured similarity between
  genuinely related tools. This is a real, observed trade-off, not a bug.
- `undefined-domain-term`'s acronym heuristic is intentionally conservative
  (info severity, confidence 0.4) and will both under- and over-flag.
- The OpenAI benchmark provider is a typed stub, not a working
  implementation.
- `fix --llm-provider` is accepted as a flag but always rejected; no
  LLM-assisted rewriting path exists yet.
- The overall score is a documented, capped-per-category heuristic, not a
  scientifically validated or universal quality metric. It exists so a
  regression in one category cannot silently zero out the total.

## Roadmap

- HTTP MCP server transport with the security constraints above
- Sentence-transformer embeddings as an additional ambiguity signal
- OpenAI benchmark provider
- LLM-assisted rewriting for `mcplint fix`
- A JavaScript GitHub Action wrapper, if the composite-workflow approach
  proves insufficient for real users

## Comparison

- **[MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)**
  is an interactive debugger for poking at a running MCP server by hand.
  MCPLint is a non-interactive, deterministic linter meant to run unattended
  in CI. The two are complementary, not competing.
- **Generic JSON Schema diff and validation tools** verify that a schema is
  well-formed and check argument values against it. They cannot tell you
  that two tools are semantically confusable, that a destructive tool lacks
  a warning, or that a required constraint is undocumented in prose. Those
  require understanding the description, not just the schema.
- **Generic LLM evaluation frameworks** (promptfoo, LangSmith evals, and
  similar) can benchmark tool-selection accuracy, and MCPLint's `benchmark`
  command covers similar ground for MCP tools specifically. MCPLint's
  distinct contribution is the deterministic linter, which runs without any
  model key, combined with static analysis and benchmark deltas in one
  `compare` command.

This is not a claim that MCPLint is better than any of the above at what
they are built for. It is scoped specifically to the MCP tool description,
schema, and ambiguity problem.

## Development

```bash
git clone https://github.com/akashkokare2910/mcplint.git
cd mcplint
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ruff check src tests examples
ruff format --check src tests examples
mypy src
pytest --cov=mcplint --cov-report=term-missing
```

See `CONTRIBUTING.md` for the rule and provider extension guides, and
`CHANGELOG.md` for the release history.

## License

MIT. See `LICENSE`.
