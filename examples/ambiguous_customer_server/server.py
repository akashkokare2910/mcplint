"""An MCP server whose four customer tools are intentionally hard for an
agent to tell apart. Used as the target of the customer-tools benchmark
dataset (Phase 4) and to demonstrate the ambiguity engine.

Run directly: python examples/ambiguous_customer_server/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("ambiguous-customer-server")


@mcp.tool(
    description="Get a customer record by identifier.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def get_customer(customer_id: str) -> dict[str, str]:
    return {"customer_id": customer_id}


@mcp.tool(
    description="Search a customer record by identifier.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def search_customers(customer_id: str) -> list[dict[str, str]]:
    return [{"customer_id": customer_id}]


@mcp.tool(description="Update a customer.")
def update_customer(customer_id: str, fields: dict) -> dict[str, str]:
    return {"customer_id": customer_id}


@mcp.tool(
    description="Delete a customer.",
    annotations=ToolAnnotations(destructiveHint=True),
)
def delete_customer(customer_id: str) -> bool:
    return True


if __name__ == "__main__":
    mcp.run()
