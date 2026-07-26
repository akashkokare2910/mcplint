import sys
from pathlib import Path

import pytest

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.mcp_client.session import collect_stdio_snapshot

EXAMPLES = Path(__file__).parent.parent.parent / "examples"


@pytest.mark.asyncio
async def test_ambiguous_customer_server_flags_get_vs_search_overlap() -> None:
    server_path = EXAMPLES / "ambiguous_customer_server" / "server.py"
    snapshot = await collect_stdio_snapshot(sys.executable, [str(server_path)])
    assert {t.name for t in snapshot.tools} == {
        "get_customer",
        "search_customers",
        "update_customer",
        "delete_customer",
    }
    report = lint_snapshot(snapshot, RuleRegistry.with_builtin_rules())
    overlap_findings = [f for f in report.findings if f.rule_id == "ambiguous-tool-overlap"]
    assert any(
        f.location.tool_name == "get_customer" and "search_customers" in f.message
        for f in overlap_findings
    )
