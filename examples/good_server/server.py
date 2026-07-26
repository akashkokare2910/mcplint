"""A well-documented example MCP server used by MCPLint's own tests.

Run directly: python examples/good_server/server.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

mcp = FastMCP("good-customer-server")

_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)


@mcp.tool(
    description=(
        "Retrieve a single customer record by its exact customer identifier. "
        "Returns the customer's profile fields as JSON. Raises a not-found "
        "error if the identifier does not exist. Use search_customers instead "
        "when you don't already have the exact identifier."
    ),
    annotations=_READ_ONLY,
)
def get_customer(
    customer_id: Annotated[str, Field(description="The exact customer identifier, e.g. 1042.")],
) -> dict[str, str]:
    return {"customer_id": customer_id, "name": "Example Customer"}


@mcp.tool(
    description=(
        "Search for customer records matching a company name and status filter. "
        "Returns a list of zero or more matching customers as JSON. Raises an "
        "error if the status filter is invalid. Use get_customer instead when "
        "you already know the exact customer identifier."
    ),
    annotations=_READ_ONLY,
)
def search_customers(
    company: Annotated[str, Field(description="Company name to match, case-sensitive.")],
    status: Annotated[
        Literal["active", "inactive"], Field(description="Status filter: 'active' or 'inactive'.")
    ] = "active",
) -> list[dict[str, str]]:
    return [{"customer_id": "1042", "company": company, "status": status}]


if __name__ == "__main__":
    mcp.run()
