import sys
from pathlib import Path

import pytest

from mcplint.mcp_client.session import collect_stdio_snapshot

EXAMPLES = Path(__file__).parent.parent.parent / "examples"


@pytest.mark.asyncio
async def test_collect_snapshot_from_good_server() -> None:
    server_path = EXAMPLES / "good_server" / "server.py"
    snapshot = await collect_stdio_snapshot(sys.executable, [str(server_path)])
    assert snapshot.server_name == "good-customer-server"
    tool_names = {tool.name for tool in snapshot.tools}
    assert tool_names == {"get_customer", "search_customers"}
    get_customer = snapshot.get_tool("get_customer")
    assert get_customer is not None
    assert get_customer.description is not None
    assert "customer_id" in get_customer.parameter_names()
