# MCPLint

**Your MCP server can pass schema validation while the model still chooses the wrong tool.**

MCPLint is an "ESLint for MCP tool contracts." It connects to a [Model
Context Protocol](https://modelcontextprotocol.io) server, retrieves its
tool definitions, detects description and schema problems that cause LLM
agents to select the wrong tool or construct invalid arguments, suggests
improvements, and benchmarks tool-selection behaviour before and after
changes.

A tool can have a perfectly valid `inputSchema` and still be a trap for an
agent: two tools whose descriptions overlap, a destructive action with no
warning, a required parameter whose constraints are never mentioned in
prose. JSON Schema validation doesn't catch any of that. MCPLint does.

---

## 60-second quick start

```bash
pip install mcplint

# Point it at any MCP server's launch command
mcplint scan --server "python my_server.py"
```

That's it — no config file, no API key, no LLM required for the core
linter. `mcplint scan` connects over stdio, retrieves the tool list, runs
15 deterministic rules, and prints a scored report with a non-zero exit
code when something's wrong (so it gates a PR the same way `eslint` does).

## Example output

```
$ mcplint scan --server "python examples/bad_server/server.py"

bad-customer-server — 34 finding(s) (6 error, 13 warning, 15 info) — score: 32/100
  -8.0  1 critical/error finding(s) x 8 pts (capped at 40)
  -20.0 18 warning/info finding(s) x 2 pts (capped at 20)
  -10.0 2 ambiguity finding(s) x 5 pts (capped at 15)
  -15.0 9 schema-completeness finding(s) x 3 pts (capped at 15)
  -15.0 4 safety-clarity finding(s) x 5 pts (capped at 15)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Rule                            ┃ Severity ┃ Tool          ┃ Message                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ missing-tool-description        │ error    │ ping          │ Tool 'ping' has no description.           │
│ description-repeats-name        │ warning  │ get_status    │ Description only restates its name.       │
│ vague-tool-description          │ warning  │ get_status    │ Description is very short (2 words).      │
│ missing-parameter-description   │ warning  │ fetch_record  │ Parameter 'record_id' has no description. │
│ ...                             │          │               │ (30 more)                                  │
└──────────────────────────────────┴──────────┴───────────────┴────────────────────────────────────────────┘
```

Every finding carries a rule ID, severity, evidence, remediation text, and
a confidence score — heuristic findings are never presented as certain (see
`undocumented-error-behaviour` above at confidence 0.5 vs.
`missing-tool-description` at 1.0).

## Architecture

```
mcp_client/   stdio connection to the MCP server -> MCPServerSnapshot
                (untrusted-process boundary; canonicalization for stable JSON)
core/         Rule ABC + RuleRegistry + lint_snapshot() engine
                core/rules/  15 built-in rules + the cross-tool ambiguity engine
                core/score.py  explainable 0-100 score
config/       mcplint.yaml loading (severity overrides, thresholds, ignores)
benchmark/    dataset format, ToolCallingProvider protocol, scorer, runner
                providers/  fake (tests), anthropic (real), openai (stub)
compare/      pure diff functions between two snapshots/lint reports/benchmarks
fix/          deterministic rewrite suggestions from JSON Schema + annotations
models/       every persisted artifact as a typed Pydantic model
reporters/    terminal (Rich), JSON, SARIF 2.1.0, standalone HTML, Markdown
cli/          Typer commands — thin wrappers around the modules above
```

The deterministic linter (`core/`) never imports an LLM client. Only
`benchmark/providers/anthropic_provider.py` (and the `openai` stub) touch a
model API, and only when you explicitly ask for `--provider anthropic`.

## Rule catalogue

Run `mcplint rules` for the live list (id, title, default severity, tags).
All 15 are deterministic — no LLM key required.

| Rule | Default severity | What it catches |
|---|---|---|
| `missing-tool-description` | error | No description at all |
| `description-repeats-name` | warning | Description just restates the tool name |
| `vague-tool-description` | warning | Description under 4 words |
| `missing-parameter-description` | warning | A parameter with no description |
| `missing-return-semantics` | warning | No outputSchema and no return-related wording |
| `undocumented-error-behaviour` | info | Description never mentions failure/error conditions |
| `undocumented-required-constraint` | warning | Required param's enum/min/max not mentioned in prose |
| `schema-description-type-conflict` | error | Description implies a type the schema doesn't declare |
| `tool-name-action-conflict` | error | Name reads read-only but is annotated destructive |
| `destructive-tool-without-warning` | error | Destructive annotation, no warning in the description |
| `state-changing-tool-marked-read-only` | error | Name reads as a mutation but `readOnlyHint` is true |
| `ambiguous-tool-overlap` | warning | Two tools score above the ambiguity threshold |
| `missing-tool-distinction` | info | Ambiguous pair never states when to use which |
| `excessive-description-length` | info | Description over the configured character limit |
| `undefined-domain-term` | info | An unexplained acronym/jargon term |

See `examples/bad_server/server.py` for one deliberate trigger per rule, and
`examples/good_server/server.py` for a server that scores 0 findings against
all 15.

### The ambiguity engine

`ambiguous-tool-overlap` and `missing-tool-distinction` are backed by
`core/rules/ambiguity.py::compute_ambiguity`, a pairwise score (0-1) built
from:

- name token similarity (25%)
- description token similarity, stopword-filtered (45%)
- parameter-name overlap (30%)

Every flagged pair carries **evidence**, not just a number: shared verbs,
shared entities, overlapping parameters, and three explicit booleans for
whether the pair states an exact-vs-search, one-vs-many, or read-vs-write
distinction. This is deliberately explainable rather than an opaque
embedding score — see `examples/ambiguous_customer_server` for a worked
example (`get_customer` vs `search_customers`).

An optional `semantic` extra (`sentence-transformers`) is planned as an
additional signal on top of this token-based score, not a replacement —
not yet wired in (see Limitations).

## Configuration

`mcplint.yaml`, auto-loaded from the current directory (`--config` to
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

Invalid config fails with a specific, actionable field-level error rather
than a generic traceback.

## Benchmark guide

Deterministic linting catches contract problems; the benchmark measures
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
# No API key needed — dry-run against a live server
mcplint benchmark evals.yaml --server "python my_server.py" --provider fake

# Real model
export ANTHROPIC_API_KEY=sk-...
mcplint benchmark evals.yaml --server "python my_server.py" \
  --provider anthropic --model claude-sonnet-5 --runs 3
```

Metrics are entirely deterministic: exact tool-selection accuracy,
valid-argument rate (checked against the tool's real JSON Schema),
required-argument accuracy, forbidden-tool invocation rate, no-tool rate,
mean/P95 latency, estimated cost, and per-case stability across repeated
trials. **No LLM judge is used anywhere** — every pass/fail is a literal
comparison.

`examples/ambiguous_customer_server/customer-tools.evals.yaml` is a worked
example showing get/search/update/delete-customer confusion.

## Compare & fix

```bash
mcplint snapshot --server "python my_server.py" --output before.json
# ... edit your tool descriptions ...
mcplint snapshot --server "python my_server.py" --output after.json

mcplint compare --baseline before.json --candidate after.json \
  --dataset evals.yaml --provider fake --min-accuracy-delta -0.02
```

`compare` diffs tool contracts (added/removed tools, schema/description
changes), findings (new vs. resolved), and ambiguity scores between two
snapshots, and — if you pass `--dataset` — re-runs the benchmark against
both tool lists and reports the accuracy/latency/cost deltas. Exits 1 if
`--min-accuracy-delta` isn't met, so it gates a PR.

```bash
mcplint fix --snapshot before.json --output fix-report.md
```

`fix` proposes rewrites for whatever it can derive mechanically from the
JSON Schema and annotations (output shape, enum values, numeric bounds,
destructive warnings, tool-distinction placeholders). It **never writes to
your source files** — only a Markdown patch report you review by hand.
Purely semantic issues (a vague description, one that just restates the
name) get an honest low-confidence TODO placeholder, since the
deterministic engine has no LLM to invent real prose.

## CI guide

```bash
mcplint scan --server "python my_server.py" --format sarif --output results.sarif --fail-on error
```

`--fail-on error` (the default) exits 1 on any error-severity finding, 0
otherwise; `--fail-on never` always exits 0 (useful for a report-only job).
See `.github/workflows/example-scan-mcp-server.yml` for a complete,
documented example workflow: install MCPLint, invoke your server, scan,
upload SARIF to GitHub code scanning, fail on error. No custom JavaScript
GitHub Action is required.

## Plugin guide

Third-party rules register via a Python entry point — no changes to this
repo needed:

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
under the `mcplint.rules` group and merges it with the 15 built-ins.

## Limitations

- Stdio transport only — HTTP MCP servers aren't supported yet (planned:
  connection timeout, response-size limit, header redaction; see
  `SECURITY.md`).
- The ambiguity engine's token overlap does no stemming/lemmatization, so
  "customer" vs. "customers" reduces measured similarity between genuinely
  related tools. Real, observed trade-off — not a bug — see
  `IMPLEMENTATION_STATUS.md`.
- `undefined-domain-term`'s acronym heuristic is intentionally conservative
  (info severity, confidence 0.4) and will both under- and over-flag.
- The OpenAI benchmark provider is a typed stub, not a working
  implementation, per the spec's "don't let it block Anthropic" guidance.
- `fix --llm-provider` is accepted as a flag but always rejected — no
  LLM-assisted rewriting path exists yet.
- The overall score is a documented, capped-per-category heuristic, **not**
  a scientifically validated or universal quality metric. It exists so a
  regression in one category can't silently zero out the total.

Full detail, including every deferred item and the reasoning behind it, is
in `IMPLEMENTATION_STATUS.md`.

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
  MCPLint is a non-interactive, deterministic linter meant to run
  unattended in CI — the two are complementary, not competing.
- **Generic JSON Schema diff/validation tools** verify that a schema is
  well-formed and check argument values against it. They cannot tell you
  that two tools are semantically confusable, that a destructive tool lacks
  a warning, or that a required constraint isn't documented in prose —
  those require understanding the *description*, not just the schema.
- **Generic LLM evaluation frameworks** (promptfoo, LangSmith evals, etc.)
  can benchmark tool-selection accuracy, and MCPLint's `benchmark` command
  covers similar ground for MCP tools specifically. MCPLint's distinct
  contribution is the deterministic linter (rules 1-15) that runs without
  any model key, plus tying static analysis and benchmark deltas together
  in one `compare` command.

We don't claim MCPLint is strictly better than any of the above at what
they're actually built for — it's scoped specifically to the MCP tool
description/schema/ambiguity problem.

## Development

```bash
git clone https://github.com/mcplint/mcplint.git && cd mcplint
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check src tests examples
mypy src
pytest --cov=mcplint --cov-report=term-missing
```

See `CONTRIBUTING.md` for the rule/provider extension guides,
`IMPLEMENTATION_STATUS.md` for exactly what's done vs. deferred, and
`CHANGELOG.md` for the phase-by-phase build history.

## License

MIT — see `LICENSE`.
