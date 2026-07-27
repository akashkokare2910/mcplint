# Contributing to MCPLint

Thanks for considering a contribution. MCPLint is a young project, and both
its architecture and this guide are likely to evolve.

## Development setup

```bash
git clone https://github.com/akashkokare2910/mcplint.git
cd mcplint
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`dev` includes `anthropic` so the Anthropic provider's test suite runs by
default. If you only want the deterministic linter, `pip install -e .` is
enough. No extras are required for `inspect`, `snapshot`, `scan`, `rules`,
or `fix`.

## Before opening a PR

Run the same gate CI runs:

```bash
ruff check src tests examples
ruff format --check src tests examples
mypy src
pytest --cov=mcplint --cov-report=term-missing
```

All checks must pass. New code should come with tests. See
`tests/unit/core/rules/` for the pattern most rules follow: a flag case and
a pass case per behavior, using hand-built `ToolContract`/`RuleContext`
fixtures, no live MCP server needed.

## Adding a built-in rule

1. Subclass `mcplint.core.rules.base.Rule` in the appropriate module under
   `src/mcplint/core/rules/` (`description_rules.py`, `schema_rules.py`,
   `safety_rules.py`, `completeness_rules.py`, or a new file for a new
   category).
2. Set `id`, `title`, `description`, `default_severity`, and optionally
   `tags` as class attributes. Implement `check(self, tool, context) ->
   list[Finding]`.
3. Register it in `BUILTIN_RULES` in `core/rules/builtin.py`.
4. Add unit tests: at least one case that triggers the finding and one that
   does not.
5. If it is meant to fire on `examples/bad_server`, add a tool there and
   confirm `tests/integration/test_bad_server.py` still passes. That test
   asserts every built-in rule ID fires at least once against that server.

Third-party rules do not need to touch this repository at all. See the
plugin guide in the README for the `mcplint.rules` entry-point mechanism.

## Adding a benchmark provider

Implement the `ToolCallingProvider` protocol (`benchmark/providers/base.py`):
a `name`/`model` pair and an async `run(prompt, tools) -> ProviderResult`.
See `benchmark/providers/anthropic_provider.py` for a real example and
`benchmark/providers/fake.py` for a test-only one. Wire it into
`benchmark/providers/factory.py::create_provider`.

## Commit and PR conventions

- Keep commits scoped to one logical change. The existing history (`git log
  --oneline`) is the style to match.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.

## Reporting bugs and requesting features

Use the GitHub issue templates. For security issues, see `SECURITY.md`
instead of opening a public issue.
