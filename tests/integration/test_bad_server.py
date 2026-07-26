import sys
from pathlib import Path

import pytest

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.mcp_client.session import collect_stdio_snapshot

EXAMPLES = Path(__file__).parent.parent.parent / "examples"

ALL_BUILTIN_RULE_IDS = {
    "missing-tool-description",
    "description-repeats-name",
    "vague-tool-description",
    "missing-parameter-description",
    "missing-return-semantics",
    "undocumented-error-behaviour",
    "undocumented-required-constraint",
    "schema-description-type-conflict",
    "tool-name-action-conflict",
    "destructive-tool-without-warning",
    "state-changing-tool-marked-read-only",
    "ambiguous-tool-overlap",
    "missing-tool-distinction",
    "excessive-description-length",
    "undefined-domain-term",
}


@pytest.mark.asyncio
async def test_bad_server_triggers_every_builtin_rule() -> None:
    server_path = EXAMPLES / "bad_server" / "server.py"
    snapshot = await collect_stdio_snapshot(sys.executable, [str(server_path)])
    report = lint_snapshot(snapshot, RuleRegistry.with_builtin_rules())
    triggered = {finding.rule_id for finding in report.findings}
    missing = ALL_BUILTIN_RULE_IDS - triggered
    assert not missing, f"bad_server did not trigger: {sorted(missing)}"
