"""A well-documented example MCP server used by MCPLint's own tests.

Run directly: python examples/good_server/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("good-customer-server")


@mcp.tool(
    description=(
        "Retrieve a single customer record by its exact customer ID "
        "(format CUST-XXXX). Read-only. Raises a not-found error if the "
        "ID does not exist. Use search_customers to find a customer when "
        "you don't already have the exact ID."
    )
)
def get_customer(customer_id: str) -> dict[str, str]:
    """customer_id: the exact customer identifier, e.g. CUST-1042."""
    return {"customer_id": customer_id, "name": "Example Customer"}


@mcp.tool(
    description=(
        "Search for customers matching a company name and/or status filter. "
        "Read-only, returns zero or more matches. Use get_customer instead "
        "when you already know the exact customer ID."
    )
)
def search_customers(company: str, status: str = "active") -> list[dict[str, str]]:
    """company: company name to match. status: one of 'active', 'inactive'."""
    return [{"customer_id": "CUST-1042", "company": company, "status": status}]


if __name__ == "__main__":
    mcp.run()
